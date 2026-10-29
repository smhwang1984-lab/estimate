"""편집 암호 (v1.2.0). 암호를 모르는 PC는 서버에서 읽기만 할 수 있다.

- 암호는 PBKDF2-SHA256 해시로만 `meta` 표에 저장한다(원문은 어디에도 남기지 않는다).
- 로그인에 성공하면 편집 토큰을 준다. 토큰은 해시에서 계산하는 값이라 서버를 다시 띄워도 그대로
  유효하고, 암호를 바꾸면 모든 PC의 토큰이 한꺼번에 무효가 된다. 쓰기 요청(`X-Edit-Token`)만 검사하고
  읽기·출력은 암호 없이 허용한다.
- 암호가 설정되지 않았으면(기본값) 예전처럼 누구나 쓸 수 있다.
- 틀린 암호를 5분에 5번 넘게 보낸 접속 IP는 잠시 막는다(사내망 안의 무작위 대입 방지).
"""

import hashlib
import hmac
import secrets
import threading
import time

from . import store

META_KEY = "edit_password"
ITERATIONS = 200_000
MIN_LENGTH = 4
MAX_LENGTH = 100
FAIL_LIMIT = 5
FAIL_WINDOW = 300.0

_lock = threading.Lock()
_cache = {"loaded": False, "value": ""}
_failures = {}


def _stored():
    with _lock:
        if not _cache["loaded"]:
            _cache["value"] = store.get_meta(META_KEY) or ""
            _cache["loaded"] = True
        return _cache["value"]


def reset_cache():
    with _lock:
        _cache["loaded"] = False
        _failures.clear()


def is_protected():
    return bool(_stored())


def _hash(password, salt=None, iterations=ITERATIONS):
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2${iterations}${salt.hex()}${digest.hex()}"


def _matches(password, stored):
    try:
        _algo, iterations, salt_hex, digest_hex = stored.split("$")
        expected = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                                       bytes.fromhex(salt_hex), int(iterations))
        return hmac.compare_digest(expected.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def token_for(stored):
    if not stored:
        return ""
    return hmac.new(stored.encode("utf-8"), b"estimate-edit-v1", hashlib.sha256).hexdigest()


def current_token():
    return token_for(_stored())


def token_ok(token):
    """쓰기를 해도 되는가. 암호가 없으면 항상 True."""
    stored = _stored()
    if not stored:
        return True
    return bool(token) and hmac.compare_digest(str(token), token_for(stored))


def throttled(ip):
    now = time.time()
    with _lock:
        recent = [t for t in _failures.get(ip, []) if now - t < FAIL_WINDOW]
        _failures[ip] = recent
        return len(recent) >= FAIL_LIMIT


def _record_failure(ip):
    with _lock:
        _failures.setdefault(ip, []).append(time.time())


def login(password, ip):
    """(성공 여부, 토큰). 암호가 없으면 성공·토큰 없음."""
    stored = _stored()
    if not stored:
        return True, ""
    if _matches(str(password or ""), stored):
        with _lock:
            _failures.pop(ip, None)
        return True, token_for(stored)
    _record_failure(ip)
    return False, ""


def change_password(current, new, ip):
    """암호를 처음 정하거나 바꾸거나(new가 비어 있으면) 해제한다.
    (결과, 토큰) — 결과: ok / bad_current / too_short / too_long."""
    stored = _stored()
    if stored and not _matches(str(current or ""), stored):
        _record_failure(ip)
        return "bad_current", ""
    new = str(new or "")
    if new and len(new) < MIN_LENGTH:
        return "too_short", ""
    if len(new) > MAX_LENGTH:
        return "too_long", ""
    if new:
        value = _hash(new)
        store.set_meta(META_KEY, value)
    else:
        value = ""
        store.delete_meta(META_KEY)
    with _lock:
        _cache["value"] = value
        _cache["loaded"] = True
        _failures.pop(ip, None)
    return "ok", token_for(value)


def edit_rev(token=None):
    """편집 토큰의 짧은 지문. 암호가 없으면 빈 문자열. 클라이언트는 자기 토큰의 지문과 비교해
    다른 PC가 암호를 바꿨는지 바로 알아챈다(토큰 자체는 노출하지 않는다)."""
    token = current_token() if token is None else token
    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:12] if token else ""
