"""assets 폴더의 JSON 설정(theme.json, rates.json)을 읽어 온다.

JSON 파일이 없거나 망가져도 프로그램이 뜨지 않는 일이 없도록,
코드 안에 같은 값의 기본값을 두고 파일 내용을 그 위에 덮어쓰는 방식으로 읽는다.
"""

import json

from . import paths

def _colors(**kwargs):
    return kwargs


# v0.1.8: TSERP(py/web/style.css)의 다크/라이트 팔레트를 그대로 옮겨 두 벌로 나눴다.
# 예전에는 이 자리에 밝은 팔레트 하나만 있었고, 다크는 실행 중에 못 켜는 참고용
# presets.dark로만 존재했다. rgba() 반투명 값(hover/selected/구분선)은 Tk가 위젯
# 배경에 알파를 못 받아서 배경 위에 미리 합성한 불투명 hex로 바꿔 옮겼다.
DEFAULT_THEMES = {
    "light": _colors(
        bg="#f1f2f4", panel="#ffffff", panel_2="#eef1fb", card="#ffffff",
        card_alt="#f7f9ff", line="#d7dbe1", text="#202733", muted="#6a7686",
        accent="#1c66c2", accent_2="#2f6fd0", success_bg="#e3f6ec",
        success_fg="#1f7a3d", warn_bg="#fff3e0", warn_fg="#8c471f",
        danger_bg="#fdeaec", danger_fg="#b0203a",
        new_bg="#fff2d9", new_fg="#8a5800", new_border="#e8bd6a",
        status_border_ok="#46c98b", status_border_warn="#eda23b",
        status_border_danger="#e5606c",
        # 체크박스 테두리 전용. line은 밝은 배경끼리 거의 안 보여서 더 진한 색을 따로 둔다.
        checkbox_border="#8089b5",
        pane_head_bg="#eef1fb", pane_head_fg="#616b82",
        th_bg="#eaedf1", th_fg="#24344d", th_underline="#4a90d9",
        row_bg="#ffffff", row_alt_bg="#eef0f2", row_hover="#d6e3f4",
        row_selected_bg="#dfeaf6",
        # v0.1.3: 품번이 겹치는 행 표시. danger_bg를 그대로 쓰면 "불가" 배지와 같은 색이라
        # 배지가 행 배경에 묻히므로, 한 단계 노란기를 섞은 별도 색을 둔다.
        row_dup_bg="#fdeee4", row_dup_alt_bg="#fbe6d8", row_dup_fg="#a4400f",
        # v0.1.8: 표 열 구분선(요청 '열 구분선 활성화/비활성화'). 데이터 행 셀 오른쪽에만 긋는다.
        col_divider="#d3d8de",
    ),
    "dark": _colors(
        bg="#11161c", panel="#171d25", panel_2="#234060", card="#171d25",
        card_alt="#1d2530", line="#2a3340", text="#dde4ec", muted="#8b97a7",
        accent="#4fb0ff", accent_2="#9cc8ff", success_bg="#2c5c44",
        success_fg="#7ddc9e", warn_bg="#5a3a1a", warn_fg="#ffb648",
        danger_bg="#40222a", danger_fg="#ff9aa2",
        new_bg="#5a3a1a", new_fg="#ffb648", new_border="#8a5a2a",
        status_border_ok="#3ecf8e", status_border_warn="#d88a4f",
        status_border_danger="#e05561",
        checkbox_border="#333f4e",
        pane_head_bg="#1d2530", pane_head_fg="#8b97a7",
        th_bg="#1a2535", th_fg="#c8d8ec", th_underline="#4fb0ff",
        row_bg="#141b23", row_alt_bg="#171f28", row_hover="#1f364b",
        row_selected_bg="#1d3346",
        row_dup_bg="#3a2318", row_dup_alt_bg="#402719", row_dup_fg="#ffb787",
        col_divider="#2e3a46",
    ),
}
THEME_MODES = tuple(DEFAULT_THEMES.keys())
DEFAULT_THEME_MODE = "light"

DEFAULT_FONTS = {
    "family": "맑은 고딕",
    "normal_size": 13,
    "small_size": 11,
    "title_size": 21,
    "card_title_size": 17,
    # v0.0.8: 표 본문은 일반 글꼴로 바꿨다(고정폭은 품번/품명/소재가 부자연스럽게 벌어짐).
    # num_family는 금액·수량처럼 자릿수를 맞춰야 하는 열에만 따로 적용한다.
    "table_family": "맑은 고딕",
    "num_family": "Consolas",
    "table_head_px": 18,
    "table_cell_px": 17,
    "table_sub_px": 13,
    "pane_head_px": 12,
    "badge_px": 14,
}

DEFAULT_LAYOUT = {
    "window_size": "1460x780",
    "min_width": 1420,
    "min_height": 680,
    "checkbox_size": 26,
    "page_size": 40,
    "cell_pad_x": 8,
    "cell_pad_y": 6,
    # v0.0.9: 맨 앞 No 열과 Comment 열이 늘어난 만큼(요청 1-3, 1-4) 나머지 열을 조금씩 줄였다.
    "col_no_width": 46,
    "col_check_width": 50,
    "col_model_width": 120,
    "col_partno_width": 180,
    "col_partname_width": 220,
    "col_comment_width": 170,
    # v0.1.0: 소재 칸이 좁아 기본 소재 목록 대부분이 잘렸다(요청 3-4). 30px 넓히고,
    # 여유가 있던 금액 칸에서 같은 만큼 덜어 전체 폭 합계는 그대로 뒀다(1억 단위까지도
    # 120px에 들어가는 것을 실측해 확인함).
    "col_material_width": 150,
    "col_heat_width": 100,
    "col_size_width": 150,
    "col_status_width": 100,
    "col_price_width": 120,
}

DEFAULT_RATES = {
    "m_5axis": 70000, "m_4axis": 50000, "m_3axis": 40000, "m_lathe": 35000,
    "m_general": 20000, "m_finish": 15600, "m_cmm": 30000, "m_grind": 35000,
    "m_jig": 35000, "m_prog": 35000,
}

DEFAULT_LABELS = {
    "m_5axis": "5축", "m_4axis": "4축", "m_3axis": "3축", "m_lathe": "선반",
    "m_general": "범용", "m_finish": "사상", "m_cmm": "3차원", "m_grind": "연마",
    "m_jig": "지그", "m_prog": "프로그래밍",
}

# 엑셀 K~T열(11~20)과 1:1로 대응하는 순서다. 순서를 바꾸면 저장 위치가 어긋난다.
MACHINE_KEYS = ["m_5axis", "m_4axis", "m_3axis", "m_lathe", "m_general",
                "m_finish", "m_cmm", "m_grind", "m_jig", "m_prog"]


def _read_json(filename):
    try:
        with open(paths.get_asset_path(filename), "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return payload if isinstance(payload, dict) else {}
    except (OSError, ValueError):
        return {}


def _merged(defaults, override):
    merged = dict(defaults)
    if isinstance(override, dict):
        for key, value in override.items():
            if key in merged:
                merged[key] = value
    return merged


def load_theme(mode=DEFAULT_THEME_MODE):
    """mode("light"/"dark")에 맞는 팔레트 한 벌만 읽는다. 잘못된 값은 라이트로 접어 둔다."""
    if mode not in THEME_MODES:
        mode = DEFAULT_THEME_MODE
    payload = _read_json("theme.json")
    themes_payload = payload.get("themes")
    theme_override = themes_payload.get(mode) if isinstance(themes_payload, dict) else None
    return {
        "colors": _merged(DEFAULT_THEMES[mode], theme_override),
        "fonts": _merged(DEFAULT_FONTS, payload.get("fonts")),
        "layout": _merged(DEFAULT_LAYOUT, payload.get("layout")),
    }


def load_rates():
    payload = _read_json("rates.json")
    rates = _merged(DEFAULT_RATES, payload.get("rates"))
    # 단가를 문자열로 적어 두는 실수를 대비해 숫자로 바꿔 둔다.
    for key, value in rates.items():
        try:
            rates[key] = float(value)
        except (TypeError, ValueError):
            rates[key] = DEFAULT_RATES[key]
    return rates


def load_machine_labels():
    payload = _read_json("rates.json")
    return _merged(DEFAULT_LABELS, payload.get("labels"))


def get_machine_fields():
    """(키, 표시이름) 목록. 화면 표와 엑셀 열 순서가 이 순서를 따른다."""
    labels = load_machine_labels()
    return [(key, labels[key]) for key in MACHINE_KEYS]
