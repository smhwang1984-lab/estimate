"""편집 권한 상태 (v1.7.0). 서버에 편집 암호가 걸려 있을 때 이 PC가 쓸 수 있는지를 기억한다.

- 서버가 암호를 쓰지 않으면(protected=False) 예전처럼 누구나 편집한다. 로컬 폴더 모드에는 암호가 없다.
- 암호를 입력해 로그인하면 서버가 준 토큰을 **메모리에만** 둔다(프로그램을 끄면 사라진다 — 다시 켜면 읽기
  전용으로 시작). 토큰은 쓰기 요청마다 `X-Edit-Token`으로 서버에 보낸다. 암호 원문은 저장하지 않는다.
- 서버가 알려 주는 편집 지문(`edit_rev`)과 내 토큰의 지문이 다르면 다른 PC가 암호를 바꾼 것이므로 토큰을 버린다.
"""

import hashlib
import threading

_lock = threading.Lock()
_state = {"protected": False, "token": "", "revoked_event": False}


def rev_of(token):
    return hashlib.sha256(str(token).encode("utf-8")).hexdigest()[:12] if token else ""


def is_protected():
    return _state["protected"]


def token():
    return _state["token"]


def can_edit():
    """서버 모드 기준: 암호가 없거나 토큰이 있으면 True."""
    with _lock:
        return (not _state["protected"]) or bool(_state["token"])


def set_token(value):
    with _lock:
        _state["token"] = str(value or "")


def clear_token():
    with _lock:
        _state["token"] = ""


def reset():
    """데이터 위치가 바뀌었을 때(다른 서버·로컬). 이전 서버의 권한을 들고 가지 않는다."""
    with _lock:
        _state.update(protected=False, token="", revoked_event=False)


def apply_server_state(protected, edit_rev):
    """서버가 알려 준 상태를 반영한다. 내 토큰이 더는 맞지 않으면 'revoked'를 돌려준다."""
    with _lock:
        _state["protected"] = bool(protected)
        if not protected:
            # 토큰은 지우지 않는다. 암호를 막 정한 직후 늦게 처리되는 '암호 없음' 상태 알림이 방금 받은
            # 토큰을 지우면 안 되기 때문이다(서버가 암호를 쓰지 않으면 토큰은 어차피 무시된다).
            return ""
        if _state["token"] and rev_of(_state["token"]) != str(edit_rev or ""):
            _state["token"] = ""
            return "revoked"
    return ""


def note_locked():
    """쓰기가 401(locked)로 거절됐다. 토큰이 있었다면 더는 유효하지 않은 것이다."""
    with _lock:
        had = bool(_state["token"])
        _state["protected"] = True
        _state["token"] = ""
        if had:
            _state["revoked_event"] = True


def consume_revoked_event():
    with _lock:
        flag = _state["revoked_event"]
        _state["revoked_event"] = False
        return flag
