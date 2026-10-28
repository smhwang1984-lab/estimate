"""서버 API 테스트. 저장소 루트에서:  python -m pytest estimate_server/tests -q"""

import os
import sqlite3
import time
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from estimate_server import app as app_module
from estimate_server import backup, config, store

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
