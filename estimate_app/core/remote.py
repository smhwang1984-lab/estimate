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
        reason = {403: REASON_FORBIDDEN, 404: REASON_MISSING,
                  409: REASON_CONFLICT}.get(exc.code, REASON_SERVER_ERROR)
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


def get_settings(base):
    """(설정 dict, 오류). 서버에 아직 설정이 없으면 (None, REASON_MISSING)."""
    body, error = _request(base, "GET", "/settings")
    if error:
        return None, error
    if not isinstance(body, dict):
        return None, REASON_BROKEN
    if not body.get("exists"):
        return None, REASON_MISSING
    settings = body.get("settings")
    if not isinstance(settings, dict):
        return None, REASON_BROKEN
    return settings, None


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
