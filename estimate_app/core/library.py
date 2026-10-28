"""견적 보관함 — 카드 목록에 이름을 붙여 저장하고 다시 불러온다(v0.1.4 신설).

데이터 폴더(`core/datastore.py`)를 공유 폴더로 잡아 두면 여러 PC가 같은 보관함을 본다.
파일 하나가 견적 한 건이다.

    {데이터 폴더}\\estimates\\{이름}.json

## 왜 세션(session.py)을 공유하지 않고 이걸 따로 만들었나

세션은 종료할 때 자동으로 저장된다. 그걸 공유 폴더에 두면 두 사람이 같이 켜 뒀을 때
나중에 끈 쪽이 앞사람 작업을 조용히 덮어쓴다 — 자동이라 물어볼 자리조차 없다.
보관함은 사용자가 이름을 정해 직접 저장하므로, 덮어쓰기 직전에 물어볼 수 있고
누가 언제 저장했는지도 파일에 남는다. 세션(작업 중 상태)은 지금처럼 PC마다 로컬이다.

## 덮어쓰기 판정

`불러오기 → 편집 → 저장` 사이에 다른 사람이 같은 파일을 고쳐 놨을 수 있다. 불러온
시각의 수정 시각(mtime)을 기억해 두었다가 저장 직전에 다시 재서 다르면 알린다.
파일 잠금은 걸지 않는다 — 네트워크 폴더에서 잠금은 프로그램이 비정상 종료하면 남아
버려서, 남의 작업을 막아 놓고 풀지 못하는 쪽이 더 큰 사고가 된다.

## v1.3.0: 서버 보관함

데이터 위치가 견적 서버면 같은 함수들이 파일 대신 서버(core/remote.py)를 부른다. 화면이
쓰는 항목 모양({"path", "mtime", ...})은 그대로다.

    path   "srv:{이름}" — 파일 경로 대신 쓰는 열쇠. 세션의 library_current에도 이대로 남는다.
    mtime  서버가 매기는 값(초 단위, 같은 견적 안에서는 반드시 커진다). 파일 mtime처럼
           날짜로 보여 줄 수 있어 화면의 충돌 안내 문구를 그대로 쓴다.

화면의 '남이 고쳤나' 확인에 더해 서버가 한 번 더 막는다. 저장할 때 마지막으로 본
mtime(`get_mtime`/`load_entry`가 기억)을 같이 보내고, 그 사이에 다른 PC가 저장했으면
서버가 거절한다(409). 확인과 저장 사이의 짧은 틈에 끼어든 저장까지 잡기 위해서다.
거절 이유는 `get_last_error()`로 화면에 알린다.

삭제는 서버에서 '지움 표시'만 한다 — 관리자가 되살릴 수 있다.
"""

import os
from datetime import datetime

from . import datastore, remote
from .. import APP_VERSION
from .model import create_blank_item, has_item_data

FILE_EXT = ".json"

# 윈도우 파일 이름에 못 쓰는 문자. 사용자가 품번을 그대로 이름에 넣는 일이 많아
# (예: `A-100/B`) 조용히 실패하지 않도록 여기서 걸러 낸다.
_BAD_CHARS = '\\/:*?"<>|'
_ENTRY_CACHE = {}

SERVER_PREFIX = "srv:"
# 서버 견적마다 마지막으로 본 mtime. 저장할 때 서버에 '이 값 그대로일 때만 덮어써라'로 보낸다.
_SERVER_SEEN = {}
_last_error = None


def sanitize_title(title):
    """견적 이름을 파일 이름으로 쓸 수 있게 다듬는다. 빈 값이면 빈 문자열."""
    text = str(title or "").strip()
    for char in _BAD_CHARS:
        text = text.replace(char, "_")
    # 윈도우는 이름 끝의 점·공백을 잘라 버려서, 그대로 두면 저장한 이름과 실제 파일 이름이
    # 어긋난다(다음에 같은 이름으로 저장할 때 덮어쓰기 판정이 빗나간다).
    text = text.rstrip(" .")
    return text[:120]


def is_server_path(path):
    return str(path or "").startswith(SERVER_PREFIX)


def _server_title(path):
    return str(path)[len(SERVER_PREFIX):]


def belongs_to_location(path):
    """이 열쇠가 지금 데이터 위치(서버/폴더)의 것인가. 위치 쪽지만 보므로 즉시 끝난다.

    세션에서 되살린 '마지막 견적' 참조가 위치를 바꾸기 전 것이면 버리는 데 쓴다 —
    서버 열쇠를 폴더 경로로(또는 그 반대로) 저장하려 들면 종료 때 자동 저장이 매번 실패한다.
    """
    return is_server_path(path) == datastore.location_is_server()


def get_last_error():
    """마지막 save_entry() 실패 이유. 서버 충돌이면 remote.REASON_CONFLICT."""
    return _last_error


def entry_path(title):
    if datastore.is_server():
        return SERVER_PREFIX + sanitize_title(title)
    return os.path.join(datastore.get_library_dir(), sanitize_title(title) + FILE_EXT)


def get_mtime(path):
    if is_server_path(path):
        if not datastore.is_server():
            return None
        entry, error = remote.get_estimate(datastore.get_data_dir(), _server_title(path), meta_only=True)
        if error == remote.REASON_MISSING:
            _SERVER_SEEN[path] = None
            return None
        if error:
            return None
        _SERVER_SEEN[path] = entry.get("mtime")
        return entry.get("mtime")
    try:
        return int(os.path.getmtime(path))
    except OSError:
        return None


def _who():
    """저장한 사람. 계정 이름과 PC 이름을 붙여 둔다 — 공유 폴더에서 '누가 올린 견적인지'를
    알려면 이 정도면 충분하다(별도 로그인 개념이 이 프로그램에는 없다).

    `getpass`/`socket` 대신 환경변수를 쓴다. 이 두 모듈은 이 프로그램이 다른 데서 전혀
    쓰지 않는 것이라, 이름 한 줄 얻자고 PyInstaller 번들에 새 의존을 들이지 않기 위해서다
    (spec의 EXCLUDES는 '확인한 것만 넣는다'는 규칙으로 관리되고 있다).
    """
    user = os.environ.get("USERNAME") or os.environ.get("USER") or "?"
    host = os.environ.get("COMPUTERNAME") or "?"
    return f"{user}@{host}"


def is_changed_by_other(library_current, path, existing_mtime):
    """저장하려는 파일이 '내가 불러온 뒤 다른 곳에서 바뀐' 것인가.

    화면 코드가 아니라 여기 두는 이유는 이 판정이 헤드리스로 검증 가능해야 하기 때문이다.
    `library_current`는 세션에도 저장되므로(session.py 참고) 프로그램을 껐다 켠 뒤에도
    같은 기준으로 판정한다. 참조가 없거나 다른 파일을 가리키면 False -- 그때는 평범한
    '이미 있습니다, 덮어쓸까요?' 확인으로 내려간다.
    """
    if not isinstance(library_current, dict) or existing_mtime is None:
        return False
    if library_current.get("path") != path:
        return False
    known = library_current.get("mtime")
    return known is not None and known != existing_mtime


def _entry_stat(path):
    try:
        stat = os.stat(path)
        return int(stat.st_mtime), int(stat.st_size)
    except OSError:
        return None, None


def _cache_entry(path, mtime, size, entry):
    _ENTRY_CACHE[path] = (mtime, size, dict(entry))


def _entry_from_file(path, title, mtime, size):
    payload, error = datastore.read_json(path)
    if error or not isinstance(payload, dict):
        entry = {"title": title, "path": path, "saved_at": "", "saved_by": "",
                 "count": 0, "mtime": mtime, "broken": True}
        _cache_entry(path, mtime, size, entry)
        return entry
    entry = {
        "title": str(payload.get("title") or title),
        "path": path,
        "saved_at": str(payload.get("saved_at") or ""),
        "saved_by": str(payload.get("saved_by") or ""),
        "count": len(payload.get("items") or []),
        "mtime": mtime,
        "broken": False,
    }
    _cache_entry(path, mtime, size, entry)
    return entry


def _entry_metadata(path, title):
    mtime, size = _entry_stat(path)
    cached = _ENTRY_CACHE.get(path)
    if cached and cached[0] == mtime and cached[1] == size:
        return dict(cached[2])
    return _entry_from_file(path, title, mtime, size)


def list_entries():
    """(목록, 오류). 오류는 None / datastore의 reason 값.

    최근에 저장한 것이 위로 오게 정렬한다. 파일 하나가 깨져 있어도 나머지는 보여 준다.
    파일별 mtime+size가 그대로면 이전에 읽은 메타데이터를 재사용한다.
    """
    state = datastore.get_state()
    if not state["ok"]:
        return [], state["reason"]
    if state.get("server"):
        return _list_server_entries(state["dir"])

    directory = datastore.get_library_dir()
    if not os.path.isdir(directory):
        # 아직 한 건도 저장하지 않은 정상 상태다(폴더는 처음 저장할 때 만든다).
        return [], None

    try:
        names = os.listdir(directory)
    except OSError:
        return [], datastore.REASON_UNREACHABLE

    entries = []
    seen_paths = set()
    for name in names:
        if not name.lower().endswith(FILE_EXT):
            continue
        path = os.path.join(directory, name)
        seen_paths.add(path)
        title = os.path.splitext(name)[0]
        entries.append(_entry_metadata(path, title))
    for cached_path in list(_ENTRY_CACHE):
        if os.path.dirname(cached_path) == directory and cached_path not in seen_paths:
            _ENTRY_CACHE.pop(cached_path, None)
    entries.sort(key=lambda entry: entry["mtime"] or 0, reverse=True)
    return entries, None


def _list_server_entries(base):
    found, error = remote.list_estimates(base)
    if error:
        return [], error
    entries = []
    for raw in found:
        title = str(raw.get("title") or "")
        if not title:
            continue
        entries.append({"title": title, "path": SERVER_PREFIX + title,
                        "saved_at": str(raw.get("saved_at") or ""),
                        "saved_by": str(raw.get("saved_by") or ""),
                        "count": int(raw.get("count") or 0),
                        "mtime": raw.get("mtime"), "broken": False})
    entries.sort(key=lambda entry: entry["mtime"] or 0, reverse=True)
    return entries, None


def _save_server_entry(kept, payload, path):
    global _last_error
    if not datastore.is_server():
        _last_error = remote.REASON_MISSING
        return None
    if path not in _SERVER_SEEN:
        # 화면이 get_mtime()을 거치지 않고 바로 저장하는 경우. 지금 값을 기준으로 삼는다.
        get_mtime(path)
        if path not in _SERVER_SEEN:
            _last_error = remote.REASON_UNREACHABLE
            return None
    body, error = remote.put_estimate(datastore.get_data_dir(), _server_title(path), payload,
                                      _SERVER_SEEN[path], payload["saved_by"])
    if error:
        _last_error = error
        if error == remote.REASON_CONFLICT:
            _SERVER_SEEN.pop(path, None)  # 다음 확인 때 서버의 지금 값을 다시 읽게 한다
        return None
    mtime = body.get("mtime")
    _SERVER_SEEN[path] = mtime
    return {"path": path, "mtime": mtime, "count": len(kept)}


def save_entry(title, items, path=None):
    """견적 한 건을 저장한다. 성공하면 {"path", "mtime", "count"}, 실패하면 None.

    덮어쓰기 여부·충돌 확인은 부르는 쪽(화면)이 먼저 끝낸 다음 이 함수를 부른다.
    실패 이유는 get_last_error()로 알 수 있다.
    """
    global _last_error
    _last_error = None
    name = sanitize_title(title)
    if not name:
        return None
    kept = [item for item in items if has_item_data(item)]
    saved_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    saved_by = _who()
    payload = {
        "title": name,
        "saved_at": saved_at,
        "saved_by": saved_by,
        "app_version": APP_VERSION,
        "items": kept,
    }
    path = path or entry_path(name)
    if is_server_path(path):
        return _save_server_entry(kept, payload, path)
    if not datastore.write_json_atomic(path, payload):
        _last_error = datastore.REASON_UNREACHABLE
        return None
    mtime, size = _entry_stat(path)
    entry = {"title": name, "path": path, "saved_at": saved_at, "saved_by": saved_by,
             "count": len(kept), "mtime": mtime, "broken": False}
    _cache_entry(path, mtime, size, entry)
    return {"path": path, "mtime": mtime, "count": len(kept)}


def load_entry(path):
    """저장한 견적을 읽어 카드 목록으로 돌려준다. (내용, 오류).

    session.load()와 같은 방식으로 빈 카드 위에 덮어쓴다 — 옛 버전에서 저장한 파일에
    없는 항목(나중에 늘어난 칸)이 있어도 빠짐없이 채워지게 하기 위해서다.
    """
    if is_server_path(path):
        if not datastore.is_server():
            return None, remote.REASON_MISSING
        entry, error = remote.get_estimate(datastore.get_data_dir(), _server_title(path))
        if error:
            return None, error
        _SERVER_SEEN[path] = entry.get("mtime")
        payload = dict(entry["payload"])
        payload.setdefault("title", _server_title(path))
        return _loaded(payload, path, entry.get("mtime")), None

    payload, error = datastore.read_json(path)
    if error or not isinstance(payload, dict):
        return None, (error or "broken")
    return _loaded(payload, path, get_mtime(path)), None


def _loaded(payload, path, mtime):
    items = []
    for raw_item in payload.get("items", []):
        if not isinstance(raw_item, dict):
            continue
        item = create_blank_item(raw_item.get("no", 0))
        item.update(raw_item)
        items.append(item)
    return {
        "title": str(payload.get("title") or os.path.splitext(os.path.basename(path))[0]),
        "items": items,
        "saved_at": str(payload.get("saved_at") or ""),
        "saved_by": str(payload.get("saved_by") or ""),
        "mtime": mtime,
    }


def delete_entry(path):
    if is_server_path(path):
        if not datastore.is_server():
            return False
        ok, _error = remote.delete_estimate(datastore.get_data_dir(), _server_title(path), _who())
        _SERVER_SEEN.pop(path, None)
        return ok
    _ENTRY_CACHE.pop(path, None)
    try:
        os.remove(path)
        return True
    except OSError:
        return False


def upload_folder(directory):
    """폴더(이 PC의 보관함이나 예전 공유 폴더)의 견적 파일을 서버 보관함으로 올린다.

    서버에 같은 이름이 이미 있으면 덮어쓰지 않고 건너뛴다 — 어느 쪽이 최신인지 이
    함수는 알 수 없다. 결과: {"uploaded": [...], "exists": [...], "failed": [...]}
    """
    result = {"uploaded": [], "exists": [], "failed": []}
    if not datastore.is_server():
        result["failed"].append("(데이터 위치가 서버가 아닙니다)")
        return result
    base = datastore.get_data_dir()
    try:
        names = sorted(name for name in os.listdir(directory) if name.lower().endswith(FILE_EXT))
    except OSError:
        result["failed"].append(directory)
        return result
    for name in names:
        payload, error = datastore.read_json(os.path.join(directory, name))
        title = sanitize_title(os.path.splitext(name)[0])
        if error or not isinstance(payload, dict) or not isinstance(payload.get("items"), list) or not title:
            result["failed"].append(name)
            continue
        saved_by = str(payload.get("saved_by") or _who())
        _body, error = remote.put_estimate(base, title, payload, None, saved_by)
        if error == remote.REASON_CONFLICT:
            result["exists"].append(title)
        elif error:
            result["failed"].append(name)
        else:
            result["uploaded"].append(title)
    return result
