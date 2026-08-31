"""화면 표시 개인 설정(v0.1.8 신설, TSERP의 ui_display_prefs.json과 같은 자리).

다크/라이트, 표 구분선, 표 글자 크기 배율을 담는다. 이 값들은 반드시 이 PC에만
저장한다 — `core/settings.py`(공정 단가·Material 등)는 v0.1.4부터 사용자가 공유
폴더로 옮길 수 있는데, 화면 취향까지 거기 같이 담으면 한 사람이 다크로 바꾸는 순간
그 폴더를 쓰는 모든 PC가 같이 바뀐다. TSERP도 같은 이유로 이 값을 서버/DB와 무관한
PC 로컬 파일로 따로 둔다.

저장 위치는 항상 `%LOCALAPPDATA%\\MachineEstimate\\display_prefs.json`이다(공유 폴더
설정과 무관하게 고정 — `core/datastore.py`의 판정을 거치지 않는다).
"""

from . import datastore, paths

PREFS_FILE = "display_prefs.json"

THEME_MODES = ("light", "dark")
DEFAULT_THEME_MODE = "light"
DEFAULT_DIVIDERS = True
FONT_SCALE_MIN = 70
FONT_SCALE_MAX = 150
FONT_SCALE_STEP = 5
DEFAULT_FONT_SCALE = 100


def _get_path():
    return paths.get_user_file(PREFS_FILE)


def clamp_font_scale(value):
    """70~150을 5단위로 반올림한다. 표 글자 크기 배율 스테퍼·단축키가 함께 쓴다."""
    try:
        value = int(round(float(value) / FONT_SCALE_STEP) * FONT_SCALE_STEP)
    except (TypeError, ValueError):
        return DEFAULT_FONT_SCALE
    return max(FONT_SCALE_MIN, min(FONT_SCALE_MAX, value))


def load():
    """{"theme_mode": str, "dividers": bool, "font_scale": int}. 없거나 깨졌으면 기본값."""
    payload, error = datastore.read_json(_get_path())
    if error or not isinstance(payload, dict):
        payload = {}
    theme_mode = payload.get("theme_mode")
    if theme_mode not in THEME_MODES:
        theme_mode = DEFAULT_THEME_MODE
    dividers = payload.get("dividers")
    if not isinstance(dividers, bool):
        dividers = DEFAULT_DIVIDERS
    return {
        "theme_mode": theme_mode,
        "dividers": dividers,
        "font_scale": clamp_font_scale(payload.get("font_scale", DEFAULT_FONT_SCALE)),
    }


def save(prefs):
    """받은 값 그대로 덮어쓴다. 실패해도(권한 등) 화면 동작은 계속되며 다음에 다시 시도한다."""
    theme_mode = prefs.get("theme_mode")
    if theme_mode not in THEME_MODES:
        theme_mode = DEFAULT_THEME_MODE
    payload = {
        "theme_mode": theme_mode,
        "dividers": bool(prefs.get("dividers", DEFAULT_DIVIDERS)),
        "font_scale": clamp_font_scale(prefs.get("font_scale", DEFAULT_FONT_SCALE)),
    }
    return datastore.write_json_atomic(_get_path(), payload)
