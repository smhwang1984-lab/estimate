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
LIST_LIMIT = 30
_last_run_day = None
_manual_lock = threading.Lock()


def _snapshot(prefix):
    directory = config.backup_dir()
    os.makedirs(directory, exist_ok=True)
    target = os.path.join(directory, f"{prefix}{datetime.now():%Y%m%d_%H%M%S}{SUFFIX}")
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
            "kind": "manual" if name.startswith(MANUAL_PREFIX) else "auto"}


def list_backups(limit=LIST_LIMIT):
    """최근 백업(자동·수동) 목록, 새것부터."""
    directory = config.backup_dir()
    if not os.path.isdir(directory):
        return []
    found = []
    for name in os.listdir(directory):
        if name.endswith(SUFFIX) and (name.startswith(PREFIX) or name.startswith(MANUAL_PREFIX)):
            try:
                found.append(_describe(os.path.join(directory, name)))
            except OSError:
                continue
    found.sort(key=lambda e: (e["created_at"], e["name"]), reverse=True)
    return found[:limit]


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
