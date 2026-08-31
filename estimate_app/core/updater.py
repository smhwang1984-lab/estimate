"""설치 폴더의 update 폴더에 새 설치 파일이 놓였는지 확인한다.

관리자가 {설치폴더}\\update 에 새 버전 설치 파일(.exe)을 복사해 두면
다음 실행 때 프로그램이 그것을 발견하고 실행 여부를 묻는다.
같은 파일로 반복해서 묻지 않도록 처리한 이력을 사용자 폴더에 남긴다.
"""

import os

from . import paths
from .model import parse_version

UPDATE_DIR_NAME = "update"
UPDATE_STATE_FILE = "update_state.txt"


def get_update_dir():
    return os.path.join(paths.get_app_dir(), UPDATE_DIR_NAME)


def _get_state_path():
    return paths.get_user_file(UPDATE_STATE_FILE)


def read_applied():
    try:
        with open(_get_state_path(), "r", encoding="utf-8") as state_file:
            return {line.strip() for line in state_file if line.strip()}
    except OSError:
        return set()


def mark_applied(marker):
    state_path = _get_state_path()
    try:
        os.makedirs(os.path.dirname(state_path), exist_ok=True)
        with open(state_path, "a", encoding="utf-8") as state_file:
            state_file.write(marker + "\n")
    except OSError:
        pass


def find_new_installer(current_version):
    """설치할 만한 새 파일이 있으면 (파일명, 경로, 마커), 없으면 None."""
    update_dir = get_update_dir()
    if not os.path.isdir(update_dir):
        return None
    current = parse_version(current_version) or (0, 0, 0)
    applied = read_applied()
    candidates = []
    for name in os.listdir(update_dir):
        if not name.lower().endswith(".exe"):
            continue
        path = os.path.join(update_dir, name)
        try:
            marker = f"{name}|{int(os.path.getmtime(path))}"
        except OSError:
            continue
        # 파일명에 적힌 버전이 지금 버전 이하이거나, 이미 처리한 파일이면 건너뛴다.
        file_version = parse_version(name)
        if file_version is not None and file_version <= current:
            continue
        if marker in applied:
            continue
        candidates.append((os.path.getmtime(path), name, path, marker))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    _, name, path, marker = candidates[0]
    return name, path, marker
