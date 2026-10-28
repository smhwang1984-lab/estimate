"""Estimate(견적) API 서버 (FastAPI).

## 사내망 전용

이 서버에는 로그인이 없다. 그래서 **서버가 직접 본 TCP 접속 IP**가 유일한 관문이다.
`ESTIMATE_ALLOWED_CIDRS` 대역 밖에서 온 요청은 경로와 상관없이 403으로 거부한다.

- 접속 IP를 못 받았거나 해석할 수 없으면 거부한다. TSERP는 같은 경우를 허용하는데,
  TSERP에는 로그인·권한이 뒤에 한 겹 더 있기 때문이다. 여기에는 그게 없다.
- NAS의 Tailscale은 VPN 접속을 127.0.0.1로 넘겨준다(TSERP 3.9.4에서 실사용 확인).
  127.0.0.1은 허용 대역이 아니므로 VPN으로 들어온 요청도 자동으로 막힌다.
- 컨테이너는 host 네트워크로 띄운다. bridge+ports로 띄우면 Docker가 접속 IP를
  게이트웨이 주소(172.x)로 바꿔 버려 이 판정이 무력해진다(TSERP 3.9.3 교훈).

## 변경 알림 — /changes (v1.1.0, 롱폴링)

클라이언트는 `/changes?since=<token>&wait=25`를 걸어 두고, 서버는 데이터가 바뀌는 순간
(설정·견적 저장, 견적 삭제) 응답한다. 안 바뀌면 wait초 뒤 같은 token으로 답한다.
몇 초마다 묻는 방식보다 반영이 빠르고(즉시) 요청 수도 적다(PC당 25초에 한 번).

- 기다리는 요청은 스레드 하나씩을 붙잡는다(FastAPI 동기 함수 = 스레드풀). 그래서 동시에
  기다리는 수를 MAX_WAITERS로 묶고, 넘치면 기다리지 않고 바로 답한다(클라이언트가 잠깐
  쉬었다 다시 묻는다 — 폴링으로 내려앉을 뿐 멈추지 않는다).
- 알림은 이 프로세스 안의 Condition으로 전한다. uvicorn worker를 여러 개 띄우면 다른
  worker의 저장을 못 듣는다 — Dockerfile의 CMD에 --workers를 붙이지 말 것.

## 응답 형식

정상은 200, 실패는 상태 코드 + {"ok": false, "reason": ...}.
클라이언트(estimate_app/core/remote.py)는 상태 코드로 판단하고 본문은 보조로 읽는다.
"""

import ipaddress
import threading
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from . import backup, config, store

_ALLOWED = config.allowed_networks()
_STATE = {"db_ok": False, "error": ""}

MAX_WAIT_SECONDS = 25
MAX_WAITERS = 16
_change_cond = threading.Condition()
_change = {"seq": 0, "waiters": 0}


def _notify_change():
    with _change_cond:
        _change["seq"] += 1
        _change_cond.notify_all()


@asynccontextmanager
async def lifespan(_app):
    try:
        store.init_db()
        _STATE["db_ok"] = True
        backup.start_scheduler()
    except Exception as exc:
        # 서버는 띄워 두고 /health로 상태를 알린다 — 컨테이너가 재시작을 반복하면
        # 원인을 로그에서밖에 볼 수 없다.
        _STATE["error"] = str(exc)
        print(f"[startup] DB init failed: {exc}", flush=True)
    yield


app = FastAPI(title="Estimate API", version=config.SERVER_VERSION, lifespan=lifespan)


def _fail(status, reason, msg="", **extra):
    return JSONResponse({"ok": False, "reason": reason, "msg": msg, **extra}, status_code=status)


def _client_ip(request: Request):
    return request.client.host if request.client else ""


def is_allowed_ip(client_ip):
    if not client_ip:
        return False
    try:
        addr = ipaddress.ip_address(client_ip)
    except ValueError:
        return False
    return any(addr in net for net in _ALLOWED)


@app.middleware("http")
async def internal_only_gate(request: Request, call_next):
    if not is_allowed_ip(_client_ip(request)):
        return _fail(403, "forbidden", "사내망에서만 접속할 수 있습니다.")
    return await call_next(request)


def _db_ready():
    return _STATE["db_ok"]


def _clean_title(title):
    title = str(title or "").strip()
    if not title or len(title) > config.TITLE_MAX:
        return ""
    if any(ord(ch) < 32 for ch in title) or any(ch in title for ch in '\\/:*?"<>|'):
        return ""
    return title


class SettingsBody(BaseModel):
    settings: Dict[str, Any]
    saved_by: str = Field(default="", max_length=200)


class EstimateBody(BaseModel):
    payload: Dict[str, Any]
    # 클라이언트가 마지막으로 본 mtime. 없던 견적을 새로 만들 때는 None.
    base_mtime: Optional[int] = None
    saved_by: str = Field(default="", max_length=200)


@app.get("/health")
def health():
    db_ok = _db_ready() and store.check_db()
    return {"ok": db_ok, "server_version": config.SERVER_VERSION,
            "api_version": config.API_VERSION, "db_ok": db_ok, "error": _STATE["error"]}


@app.get("/settings")
def get_settings():
    if not _db_ready():
        return _fail(503, "server_error", "서버 DB를 사용할 수 없습니다.")
    found = store.get_settings()
    if found is None:
        return {"ok": True, "exists": False}
    return {"ok": True, "exists": True, **found}


@app.put("/settings")
def put_settings(body: SettingsBody, request: Request):
    if not _db_ready():
        return _fail(503, "server_error", "서버 DB를 사용할 수 없습니다.")
    mtime = store.put_settings(body.settings, body.saved_by, _client_ip(request))
    _notify_change()
    return {"ok": True, "mtime": mtime}


@app.get("/estimates")
def list_estimates():
    if not _db_ready():
        return _fail(503, "server_error", "서버 DB를 사용할 수 없습니다.")
    return {"ok": True, "entries": store.list_estimates()}


@app.get("/estimates/{title}")
def get_estimate(title: str, meta: int = 0):
    if not _db_ready():
        return _fail(503, "server_error", "서버 DB를 사용할 수 없습니다.")
    clean = _clean_title(title)
    if not clean:
        return _fail(400, "bad_title", "견적 이름이 올바르지 않습니다.")
    entry = store.get_estimate(clean, with_payload=not meta)
    if entry is None:
        return _fail(404, "missing", "견적이 없습니다.")
    return {"ok": True, **entry}


@app.put("/estimates/{title}")
def put_estimate(title: str, body: EstimateBody, request: Request):
    if not _db_ready():
        return _fail(503, "server_error", "서버 DB를 사용할 수 없습니다.")
    clean = _clean_title(title)
    if not clean:
        return _fail(400, "bad_title", "견적 이름이 올바르지 않습니다.")
    try:
        entry = store.put_estimate(clean, body.payload, body.base_mtime,
                                   body.saved_by, _client_ip(request))
    except store.ConflictError as exc:
        return _fail(409, "conflict", "다른 곳에서 먼저 저장했습니다.", mtime=exc.current_mtime)
    _notify_change()
    return {"ok": True, **entry}


@app.delete("/estimates/{title}")
def delete_estimate(title: str, request: Request, by: str = ""):
    if not _db_ready():
        return _fail(503, "server_error", "서버 DB를 사용할 수 없습니다.")
    clean = _clean_title(title)
    if not clean:
        return _fail(400, "bad_title", "견적 이름이 올바르지 않습니다.")
    if not store.delete_estimate(clean, by[:200], _client_ip(request)):
        return _fail(404, "missing", "견적이 없습니다.")
    _notify_change()
    return {"ok": True}


@app.get("/changes")
def changes(since: str = "", wait: float = 0):
    """지금 변경 표시를 돌려준다. since가 지금 값과 같으면 바뀔 때까지(최대 wait초) 기다린다."""
    if not _db_ready():
        return _fail(503, "server_error", "서버 DB를 사용할 수 없습니다.")
    with _change_cond:
        seq = _change["seq"]
    current = store.change_state()
    if since and current["token"] == since and wait > 0:
        with _change_cond:
            if _change["waiters"] < MAX_WAITERS:
                _change["waiters"] += 1
                try:
                    # seq를 먼저 잡아 두었으므로, 상태를 읽은 직후 끼어든 변경도 놓치지 않는다.
                    _change_cond.wait_for(lambda: _change["seq"] != seq,
                                          timeout=min(float(wait), MAX_WAIT_SECONDS))
                finally:
                    _change["waiters"] -= 1
        current = store.change_state()
    return {"ok": True, **current}
