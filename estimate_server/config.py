"""서버 설정. 값은 전부 환경변수(.env → docker-compose.yml)로 바꾼다.

TSERP 서버와는 코드·DB·컨테이너·버전을 하나도 공유하지 않는다. 같은 NAS에서 돌 뿐이다.
"""

import ipaddress
import os

SERVER_VERSION = "1.2.0"
# 클라이언트가 /health에서 이 값을 보고 자기와 맞는 서버인지 판단한다. 요청·응답 형식을
# 호환되지 않게 바꿀 때만 올린다(클라이언트 core/remote.py의 API_VERSION과 짝).
API_VERSION = 1

DATA_DIR = os.environ.get("ESTIMATE_DATA_DIR", "/data")
DB_FILE = "estimate.db"
BACKUP_DIR_NAME = "backup"

# 사내망 대역. 이 밖에서 온 요청은 전부 거부한다(로그인이 없으므로 접속 IP가 유일한 관문).
ALLOWED_CIDRS_ENV = "ESTIMATE_ALLOWED_CIDRS"
ALLOWED_CIDRS_DEFAULT = "192.168.0.0/24,192.168.10.0/24"

BACKUP_ENABLED = str(os.environ.get("ESTIMATE_BACKUP_ENABLED", "1")).strip() not in ("0", "false", "False")
# TSERP DB 백업(23:30)과 겹치지 않게 10분 뒤로 둔다.
BACKUP_AT = str(os.environ.get("ESTIMATE_BACKUP_AT", "23:40")).strip()
BACKUP_RETENTION_DAYS = int(os.environ.get("ESTIMATE_BACKUP_RETENTION_DAYS", "30") or 30)

TITLE_MAX = 120

# 편집 암호를 잊었을 때: .env에 1을 적고 컨테이너를 다시 띄우면 시작할 때 암호를 지운다(DEPLOY_Synology.md 5).
RESET_EDIT_PASSWORD = str(os.environ.get("ESTIMATE_RESET_EDIT_PASSWORD", "0")).strip() in ("1", "true", "True")


def allowed_networks():
    raw = str(os.environ.get(ALLOWED_CIDRS_ENV, "") or ALLOWED_CIDRS_DEFAULT)
    nets = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            nets.append(ipaddress.ip_network(part, strict=False))
        except ValueError:
            continue
    return nets


def db_path():
    return os.path.join(DATA_DIR, DB_FILE)


def backup_dir():
    return os.path.join(DATA_DIR, BACKUP_DIR_NAME)
