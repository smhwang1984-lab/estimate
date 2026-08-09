"""파일 경로를 한 곳에서 계산한다.

exe로 묶었을 때(onedir)와 소스 그대로 실행할 때의 경로가 서로 달라서,
경로를 만드는 코드는 전부 이 모듈에 모아 둔다.

    get_app_dir()   실행 파일이 놓인 폴더. 설치 폴더({app})와 같다. update 폴더 기준점.
    get_bundle_dir() 프로그램에 같이 묶인 읽기 전용 자원 폴더.
                    onedir로 빌드하면 {app}\\_internal 이고, 소스 실행이면 패키지 폴더다.
    get_user_dir()  사용자별 쓰기 가능 폴더(%LOCALAPPDATA%\\MachineEstimate).
                    설치 폴더는 Program Files라 일반 사용자가 쓸 수 없으므로 저장은 전부 여기로 한다.
"""

import os
import sys

USER_DIR_NAME = "MachineEstimate"


def get_app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_bundle_dir():
    # PyInstaller는 datas를 sys._MEIPASS 아래에 푼다(onedir이면 {app}\_internal).
    bundled = getattr(sys, "_MEIPASS", "")
    if bundled:
        return bundled
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_user_dir():
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    return os.path.join(base, USER_DIR_NAME)


def get_user_file(filename):
    return os.path.join(get_user_dir(), filename)


def ensure_user_dir():
    try:
        os.makedirs(get_user_dir(), exist_ok=True)
        return True
    except OSError:
        return False


def get_asset_path(filename):
    """assets 폴더 안의 설정 파일 경로. 사용자 폴더 사본이 있으면 그쪽을 먼저 쓴다."""
    override = get_user_file(filename)
    if os.path.exists(override):
        return override
    candidates = [
        os.path.join(get_bundle_dir(), "assets", filename),
        os.path.join(get_app_dir(), "assets", filename),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", filename),
    ]
    for path in candidates:
        if os.path.exists(path):
            return os.path.normpath(path)
    return os.path.normpath(candidates[0])


def get_resource_path(filename):
    """견적 양식(견적용.xlsx)처럼 프로그램에 같이 묶인 파일을 찾는다."""
    candidates = [
        os.path.join(get_app_dir(), filename),
        os.path.join(get_bundle_dir(), filename),
        os.path.join(get_bundle_dir(), "assets", filename),
        os.path.join(os.getcwd(), filename),
        os.path.join(os.getcwd(), "견적_산정", "양식", filename),
    ]
    for path in candidates:
        if path and os.path.exists(path):
            return path
    return candidates[0]


# v0.0.9: 날짜별 누적 저장(요청 4-2)을 없애면서 '견적_산정' 폴더를 찾던
# get_estimate_root_dir()도 함께 걷어냈다. 저장 위치는 이제 항상 사용자가 대화상자에서 고른다.
