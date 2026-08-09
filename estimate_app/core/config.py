"""assets 폴더의 JSON 설정(theme.json, rates.json)을 읽어 온다.

JSON 파일이 없거나 망가져도 프로그램이 뜨지 않는 일이 없도록,
코드 안에 같은 값의 기본값을 두고 파일 내용을 그 위에 덮어쓰는 방식으로 읽는다.
"""

import json

from . import paths

DEFAULT_COLORS = {
    # v0.0.8: 밝은 그라데이션 테마로 전환. 모든 글자/배경 조합은 WCAG 상대휘도 공식으로
    # 명도차를 직접 계산해 통과시킨 값이다(본문 4.5:1 / 큰 글자·배지 3:1 이상).
    # panel은 헤더 바 색이 아니라 ttk 위젯 전체(TFrame/TLabel/TLabelframe 등)의 배경색이므로
    # 반드시 밝은 값을 유지해야 한다 — 팝업창이 ttk 위젯 위주라 여기가 어긋나면 팝업 전체가
    # 강조색으로 덮인다. 헤더 그라데이션은 grad_from/grad_to 두 키로 따로 그린다.
    "bg": "#f5f6fa", "panel": "#ffffff", "panel_2": "#eef1fb", "card": "#ffffff",
    "card_alt": "#f7f9ff", "line": "#e3e7f2", "text": "#1c2436", "muted": "#616b82",
    "accent": "#6553f0", "accent_2": "#2f6fd0", "success_bg": "#e3f6ec",
    "success_fg": "#0f7a44", "warn_bg": "#fff3e0", "warn_fg": "#9a5b00",
    "danger_bg": "#fdeaec", "danger_fg": "#b3252f",
    "new_bg": "#fff2d9", "new_fg": "#8a5800", "new_border": "#e8bd6a",
    "status_border_ok": "#46c98b", "status_border_warn": "#eda23b",
    "status_border_danger": "#e5606c",
    # 헤더 바 그라데이션(보라->파랑) 및 그 위에 얹는 글자색.
    "grad_from": "#6553f0", "grad_to": "#2a76c4", "grad_fallback": "#6553f0",
    "panel_fg": "#ffffff", "panel_muted_fg": "#dde4ff",
    # 체크박스 테두리 전용. line(#e3e7f2)은 밝은 배경끼리는 거의 안 보여서
    # 흰 바탕에서도 또렷하도록 더 진한 색을 따로 둔다(대비 3.4:1).
    "checkbox_border": "#8089b5",
    # 현황판 표(TSERP #tbl) 전용 색.
    # v0.0.8: 행 사이 구분선(위/아래 바)을 없앴다 — 선택된 행이 많으면 두꺼운 줄무늬처럼
    # 보여 어색하다는 지적을 받았다. 선택 표시는 줄 대신 행 배경을 옅게 물들이는 방식으로 바꿨다.
    "pane_head_bg": "#eef1fb", "pane_head_fg": "#616b82",
    "th_bg": "#f0f3fc", "th_fg": "#2b3550", "th_underline": "#6553f0",
    "row_bg": "#ffffff", "row_alt_bg": "#f9fbff", "row_hover": "#eef4ff",
    "row_selected_bg": "#f0eefe",
}

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
    "window_size": "1380x760",
    "min_width": 1320,
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
    "col_material_width": 120,
    "col_size_width": 150,
    "col_status_width": 100,
    "col_price_width": 150,
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


def load_theme():
    payload = _read_json("theme.json")
    return {
        "colors": _merged(DEFAULT_COLORS, payload.get("colors")),
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
