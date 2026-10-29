"""매일 한 번 SQLite 스냅샷을 {데이터 폴더}/backup/에 남긴다.

파일 복사가 아니라 sqlite3 백업 API를 쓴다 — 쓰는 도중의 DB를 그대로 복사하면 반쯤
쓰인 상태가 찍힐 수 있다. 보관 기간이 지난 스냅샷은 지운다.
NAS의 Hyper Backup이 이 폴더를 한 번 더 보관하게 해 두기를 권한다(DEPLOY_Synology.md).
"""

import os
import sqlite3
import threading
import time
from datetime import datetime, timedelta

from . import config, store

PREFIX = "estimate_"
MANUAL_PREFIX = "manual_"   # v1.2.0: 화면의 [데이터 백업] 단추로 만든 것. 날짜 기준 자동 삭제 대상이 아니다.
SUFFIX = ".db"
MANUAL_KEEP = 50
RESTORE_PREFIX = "before_restore_"   # v1.3.0: 복원 직전 상태. 복원을 되돌릴 수 있게 남긴다.
RESTORE_KEEP = 10
LIST_LIMIT = 30
_last_run_day = None
_manual_lock = threading.Lock()
_restore_lock = threading.Lock()


def _snapshot(prefix):
    directory = config.backup_dir()
    os.makedirs(directory, exist_ok=True)
    stem = f"{prefix}{datetime.now():%Y%m%d_%H%M%S}"
    target = os.path.join(directory, stem + SUFFIX)
    extra = 1
    while os.path.exists(target):   # 같은 초에 또 만들면 기존 파일을 덮지 않는다(복원 직후 바로 되돌릴 때 그 파일이 원본이다)
        extra += 1
        target = os.path.join(directory, f"{stem}_{extra}{SUFFIX}")
    source = store.connect()
    try:
        dest = sqlite3.connect(target)
        try:
            source.backup(dest)
        finally:
            dest.close()
    finally:
        source.close()
    return target


def run_backup():
    """스냅샷 한 개를 만들고 오래된 것을 지운다. 만든 파일 경로를 돌려준다."""
    target = _snapshot(PREFIX)
    prune(os.path.dirname(target))
    return target


def run_manual_backup():
    """사용자가 누른 백업. 파일 정보를 돌려주고, 수동 백업이 MANUAL_KEEP개를 넘으면 오래된 것부터 지운다."""
    with _manual_lock:   # 동시에 눌러도 같은 파일 이름·정리가 겹치지 않게
        target = _snapshot(MANUAL_PREFIX)
        _prune_manual(os.path.dirname(target))
    return _describe(target)


def _prune_manual(directory):
    names = sorted(n for n in os.listdir(directory) if n.startswith(MANUAL_PREFIX) and n.endswith(SUFFIX))
    for name in names[:-MANUAL_KEEP]:
        try:
            os.remove(os.path.join(directory, name))
        except OSError:
            continue


def _describe(path):
    stat = os.stat(path)
    name = os.path.basename(path)
    return {"name": name, "size": stat.st_size,
            "created_at": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            "kind": "manual" if name.startswith(MANUAL_PREFIX)
            else "restore" if name.startswith(RESTORE_PREFIX) else "auto"}


def list_backups(limit=LIST_LIMIT):
    """최근 백업(자동·수동) 목록, 새것부터."""
    directory = config.backup_dir()
    if not os.path.isdir(directory):
        return []
    found = []
    for name in os.listdir(directory):
        if name.endswith(SUFFIX) and name.startswith((PREFIX, MANUAL_PREFIX, RESTORE_PREFIX)):
            try:
                found.append(_describe(os.path.join(directory, name)))
            except OSError:
                continue
    found.sort(key=lambda e: (e["created_at"], e["name"]), reverse=True)
    found = found[:limit]
    for entry in found:
        entry["estimates"] = _count_estimates(os.path.join(directory, entry["name"]))
    return found


def _count_estimates(path):
    """백업 안의 (지워지지 않은) 견적 개수. 읽지 못하면 None."""
    try:
        conn = sqlite3.connect("file:" + path.replace("\\", "/") + "?mode=ro", uri=True, timeout=5)
        try:
            return conn.execute("SELECT COUNT(*) FROM estimates WHERE deleted_at IS NULL").fetchone()[0]
        finally:
            conn.close()
    except sqlite3.Error:
        return None


class RestoreError(Exception):
    def __init__(self, reason, msg):
        super().__init__(msg)
        self.reason = reason
        self.msg = msg


def _backup_path(name):
    """목록에 나오는 백업 파일 이름만 받는다(경로 문자가 섞이면 거부 — 폴더 밖 파일을 못 쓰게)."""
    name = str(name or "")
    if (os.path.basename(name) != name or not name.endswith(SUFFIX)
            or not name.startswith((PREFIX, MANUAL_PREFIX, RESTORE_PREFIX))):
        raise RestoreError("bad_name", "백업 파일 이름이 올바르지 않습니다.")
    path = os.path.join(config.backup_dir(), name)
    if not os.path.isfile(path):
        raise RestoreError("missing", "백업 파일이 없습니다.")
    return path


def restore_backup(name):
    """선택한 백업으로 DB 내용을 되돌린다. 먼저 지금 상태를 before_restore_ 파일로 남긴다.

    파일을 바꿔 끼우지 않고 sqlite 백업 API로 '백업 → 지금 DB'에 덮어쓴다 — 서버가 DB를 열어 둔 채여도
    안전하고, 쓰기 중인 요청은 잠금으로 잠깐 기다린다. 편집 암호는 지금 값을 그대로 유지한다(백업 시점에
    암호가 없었어도 복원이 암호를 지우지 못하게). library_rev는 지금보다 반드시 커지게 해서 모든 PC가
    변경을 알아차리게 한다.
    """
    path = _backup_path(name)
    try:
        probe = sqlite3.connect("file:" + path.replace("\\", "/") + "?mode=ro", uri=True, timeout=5)
        try:
            ok = probe.execute("PRAGMA quick_check").fetchone()[0] == "ok"
            tables = {r[0] for r in probe.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        finally:
            probe.close()
    except sqlite3.Error:
        raise RestoreError("broken", "백업 파일을 읽을 수 없습니다.")
    if not ok or not {"meta", "settings", "estimates"} <= tables:
        raise RestoreError("broken", "백업 파일이 손상됐거나 견적 DB가 아닙니다.")

    with _restore_lock:
        safety = os.path.basename(_snapshot(RESTORE_PREFIX))
        _prune_prefix(config.backup_dir(), RESTORE_PREFIX, RESTORE_KEEP)
        keep_password = store.get_meta("edit_password")
        live = store.connect()
        try:
            rev_row = live.execute("SELECT value FROM meta WHERE key = 'library_rev'").fetchone()
            before_rev = int(rev_row["value"]) if rev_row else 0
            source = sqlite3.connect(path)
            try:
                source.backup(live)
            finally:
                source.close()
            row = live.execute("SELECT value FROM meta WHERE key = 'library_rev'").fetchone()
            restored_rev = int(row["value"]) if row else 0
            live.execute("INSERT INTO meta (key, value) VALUES ('library_rev', ?)"
                         " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                         (str(max(before_rev, restored_rev) + 1),))
            if keep_password is None:
                live.execute("DELETE FROM meta WHERE key = 'edit_password'")
            else:
                live.execute("INSERT INTO meta (key, value) VALUES ('edit_password', ?)"
                             " ON CONFLICT(key) DO UPDATE SET value = excluded.value", (keep_password,))
        finally:
            live.close()
    return {"restored": os.path.basename(path), "safety": safety}


def _prune_prefix(directory, prefix, keep):
    names = sorted(n for n in os.listdir(directory) if n.startswith(prefix) and n.endswith(SUFFIX))
    for name in names[:-keep]:
        try:
            os.remove(os.path.join(directory, name))
        except OSError:
            continue


def prune(directory):
    cutoff = datetime.now() - timedelta(days=config.BACKUP_RETENTION_DAYS)
    for name in os.listdir(directory):
        if not (name.startswith(PREFIX) and name.endswith(SUFFIX)):
            continue
        path = os.path.join(directory, name)
        try:
            if datetime.fromtimestamp(os.path.getmtime(path)) < cutoff:
                os.remove(path)
        except OSError:
            continue


def _due(now):
    try:
        hour, minute = (int(part) for part in config.BACKUP_AT.split(":"))
    except ValueError:
        hour, minute = 23, 40
    return now.hour * 60 + now.minute >= hour * 60 + minute


def _loop():
    global _last_run_day
    while True:
        now = datetime.now()
        if _last_run_day != now.date() and _due(now):
            _last_run_day = now.date()
            try:
                print(f"[backup] {run_backup()}", flush=True)
            except Exception as exc:  # 백업 실패가 서버를 멈추면 안 된다
                print(f"[backup] failed: {exc}", flush=True)
        time.sleep(60)


def start_scheduler():
    global _last_run_day
    if not config.BACKUP_ENABLED:
        return
    # 정해진 시각이 지난 뒤 서버가 켜졌다면 그날 것은 건너뛴다(재시작마다 백업이 쌓이지 않게).
    if _due(datetime.now()):
        _last_run_day = datetime.now().date()
    threading.Thread(target=_loop, daemon=True, name="estimate-backup").start()
