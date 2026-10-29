"""견적 서버(estimate_server) 통신 (v1.3.0 신설).

표준 라이브러리 urllib만 쓴다 — PyInstaller 번들에 새 의존을 들이지 않기 위해서다.
서버는 사내망 HTTP 전용이라 TLS를 쓰지 않는다. 그래서 spec의 `_ssl`/`ssl` 제외를 그대로
둘 수 있다(urllib·http.client는 ssl이 없으면 https만 못 쓸 뿐 http는 정상 동작한다).

모든 함수는 (값, 오류)를 돌려준다. 오류는 None 또는 아래 REASON_* 중 하나다.
datastore.py의 REASON_*와 같은 문자열을 쓰는 것은 일부러다 — 화면은 오류가 폴더에서
왔는지 서버에서 왔는지 몰라도 같은 문장으로 보여 줄 수 있어야 한다.
"""

import json
import urllib.error
import urllib.request
from urllib.parse import quote

from . import editlock

# 서버 config.API_VERSION과 짝. 서버가 다른 값을 내면 이 프로그램은 그 서버를 쓰지 않는다.
API_VERSION = 1

TIMEOUT = 5.0
PROBE_TIMEOUT = 3.5

REASON_MISSING = "missing"
REASON_UNREACHABLE = "unreachable"
REASON_FORBIDDEN = "forbidden"
REASON_INCOMPATIBLE = "incompatible"
REASON_SERVER_ERROR = "server_error"
REASON_CONFLICT = "conflict"
REASON_BROKEN = "broken"
REASON_LOCKED = "locked"            # v1.7.0: 서버에 편집 암호가 걸려 있고 이 PC는 입력하지 않았다
REASON_BAD_PASSWORD = "bad_password"
REASON_THROTTLED = "throttled"  # 암호를 여러 번 틀려 잠시 막힘


def is_server_url(path):
    return str(path or "").strip().lower().startswith(("http://", "https://"))


def normalize_url(text):
    """사용자가 적은 주소를 정리한다. `192.168.0.10:8100`처럼 적어도 http://를 붙여 준다."""
    text = str(text or "").strip().rstrip("/")
    if text and not is_server_url(text):
        text = "http://" + text
    return text


def _request(base, method, path, body=None, timeout=TIMEOUT):
    data = None
    headers = {"Accept": "application/json"}
    edit_token = editlock.token()
    if edit_token:
        headers["X-Edit-Token"] = edit_token
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    req = urllib.request.Request(base.rstrip("/") + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return json.loads(res.read().decode("utf-8")), None
    except urllib.error.HTTPError as exc:
        try:
            detail = json.loads(exc.read().decode("utf-8"))
        except (ValueError, OSError):
            detail = {}
        reason = {403: REASON_FORBIDDEN, 404: REASON_MISSING, 409: REASON_CONFLICT,
                  429: REASON_THROTTLED}.get(exc.code, REASON_SERVER_ERROR)
        if exc.code == 401:
            if isinstance(detail, dict) and detail.get("reason") == "bad_password":
                reason = REASON_BAD_PASSWORD
            else:
                reason = REASON_LOCKED
                editlock.note_locked()
        return detail if isinstance(detail, dict) else {}, reason
    except (urllib.error.URLError, OSError):
        # 연결 거부·시간 초과·이름 해석 실패 모두 '서버에 못 닿음'으로 본다.
        return None, REASON_UNREACHABLE
    except ValueError:
        return None, REASON_BROKEN


def _estimate_path(title):
    return "/estimates/" + quote(title, safe="")


def probe(base, timeout=PROBE_TIMEOUT):
    """서버를 쓸 수 있으면 "", 아니면 이유. datastore.probe()가 폴더 대신 이걸 부른다."""
    body, error = _request(base, "GET", "/health", timeout=timeout)
    if error:
        return error
    if not isinstance(body, dict):
        return REASON_BROKEN
    if body.get("api_version") != API_VERSION:
        return REASON_INCOMPATIBLE
    if not body.get("db_ok"):
        return REASON_SERVER_ERROR
    return ""


def fetch_settings(base):
    """(서버 응답 dict, 오류). 응답의 mtime·updated_by까지 필요할 때 쓴다(v1.4.0)."""
    body, error = _request(base, "GET", "/settings")
    if error:
        return None, error
    if not isinstance(body, dict):
        return None, REASON_BROKEN
    if not body.get("exists"):
        return None, REASON_MISSING
    if not isinstance(body.get("settings"), dict):
        return None, REASON_BROKEN
    return body, None


def get_settings(base):
    """(설정 dict, 오류). 서버에 아직 설정이 없으면 (None, REASON_MISSING)."""
    body, error = fetch_settings(base)
    return (body["settings"] if body else None), error


def wait_changes(base, since="", wait=0):
    """변경 표시(/changes, 서버 1.1.0+). since가 서버의 지금 값과 같으면 서버가 바뀔 때까지
    최대 wait초 붙잡고 있다가 답한다(롱폴링). 서버 1.0.0이면 (…, REASON_MISSING).

    클라이언트 쪽 시간 제한은 wait보다 넉넉히 둔다 — 서버가 꽉 채워 기다린 뒤 답하는 것이
    정상이므로, 같은 값이면 정상 응답을 '못 닿음'으로 잘못 판정한다.
    """
    path = "/changes?since=" + quote(str(since or ""), safe="") + f"&wait={int(wait)}"
    body, error = _request(base, "GET", path, timeout=max(TIMEOUT, wait + 10))
    if error:
        return None, error
    if not isinstance(body, dict) or "token" not in body:
        return None, REASON_BROKEN
    return body, None


def put_settings(base, settings, saved_by):
    body, error = _request(base, "PUT", "/settings", {"settings": settings, "saved_by": saved_by})
    return (body.get("mtime") if isinstance(body, dict) else None), error


def list_estimates(base):
    body, error = _request(base, "GET", "/estimates")
    if error:
        return None, error
    entries = body.get("entries") if isinstance(body, dict) else None
    if not isinstance(entries, list):
        return None, REASON_BROKEN
    return entries, None


def get_estimate(base, title, meta_only=False):
    """(견적 dict, 오류). meta_only면 payload 없이 mtime 등만."""
    path = _estimate_path(title) + ("?meta=1" if meta_only else "")
    body, error = _request(base, "GET", path)
    if error:
        return None, error
    if not isinstance(body, dict) or (not meta_only and not isinstance(body.get("payload"), dict)):
        return None, REASON_BROKEN
    return body, None


def put_estimate(base, title, payload, base_mtime, saved_by):
    """저장. 충돌이면 (서버 응답, REASON_CONFLICT) — 응답의 mtime이 서버의 지금 값이다."""
    body, error = _request(base, "PUT", _estimate_path(title),
                           {"payload": payload, "base_mtime": base_mtime, "saved_by": saved_by})
    return body, error


def delete_estimate(base, title, deleted_by):
    _body, error = _request(base, "DELETE", _estimate_path(title) + "?by=" + quote(deleted_by, safe=""))
    return error is None, error


BACKUP_TIMEOUT = 30.0
RESTORE_TIMEOUT = 60.0


def create_backup(base):
    """서버에 지금 백업을 만든다(서버 1.2.0+). (파일 정보 dict, 오류). 옛 서버는 REASON_MISSING."""
    body, error = _request(base, "POST", "/backup", {}, timeout=BACKUP_TIMEOUT)
    if error:
        return (body if isinstance(body, dict) else None), error
    if not isinstance(body, dict) or not body.get("name"):
        return None, REASON_BROKEN
    return body, None


def list_backups(base):
    """서버의 백업 목록(최근 30개, 새것부터). (list, 오류). 옛 서버에도 목록은 있다."""
    body, error = _request(base, "GET", "/backup")
    if error:
        return None, error
    entries = body.get("entries") if isinstance(body, dict) else None
    if not isinstance(entries, list):
        return None, REASON_BROKEN
    return entries, None


def restore_backup(base, name):
    """고른 백업으로 서버 데이터를 되돌린다(서버 1.3.0+). ({restored, safety} 또는 오류 본문, 오류)."""
    body, error = _request(base, "POST", "/backup/restore", {"name": name}, timeout=RESTORE_TIMEOUT)
    if error:
        return (body if isinstance(body, dict) else None), error
    if not isinstance(body, dict) or not body.get("restored"):
        return None, REASON_BROKEN
    return body, None


def login(base, password):
    """편집 암호 확인. (토큰 또는 "", 오류) — 서버에 암호가 없으면 ("", None). 옛 서버는 REASON_MISSING."""
    body, error = _request(base, "POST", "/auth/login", {"password": password})
    if error:
        return None, error
    if not isinstance(body, dict):
        return None, REASON_BROKEN
    return str(body.get("token") or ""), None


def change_password(base, current, new):
    """편집 암호를 정하거나 바꾼다(new가 비면 해제). (토큰 또는 "", 오류)."""
    body, error = _request(base, "POST", "/auth/password", {"current": current, "new": new})
    if error:
        return None, error
    if not isinstance(body, dict):
        return None, REASON_BROKEN
    return str(body.get("token") or ""), None
