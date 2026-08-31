"""데이터를 어느 폴더에 둘지 정한다(v0.1.4 신설 — 네트워크 공유 요청).

여러 대의 PC가 같은 단가·소재 기준으로 견적을 내고, 만든 견적을 서로 주고받을 수 있도록
저장 폴더를 사용자가 고를 수 있게 한 것이다. 고른 폴더(공유 폴더)에는 두 가지가 놓인다.

    {데이터 폴더}\\settings.json     단가·Material·비중·가공조건·회사/견적서 양식
    {데이터 폴더}\\estimates\\*.json  견적 보관함(core/library.py)

## `paths.get_user_dir()`를 통째로 옮기지 않은 이유

사용자 폴더에 있는 파일 넷은 성격이 서로 다르다. 한꺼번에 공유로 옮기면 두 가지가 깨진다.

    session_state.json  자동 저장이다. 종료할 때 쓰고 시작할 때 읽는다. 공유로 옮기면 두
                        사람이 같이 켜 뒀을 때 나중에 끈 쪽이 앞사람 작업을 말없이 덮어쓴다
                        (자동이라 물어볼 자리조차 없다). 그래서 로컬에 그대로 둔다.
                        여러 PC가 나눠 갖는 것은 '견적 보관함'(library.py)이 맡는다.
    update_state.txt    "이 PC가 이미 처리한 설치 파일" 기록이다. 공유하면 A PC가 업데이트한
                        순간 B PC는 이미 처리한 것으로 판단해 안내를 영영 못 받는다.
    theme.json/rates.json 사본  화면 실험용 덮어쓰기라 PC마다 달라도 되는 값이다.

## 위치를 적어 둔 쪽지는 반드시 로컬이다

공유 위치를 가리키는 쪽지를 공유 위치에 둘 수는 없다(어디인지 알아야 읽을 수 있으므로).
`%LOCALAPPDATA%\\MachineEstimate\\data_location.json`에 둔다.

## 못 닿는 경로를 만났을 때

네트워크 폴더는 로컬 디스크와 달리 '가끔 없다'. 여기서 두 가지를 막는다.

1. **끊긴 경로에서 오래 멈추지 않는다.** 존재하지 않는 UNC 호스트에 접근하면 SMB가
   수십 초를 기다린다. 프로그램이 그동안 안 뜬 것처럼 보이므로, 접근 확인은 별도 스레드로
   돌리고 정해진 시간 안에 답이 없으면 '못 닿음'으로 판정한다.
2. **못 읽었으면 쓰지도 않는다.** 이건 `settings.py`가 맡는다 — 읽기에 실패해 기본값을
   들고 있는 상태에서 저장하면, 공유 settings.json이 모두에게 기본값으로 덮어써진다.

판정 결과는 실행하는 동안 한 번만 하고 캐시한다(`get_state`). 폴더를 바꾸거나 사용자가
'다시 확인'을 누르면 `recheck=True`로 다시 잰다.
"""

import json
import os
import tempfile
import threading

from . import paths

LOCATION_FILE = "data_location.json"
LIBRARY_DIR_NAME = "estimates"

# 못 닿는 네트워크 경로에서 이만큼만 기다린다. 살아 있는 공유 폴더는 1초 안에 답한다.
PROBE_TIMEOUT = 4.0

# reason 값 — 화면에 문장으로 바꿔 보여 준다(describe 참고).
REASON_OK = ""
REASON_MISSING = "missing"          # 경로는 살아 있는데 폴더가 없다
REASON_UNREACHABLE = "unreachable"  # 정해진 시간 안에 응답이 없다(연결 끊김 등)
REASON_READONLY = "readonly"        # 폴더는 보이는데 쓸 수 없다(권한)

_state = None


# ---------- 위치 쪽지(로컬 고정) ----------

def get_location_path():
    """공유 폴더 위치를 적어 둔 파일. 반드시 로컬이다(위 설명 참고)."""
    return paths.get_user_file(LOCATION_FILE)


def load_location():
    """{"path": str, "enabled": bool}. 지정한 적이 없으면 빈 경로."""
    try:
        with open(get_location_path(), "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, ValueError):
        return {"path": "", "enabled": False}
    if not isinstance(payload, dict):
        return {"path": "", "enabled": False}
    path = str(payload.get("path", "")).strip()
    return {"path": path, "enabled": bool(payload.get("enabled", False)) and bool(path)}


def save_location(path, enabled=True):
    """위치를 기록한다. 다음 `get_state()`부터 새 위치가 쓰인다."""
    global _state
    payload = {"path": str(path or "").strip(), "enabled": bool(enabled) and bool(path)}
    ok = write_json_atomic(get_location_path(), payload)
    if ok:
        _state = None  # 다음 조회 때 새 위치로 다시 판정한다
    return ok


def clear_location():
    """로컬(%LOCALAPPDATA%)로 되돌린다. 공유 폴더의 파일은 건드리지 않는다."""
    return save_location("", enabled=False)


# ---------- 상태 판정 ----------

def _probe_blocking(path):
    """실제로 써 보고 판정한다. '될 것 같다'로 넘기지 않는다."""
    if not os.path.isdir(path):
        return REASON_MISSING
    try:
        handle, temp_path = tempfile.mkstemp(dir=path, prefix=".estimate_probe_")
        os.close(handle)
        os.remove(temp_path)
    except OSError:
        return REASON_READONLY
    return REASON_OK


def probe(path, timeout=PROBE_TIMEOUT):
    """`_probe_blocking`을 시간 제한을 걸어 부른다.

    스레드를 daemon으로 두고 join(timeout)으로 기다린다 — 끊긴 UNC 경로에서 os 호출 자체가
    수십 초 잡혀 있어도 프로그램은 timeout 뒤에 진행한다(그 스레드는 그대로 두고 잊는다.
    파이썬에서 블로킹 중인 스레드를 밖에서 끊을 방법은 없고, 남아 있어도 임시 파일 하나를
    만들려다 실패할 뿐이라 해가 없다).
    """
    if not str(path or "").strip():
        return REASON_MISSING
    result = {}

    def run():
        try:
            result["reason"] = _probe_blocking(path)
        except OSError:
            result["reason"] = REASON_UNREACHABLE

    worker = threading.Thread(target=run, daemon=True)
    worker.start()
    worker.join(timeout)
    return result.get("reason", REASON_UNREACHABLE)


def get_state(recheck=False):
    """지금 데이터 폴더의 상태.

        dir     실제로 쓸 폴더 경로
        shared  공유 폴더를 쓰고 있는가(로컬이면 False)
        ok      읽고 쓸 수 있는가
        reason  ok가 False일 때의 이유(REASON_* 중 하나)

    공유 폴더가 못 쓰는 상태여도 `dir`은 그대로 공유 경로를 가리킨다. 말없이 로컬로
    돌아가면 사용자는 공유 값을 쓰고 있다고 믿은 채 자기 PC에만 값을 쌓게 된다 —
    조용히 갈라지는 것보다 "지금 못 닿는다"고 알리고 멈추는 편이 낫다.
    """
    global _state
    if _state is not None and not recheck:
        return dict(_state)

    location = load_location()
    if not location["enabled"]:
        _state = {"dir": paths.get_user_dir(), "shared": False,
                  "ok": True, "reason": REASON_OK}
        return dict(_state)

    reason = probe(location["path"])
    _state = {"dir": location["path"], "shared": True,
              "ok": reason == REASON_OK, "reason": reason}
    return dict(_state)


def get_data_dir():
    """settings.json과 견적 보관함이 놓이는 폴더."""
    return get_state()["dir"]


def get_data_file(filename):
    return os.path.join(get_data_dir(), filename)


def get_library_dir():
    return os.path.join(get_data_dir(), LIBRARY_DIR_NAME)


def is_shared():
    return get_state()["shared"]


def describe(state=None):
    """상태를 사람이 읽는 한 줄로. 화면 여러 곳에서 같은 문구를 쓰기 위해 여기 둔다."""
    state = state or get_state()
    if not state["shared"]:
        return "이 PC에만 저장 (기본값)"
    if state["ok"]:
        return "공유 폴더 사용 중 — 정상"
    return {
        REASON_MISSING: "공유 폴더를 찾을 수 없습니다 (경로가 바뀌었거나 삭제됨)",
        REASON_UNREACHABLE: "공유 폴더에 연결하지 못했습니다 (네트워크 연결 확인)",
        REASON_READONLY: "공유 폴더에 쓸 수 없습니다 (폴더 권한 확인)",
    }.get(state["reason"], "공유 폴더를 쓸 수 없습니다")


# ---------- 파일 쓰기 ----------

def write_json_atomic(path, payload):
    """임시 파일에 다 쓴 뒤 이름을 바꿔치기한다.

    `open(path, "w")`는 쓰기 전에 파일을 먼저 비운다. 로컬 디스크에서는 거의 문제가 안
    되지만, 네트워크 폴더는 쓰는 도중에 끊길 수 있어 그 경우 모두에게 잘린 파일이 남는다.
    임시 파일은 반드시 같은 폴더에 만든다 — 다른 드라이브에 만들면 os.replace가
    한 번에 바꿔치기하지 못한다.
    """
    directory = os.path.dirname(path) or "."
    try:
        os.makedirs(directory, exist_ok=True)
    except OSError:
        return False

    temp_path = None
    try:
        handle, temp_path = tempfile.mkstemp(dir=directory, prefix=".tmp_", suffix=".json")
        with os.fdopen(handle, "w", encoding="utf-8") as temp_file:
            json.dump(payload, temp_file, ensure_ascii=False, indent=2)
        os.replace(temp_path, path)
        return True
    except OSError:
        if temp_path:
            try:
                os.remove(temp_path)
            except OSError:
                pass
        return False


def read_json(path):
    """(내용, 오류)를 돌려준다. 오류는 None / "missing" / "unreachable" / "broken".

    '파일이 없다'와 '경로에 못 닿는다'를 반드시 구분한다 — 앞쪽은 처음 쓰는 정상 상태라
    기본값으로 시작하면 되지만, 뒤쪽에서 기본값으로 시작했다가 저장하면 공유 파일을
    통째로 날린다.
    """
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle), None
    except FileNotFoundError:
        return None, REASON_MISSING
    except ValueError:
        return None, "broken"
    except OSError:
        return None, REASON_UNREACHABLE
