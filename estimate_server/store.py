"""SQLite 저장소. 서버 프로세스만 이 파일을 연다 — PC가 SMB로 직접 열면 깨질 수 있다.

## mtime(버전 표시)

클라이언트의 보관함(core/library.py)은 파일 수정 시각(mtime)으로 "내가 불러온 뒤 남이
고쳤는가"를 판정한다. 서버도 같은 이름·같은 단위(초)의 값을 돌려줘서 화면 코드를 그대로
쓰게 했다. 다만 파일 mtime과 달리 **같은 견적 안에서는 반드시 커진다** —
`max(지금 초, 이전 값 + 1)`. 같은 초에 두 번 저장해도 값이 갈라져 충돌 판정이 빗나가지 않는다.

## 저장 충돌

견적 저장은 `base_mtime`(클라이언트가 마지막으로 본 값, 없던 견적이면 None)이 지금 값과
같을 때만 받는다. 다르면 ConflictError — 판정과 쓰기를 `BEGIN IMMEDIATE` 한 트랜잭션에서
해서, 두 PC가 동시에 저장해도 둘 다 통과하는 일이 없다.

## 변경 알림(v1.1.0)

`meta.library_rev`는 보관함에 무엇이든 쓰일 때마다(저장·삭제) 1씩 오른다. 설정의 mtime과
합쳐 `change_state()`의 token이 된다 — 클라이언트는 이 token이 바뀌었는지만 보고
"무엇이 바뀌었는지"는 설정 mtime·자기 견적의 mtime으로 따로 확인한다. DB에서 계산하므로
서버를 재시작해도 값이 이어진다.

## 삭제

지우지 않고 `deleted_at`만 적는다. 공유 보관함에서 남이 지운 견적을 서버 관리자가
되살릴 수 있게 하기 위해서다. 같은 이름으로 다시 저장하면 그 행을 되살려 쓴다.
"""

import json
import os
import sqlite3
import time
from contextlib import closing
from datetime import datetime

from . import config

SCHEMA_VERSION = 1


class ConflictError(Exception):
    def __init__(self, current_mtime):
        super().__init__("conflict")
        self.current_mtime = current_mtime


def _now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _next_mtime(previous):
    return max(int(time.time()), int(previous or 0) + 1)


def connect():
    conn = sqlite3.connect(config.db_path(), timeout=10, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 10000")
    return conn


def init_db():
    os.makedirs(config.DATA_DIR, exist_ok=True)
    with closing(connect()) as conn:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS meta (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS settings (
                id         INTEGER PRIMARY KEY CHECK (id = 1),
                payload    TEXT    NOT NULL,
                mtime      INTEGER NOT NULL,
                updated_at TEXT    NOT NULL,
                updated_by TEXT    NOT NULL DEFAULT '',
                ip         TEXT    NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS estimates (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT    NOT NULL UNIQUE,
                payload     TEXT    NOT NULL,
                item_count  INTEGER NOT NULL DEFAULT 0,
                mtime       INTEGER NOT NULL,
                saved_at    TEXT    NOT NULL,
                saved_by    TEXT    NOT NULL DEFAULT '',
                app_version TEXT    NOT NULL DEFAULT '',
                ip          TEXT    NOT NULL DEFAULT '',
                deleted_at  TEXT,
                deleted_by  TEXT    NOT NULL DEFAULT ''
            );
        """)
        conn.execute("INSERT OR IGNORE INTO meta (key, value) VALUES ('schema_version', ?)",
                     (str(SCHEMA_VERSION),))
        conn.execute("INSERT OR IGNORE INTO meta (key, value) VALUES ('library_rev', '0')")


def _bump_library_rev(conn):
    conn.execute("UPDATE meta SET value = CAST(CAST(value AS INTEGER) + 1 AS TEXT)"
                 " WHERE key = 'library_rev'")


def change_state():
    """지금 데이터의 변경 표시. 무엇이든 바뀌면 token이 달라진다."""
    with closing(connect()) as conn:
        row = conn.execute("SELECT mtime FROM settings WHERE id = 1").fetchone()
        rev = conn.execute("SELECT value FROM meta WHERE key = 'library_rev'").fetchone()
    settings_mtime = row["mtime"] if row else 0
    library_rev = int(rev["value"]) if rev else 0
    return {"token": f"{settings_mtime}-{library_rev}",
            "settings_mtime": settings_mtime, "library_rev": library_rev}


def check_db():
    """DB를 실제로 읽어 본다. /health가 쓴다."""
    try:
        with closing(connect()) as conn:
            row = conn.execute("SELECT value FROM meta WHERE key = 'schema_version'").fetchone()
        return row is not None
    except sqlite3.Error:
        return False


# ---------- 메타(편집 암호 등) ----------

def get_meta(key):
    with closing(connect()) as conn:
        row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def set_meta(key, value):
    with closing(connect()) as conn:
        conn.execute("INSERT INTO meta (key, value) VALUES (?, ?)"
                     " ON CONFLICT(key) DO UPDATE SET value = excluded.value", (key, value))


def delete_meta(key):
    with closing(connect()) as conn:
        conn.execute("DELETE FROM meta WHERE key = ?", (key,))


# ---------- 설정 ----------

def get_settings():
    with closing(connect()) as conn:
        row = conn.execute("SELECT * FROM settings WHERE id = 1").fetchone()
    if row is None:
        return None
    return {
        "settings": json.loads(row["payload"]),
        "mtime": row["mtime"],
        "updated_at": row["updated_at"],
        "updated_by": row["updated_by"],
    }


def put_settings(settings, saved_by, ip):
    """설정은 지금 공유 폴더 방식과 같이 마지막에 저장한 쪽이 이긴다."""
    payload = json.dumps(settings, ensure_ascii=False)
    conn = connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT mtime FROM settings WHERE id = 1").fetchone()
        mtime = _next_mtime(row["mtime"] if row else None)
        conn.execute(
            "INSERT INTO settings (id, payload, mtime, updated_at, updated_by, ip)"
            " VALUES (1, ?, ?, ?, ?, ?)"
            " ON CONFLICT(id) DO UPDATE SET payload = excluded.payload, mtime = excluded.mtime,"
            " updated_at = excluded.updated_at, updated_by = excluded.updated_by, ip = excluded.ip",
            (payload, mtime, _now_text(), saved_by, ip))
        conn.execute("COMMIT")
        return mtime
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()


# ---------- 견적 보관함 ----------

def _entry_meta(row):
    return {
        "title": row["title"],
        "saved_at": row["saved_at"],
        "saved_by": row["saved_by"],
        "count": row["item_count"],
        "mtime": row["mtime"],
    }


def list_estimates():
    with closing(connect()) as conn:
        rows = conn.execute(
            "SELECT title, saved_at, saved_by, item_count, mtime FROM estimates"
            " WHERE deleted_at IS NULL ORDER BY mtime DESC").fetchall()
    return [_entry_meta(row) for row in rows]


def get_estimate(title, with_payload=True):
    with closing(connect()) as conn:
        row = conn.execute("SELECT * FROM estimates WHERE title = ? AND deleted_at IS NULL",
                           (title,)).fetchone()
    if row is None:
        return None
    entry = _entry_meta(row)
    if with_payload:
        entry["payload"] = json.loads(row["payload"])
    return entry


def put_estimate(title, payload, base_mtime, saved_by, ip):
    """견적을 저장한다. 성공하면 메타데이터, base_mtime이 어긋나면 ConflictError."""
    items = payload.get("items") if isinstance(payload.get("items"), list) else []
    saved_at = _now_text()
    stored = dict(payload)
    stored.update({"title": title, "saved_at": saved_at, "saved_by": saved_by})
    text = json.dumps(stored, ensure_ascii=False)
    app_version = str(payload.get("app_version") or "")

    conn = connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT mtime, deleted_at FROM estimates WHERE title = ?",
                           (title,)).fetchone()
        live_mtime = row["mtime"] if row is not None and row["deleted_at"] is None else None
        if live_mtime != base_mtime:
            raise ConflictError(live_mtime)
        mtime = _next_mtime(row["mtime"] if row is not None else None)
        if row is None:
            conn.execute(
                "INSERT INTO estimates (title, payload, item_count, mtime, saved_at, saved_by,"
                " app_version, ip) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (title, text, len(items), mtime, saved_at, saved_by, app_version, ip))
        else:
            conn.execute(
                "UPDATE estimates SET payload = ?, item_count = ?, mtime = ?, saved_at = ?,"
                " saved_by = ?, app_version = ?, ip = ?, deleted_at = NULL, deleted_by = ''"
                " WHERE title = ?",
                (text, len(items), mtime, saved_at, saved_by, app_version, ip, title))
        _bump_library_rev(conn)
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()
    return {"title": title, "saved_at": saved_at, "saved_by": saved_by,
            "count": len(items), "mtime": mtime}


def delete_estimate(title, deleted_by, ip):
    """소프트 삭제. 지운 게 있으면 True."""
    conn = connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        cursor = conn.execute(
            "UPDATE estimates SET deleted_at = ?, deleted_by = ?"
            " WHERE title = ? AND deleted_at IS NULL",
            (_now_text(), f"{deleted_by} ({ip})", title))
        deleted = cursor.rowcount > 0
        if deleted:
            _bump_library_rev(conn)
        conn.execute("COMMIT")
        return deleted
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()
