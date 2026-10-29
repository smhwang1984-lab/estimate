"""서버 API 테스트. 저장소 루트에서:  python -m pytest estimate_server/tests -q"""

import os
import sqlite3
import time
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from estimate_server import app as app_module
from estimate_server import auth as auth_module, backup, config, store

LAN = ("192.168.0.25", 50000)


@pytest.fixture()
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(config, "BACKUP_ENABLED", False)
    return tmp_path


def make_client(ip=LAN):
    """접속 IP를 바꿔 끼운 TestClient. starlette 0.41 TestClient에는 client= 인자가 없다."""
    inner = app_module.app

    async def asgi(scope, receive, send):
        if scope["type"] == "http":
            scope = dict(scope, client=ip)
        await inner(scope, receive, send)

    return TestClient(asgi)


@pytest.fixture()
def client(data_dir):
    with make_client() as c:
        yield c


def url(title):
    return "/estimates/" + quote(title, safe="")


def payload(n=2):
    return {"title": "x", "app_version": "1.3.0",
            "items": [{"no": i + 1, "part_no": f"P-{i}"} for i in range(n)]}


# ---------- 사내망 관문 ----------

@pytest.mark.parametrize("ip", ["192.168.0.25", "192.168.10.7"])
def test_lan_allowed(data_dir, ip):
    with make_client((ip, 1)) as c:
        assert c.get("/health").status_code == 200


@pytest.mark.parametrize("ip", ["127.0.0.1", "100.101.102.103", "8.8.8.8", "192.168.1.5",
                                "172.18.0.1", "testclient", ""])
def test_outside_blocked(data_dir, ip):
    with make_client((ip, 1)) as c:
        for res in (c.get("/health"), c.get("/estimates"), c.get(url("a")),
                    c.put("/settings", json={"settings": {}}),
                    c.put(url("a"), json={"payload": payload(), "base_mtime": None}),
                    c.delete(url("a"))):
            assert res.status_code == 403, (ip, res.request.url)
            assert res.json()["reason"] == "forbidden"


# ---------- health / 설정 ----------

def test_health(client):
    body = client.get("/health").json()
    assert body["ok"] and body["db_ok"]
    assert body["api_version"] == config.API_VERSION


def test_settings_roundtrip(client):
    assert client.get("/settings").json() == {"ok": True, "exists": False}
    res = client.put("/settings", json={"settings": {"rates": {"mct": 50000}}, "saved_by": "a@PC1"})
    assert res.status_code == 200
    body = client.get("/settings").json()
    assert body["exists"] and body["settings"] == {"rates": {"mct": 50000}}
    assert body["updated_by"] == "a@PC1"
    first = body["mtime"]
    client.put("/settings", json={"settings": {"rates": {"mct": 1}}})
    assert client.get("/settings").json()["mtime"] > first


# ---------- 견적 보관함 ----------

def test_estimate_create_load_list(client):
    title = "현대 A-100 견적 (1차)"
    res = client.put(url(title), json={"payload": payload(3), "base_mtime": None, "saved_by": "a@PC1"})
    assert res.status_code == 200, res.text
    saved = res.json()
    assert saved["count"] == 3

    loaded = client.get(url(title)).json()
    assert loaded["payload"]["items"][2]["part_no"] == "P-2"
    assert loaded["payload"]["title"] == title  # 저장 이름이 본문 제목을 이긴다
    assert loaded["mtime"] == saved["mtime"]

    meta = client.get(url(title) + "?meta=1").json()
    assert "payload" not in meta and meta["mtime"] == saved["mtime"]

    entries = client.get("/estimates").json()["entries"]
    assert [e["title"] for e in entries] == [title]


def test_estimate_conflicts(client):
    title = "충돌"
    first = client.put(url(title), json={"payload": payload(), "base_mtime": None}).json()
    # 이미 있는데 '새로 만들기'로 보내면 충돌
    res = client.put(url(title), json={"payload": payload(), "base_mtime": None})
    assert res.status_code == 409 and res.json()["mtime"] == first["mtime"]
    # 맞는 base로는 저장되고, mtime은 같은 초 안에서도 반드시 커진다
    second = client.put(url(title), json={"payload": payload(), "base_mtime": first["mtime"]}).json()
    assert second["mtime"] > first["mtime"]
    # 옛 base로 다시 보내면 충돌(다른 PC가 먼저 저장한 상황)
    res = client.put(url(title), json={"payload": payload(), "base_mtime": first["mtime"]})
    assert res.status_code == 409 and res.json()["mtime"] == second["mtime"]


def test_soft_delete_and_revive(client, data_dir):
    title = "지울 견적"
    saved = client.put(url(title), json={"payload": payload(), "base_mtime": None}).json()
    assert client.delete(url(title) + "?by=b@PC2").status_code == 200
    assert client.get(url(title)).status_code == 404
    assert client.get("/estimates").json()["entries"] == []
    assert client.delete(url(title)).status_code == 404

    # 행은 남아 있어 관리자가 되살릴 수 있다
    conn = sqlite3.connect(os.path.join(data_dir, config.DB_FILE))
    row = conn.execute("SELECT deleted_at, deleted_by FROM estimates WHERE title = ?", (title,)).fetchone()
    conn.close()
    assert row[0] and row[1].startswith("b@PC2")

    # 같은 이름으로 새로 저장하면 되살아나고 mtime은 계속 커진다
    revived = client.put(url(title), json={"payload": payload(1), "base_mtime": None}).json()
    assert revived["mtime"] > saved["mtime"] and revived["count"] == 1


@pytest.mark.parametrize("title", [" ", "a/b", "a:b", "x" * 121])
def test_bad_title(client, title):
    res = client.put(url(title), json={"payload": payload(), "base_mtime": None})
    assert res.status_code in (400, 404, 405)


def test_db_unavailable_reports_on_health(tmp_path, monkeypatch):
    # 데이터 폴더 자리에 파일이 있어 DB를 만들 수 없는 상황
    blocker = tmp_path / "not_a_dir"
    blocker.write_text("x")
    monkeypatch.setattr(config, "DATA_DIR", str(blocker))
    monkeypatch.setattr(config, "BACKUP_ENABLED", False)
    monkeypatch.setitem(app_module._STATE, "db_ok", False)
    with make_client() as c:
        body = c.get("/health").json()
        assert body["ok"] is False and body["db_ok"] is False and body["error"]
        assert c.get("/estimates").status_code == 503


def test_backup_snapshot_and_prune(client, data_dir, monkeypatch):
    client.put(url("백업"), json={"payload": payload(), "base_mtime": None})
    path = backup.run_backup()
    conn = sqlite3.connect(path)
    assert conn.execute("SELECT COUNT(*) FROM estimates").fetchone()[0] == 1
    conn.close()

    old = os.path.join(config.backup_dir(), "estimate_20000101_000000.db")
    with open(old, "wb") as handle:
        handle.write(b"")
    past = time.time() - (config.BACKUP_RETENTION_DAYS + 2) * 86400
    os.utime(old, (past, past))
    backup.prune(config.backup_dir())
    assert not os.path.exists(old) and os.path.exists(path)


# ---------- 변경 알림 /changes (v1.1.0) ----------

def test_changes_token_moves_on_every_write(client):
    t0 = client.get("/changes").json()["token"]
    client.put("/settings", json={"settings": {"a": 1}})
    t1 = client.get("/changes").json()["token"]
    client.put(url("알림"), json={"payload": payload(), "base_mtime": None})
    t2 = client.get("/changes").json()
    assert len({t0, t1, t2["token"]}) == 3 and t2["library_rev"] == 1
    client.delete(url("알림"))
    assert client.get("/changes").json()["library_rev"] == 2
    # 실패한 저장(409)·없는 견적 삭제는 표시를 바꾸지 않는다
    client.put(url("알림2"), json={"payload": payload(), "base_mtime": 999})
    client.delete(url("없음"))
    assert client.get("/changes").json()["library_rev"] == 2


def test_changes_returns_immediately_when_token_differs(client):
    start = time.time()
    body = client.get("/changes?since=old&wait=10").json()
    assert body["ok"] and time.time() - start < 2


def test_changes_times_out_with_same_token(client):
    token = client.get("/changes").json()["token"]
    start = time.time()
    body = client.get(f"/changes?since={token}&wait=1").json()
    assert body["token"] == token and 0.8 < time.time() - start < 5


def test_changes_wakes_up_on_write(data_dir):
    import threading
    with make_client() as waiter, make_client() as writer:
        token = waiter.get("/changes").json()["token"]
        result = {}

        def wait():
            start = time.time()
            result["body"] = waiter.get(f"/changes?since={token}&wait=20").json()
            result["elapsed"] = time.time() - start

        thread = threading.Thread(target=wait)
        thread.start()
        time.sleep(0.5)
        writer.put("/settings", json={"settings": {"rates": {"x": 1}}})
        thread.join(10)
        assert result["body"]["token"] != token
        assert result["elapsed"] < 5  # 20초를 다 기다리지 않고 저장 직후 깨어난다


def test_changes_blocked_outside_lan(data_dir):
    with make_client(("8.8.8.8", 1)) as c:
        assert c.get("/changes").status_code == 403


def test_manual_backup_endpoint_and_list(client, data_dir):
    client.put(url("A"), json={"payload": payload(), "base_mtime": None})
    res = client.post("/backup")
    assert res.status_code == 200
    info = res.json()
    assert info["ok"] and info["name"].startswith("manual_") and info["size"] > 0 and info["kind"] == "manual"
    path = os.path.join(config.backup_dir(), info["name"])
    snap = sqlite3.connect(path)
    try:
        assert snap.execute("select count(*) from sqlite_master").fetchone()[0] > 0
    finally:
        snap.close()
    names = [e["name"] for e in client.get("/backup").json()["entries"]]
    assert info["name"] in names


def test_manual_backup_prune_keeps_latest_and_spares_auto(client, data_dir, monkeypatch):
    monkeypatch.setattr(backup, "MANUAL_KEEP", 3)
    directory = config.backup_dir()
    os.makedirs(directory, exist_ok=True)
    for i in range(5):
        open(os.path.join(directory, f"manual_2000010{i}_000000.db"), "wb").close()
    auto = os.path.join(directory, "estimate_20000101_000000.db")
    open(auto, "wb").close()
    client.post("/backup")
    manual = sorted(n for n in os.listdir(directory) if n.startswith("manual_"))
    assert len(manual) == 3 and "manual_20000100_000000.db" not in manual
    assert os.path.exists(auto)


def test_backup_blocked_outside_lan(data_dir):
    with make_client(("8.8.8.8", 50000)) as outsider:
        assert outsider.post("/backup").status_code == 403
        assert outsider.get("/backup").status_code == 403


# ---------- 편집 암호 (v1.2.0) ----------

def set_pw(client, new, current=""):
    return client.post("/auth/password", json={"current": current, "new": new})


def test_no_password_means_open_as_before(client):
    assert client.get("/auth/status").json()["protected"] is False
    assert client.get("/health").json()["edit_protected"] is False
    assert client.put(url("A"), json={"payload": payload(), "base_mtime": None}).status_code == 200
    assert client.post("/backup").status_code == 200


def test_password_blocks_writes_but_not_reads(client):
    client.put(url("A"), json={"payload": payload(), "base_mtime": None})
    res = set_pw(client, "1234")
    assert res.status_code == 200 and res.json()["token"]
    token = res.json()["token"]
    assert client.get("/health").json()["edit_protected"] is True
    # 읽기는 그대로
    assert client.get("/estimates").status_code == 200
    assert client.get(url("A")).status_code == 200
    assert client.get("/settings").status_code == 200
    assert client.get("/changes").status_code == 200
    assert client.get("/backup").status_code == 200
    # 쓰기는 토큰이 없으면 401
    body = {"payload": payload(), "base_mtime": None}
    assert client.put(url("B"), json=body).status_code == 401
    assert client.put(url("A"), json=body, headers={"X-Edit-Token": "wrong"}).status_code == 401
    assert client.delete(url("A")).status_code == 401
    assert client.put("/settings", json={"settings": {"x": 1}}).status_code == 401
    assert client.post("/backup").status_code == 401
    # 토큰이 있으면 통과
    h = {"X-Edit-Token": token}
    assert client.put(url("B"), json=body, headers=h).status_code == 200
    assert client.put("/settings", json={"settings": {"x": 1}}, headers=h).status_code == 200
    assert client.post("/backup", headers=h).status_code == 200
    assert client.delete(url("B"), headers=h).status_code == 200


def test_login_and_token_survives_restart(data_dir):
    with make_client() as c:
        token = set_pw(c, "pass1").json()["token"]
        assert c.post("/auth/login", json={"password": "pass1"}).json()["token"] == token
        bad = c.post("/auth/login", json={"password": "nope"})
        assert bad.status_code == 401 and bad.json()["reason"] == "bad_password"
    with make_client() as c:   # 서버 재시작과 같다(캐시 초기화)
        assert c.get("/auth/status").json()["protected"] is True
        assert c.put(url("A"), json={"payload": payload(), "base_mtime": None},
                     headers={"X-Edit-Token": token}).status_code == 200


def test_hash_only_stored_and_change_invalidates_token(client, data_dir):
    old = set_pw(client, "secret-pw").json()["token"]
    raw = sqlite3.connect(config.db_path()).execute(
        "select value from meta where key='edit_password'").fetchone()[0]
    assert "secret-pw" not in raw and raw.startswith("pbkdf2$")
    assert set_pw(client, "newpass", current="wrong").status_code == 401
    new = set_pw(client, "newpass", current="secret-pw").json()["token"]
    assert new != old
    body = {"payload": payload(), "base_mtime": None}
    assert client.put(url("A"), json=body, headers={"X-Edit-Token": old}).status_code == 401
    assert client.put(url("A"), json=body, headers={"X-Edit-Token": new}).status_code == 200


def test_clear_password_reopens(client):
    set_pw(client, "abcd")
    assert set_pw(client, "", current="zzzz").status_code == 401
    assert set_pw(client, "", current="abcd").json()["protected"] is False
    assert client.put(url("A"), json={"payload": payload(), "base_mtime": None}).status_code == 200


def test_password_rules_and_throttle(client):
    assert set_pw(client, "abc").status_code == 400          # 4자 미만
    set_pw(client, "abcd")
    for _ in range(5):
        assert client.post("/auth/login", json={"password": "bad"}).status_code == 401
    blocked = client.post("/auth/login", json={"password": "abcd"})   # 맞는 암호도 잠시 막는다
    assert blocked.status_code == 429


def test_auth_routes_blocked_outside_lan(data_dir):
    with make_client(("8.8.8.8", 50000)) as outsider:
        assert outsider.post("/auth/login", json={"password": "x"}).status_code == 403
        assert outsider.post("/auth/password", json={"new": "abcd"}).status_code == 403


def test_changes_reports_protection_and_changes_token(client):
    before = client.get("/changes").json()
    assert before["protected"] is False and before["edit_rev"] == ""
    token = set_pw(client, "abcd").json()["token"]
    after = client.get("/changes").json()
    assert after["protected"] is True and after["token"] != before["token"]
    assert after["edit_rev"] == auth_module.edit_rev(token)
    other = set_pw(client, "efgh", current="abcd").json()["token"]
    assert client.get("/changes").json()["edit_rev"] == auth_module.edit_rev(other) != after["edit_rev"]


def test_reset_env_clears_password_on_startup(data_dir, monkeypatch):
    with make_client() as c:
        set_pw(c, "abcd")
        assert c.get("/auth/status").json()["protected"] is True
    monkeypatch.setattr(config, "RESET_EDIT_PASSWORD", True)
    with make_client() as c:
        assert c.get("/auth/status").json()["protected"] is False
        assert c.put(url("A"), json={"payload": payload(), "base_mtime": None}).status_code == 200
