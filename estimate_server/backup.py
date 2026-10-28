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
SUFFIX = ".db"
_last_run_day = None


def run_backup():
    """스냅샷 한 개를 만들고 오래된 것을 지운다. 만든 파일 경로를 돌려준다."""
    directory = config.backup_dir()
    os.makedirs(directory, exist_ok=True)
    target = os.path.join(directory, f"{PREFIX}{datetime.now():%Y%m%d_%H%M%S}{SUFFIX}")
    source = store.connect()
    try:
        dest = sqlite3.connect(target)
        try:
            source.backup(dest)
        finally:
            dest.close()
    finally:
        source.close()
    prune(directory)
    return target


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
