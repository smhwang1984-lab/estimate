"""견적 카드 한 건의 자료 구조와, 그 위에서 도는 값 변환·검색 규칙."""

import math
import re
from datetime import datetime

from .config import MACHINE_KEYS

TEXT_KEYS = ["part_no", "part_name", "comment", "material", "size"]
# 검색 대상은 품번/품명/기종 3종류로만 한정한다(Material/Size/Comment/금액 등은 제외).
SEARCH_KEYS = ["part_no", "part_name", "model"]


def create_blank_item(no):
    now = datetime.now()
    item = {
        "no": no,
        "created_at": now.strftime("%Y-%m-%d"),
        "added_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "source_file": "",
        "source_month": "",
        "save_pending": True,
        # NEW는 수정 여부가 아니라 신규 등록 여부다. 기존 품목을 고쳐도 이 값은 바꾸지 않는다.
        "is_new_registration": False,
        "part_no": "",
        "part_name": "",
        "model": "",
        "comment": "",
        "possible": "가능",
        "qty": 1,
        "material": "",
        # v0.0.9: 열처리 여부와 HRC 경도 Min/Max(요청 5-2, 5-3). 기계 시트에 열처리 전용 열이
        # 없어서 엑셀에는 Material 값 뒤에 `HRC00~00` 형태로 붙여 기록한다.
        "heat_treat": False,
        "hrc_min": "",
        "hrc_max": "",
        "size": "",
        # v0.1.0: Size 치수 x 소재 비중으로 계산한 무게(kg, 요청 4). 치수를 모르거나
        # (직접입력) 소재 비중을 못 찾으면 None -- 추측해서 채우지 않는다.
        "weight": None,
    }
    for key in MACHINE_KEYS:
        item[key] = 0.0
    return item


def hrc_text(item):
    """열처리 경도를 `HRC58~62` 한 덩어리로 만든다. 한쪽만 적었으면 그 값만 쓴다."""
    if not item.get("heat_treat"):
        return ""
    low = str(item.get("hrc_min", "")).strip()
    high = str(item.get("hrc_max", "")).strip()
    if low and high:
        return f"HRC{low}~{high}"
    if low or high:
        return f"HRC{low or high}"
    return "HRC"


def material_text(item):
    """엑셀 Material 칸에 실제로 적을 값. 열처리를 체크했으면 경도를 뒤에 붙인다."""
    material = str(item.get("material", "")).strip()
    hardness = hrc_text(item)
    if not hardness:
        return material
    return f"{material} {hardness}".strip()


def calc_weight_kg(shape, t=None, w=None, l=None, d=None, density=None):
    """치수(mm)와 비중(g/cm³)으로 무게(kg, 1개 기준)를 낸다(요청 4-1).

    치수를 모르거나(shape="custom") 비중을 못 찾았으면 None -- 추측해서 채우지 않는다.
    mm³ x g/cm³ 는 그대로 mg이므로 1,000,000으로 나누면 kg이 된다
    (mm³->cm³ /1000, g->kg /1000, 합쳐서 /1e6).
    """
    if density is None:
        return None
    if shape == "block":
        if None in (t, w, l):
            return None
        volume_mm3 = t * w * l
    elif shape == "rod":
        if None in (d, l):
            return None
        volume_mm3 = math.pi * (d / 2) ** 2 * l
    else:
        return None
    return volume_mm3 * density / 1_000_000


def parse_size(size_text):
    """Size 문자열을 형상과 치수로 되짚는다(v0.1.1).

    카드 팝업(`ui/popup.py`)의 Size 섹션과 가공조건 산출기(`ui/condition_dialog.py`)가
    같은 것을 쓰도록 여기 하나로 모았다 -- 원래 팝업 안에 인라인으로만 있던 로직이다.

    반환: (shape, dims). shape는 "block"/"rod"/"custom"/None(빈 문자열).
    dims는 문자열 값 그대로를 담은 사전이다(숫자 변환은 호출부가 필요할 때 한다):
        block -> {"t","w","l"} (셋 다 있어야 채운다. 하나라도 빠지면 빈 사전)
        rod   -> {"d","l"} (둘 다 있어야 채운다)
        custom -> {"text": 원문 그대로}
    """
    text = str(size_text or "").strip()
    if not text:
        return None, {}
    if "Ø" in text or "D*" in text:
        matches = re.findall(r"[\d\.]+", text)
        if len(matches) >= 2:
            return "rod", {"d": matches[0], "l": matches[1]}
        return "rod", {}
    if "T" in text or "W" in text or "*" in text:
        matches = re.findall(r"[\d\.]+", text)
        if len(matches) >= 3:
            return "block", {"t": matches[0], "w": matches[1], "l": matches[2]}
        return "block", {}
    return "custom", {"text": text}


def get_next_no(items):
    return max([item["no"] for item in items], default=0) + 1


def safe_float(value):
    if value in (None, ""):
        return 0.0
    if isinstance(value, str) and value.strip().startswith("="):
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def safe_int(value, default=1):
    if value in (None, ""):
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def parse_number(text):
    """화면 입력칸의 문자열을 숫자로 바꾼다. 숫자가 아니면 None."""
    text = str(text).strip().replace(",", "")
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return None


def has_item_data(item):
    has_text = any(str(item.get(key, "")).strip() for key in TEXT_KEYS)
    has_time = any(float(item.get(key, 0) or 0) > 0 for key in MACHINE_KEYS)
    return has_text or has_time


def item_matches_search(item, query):
    """부분 일치 검색. 'A34444'를 '444'로도 찾을 수 있고, 공백/쉼표로 여러 조건을 준다."""
    if not query:
        return True
    terms = [term.lower() for term in re.split(r"[\s,]+", query.strip()) if term]
    haystack = " ".join(str(item.get(key, "")).lower() for key in SEARCH_KEYS)
    return all(term in haystack for term in terms)


def filter_items(items, query):
    """(전체 유효 카드, 검색에 걸린 카드) 두 벌을 돌려준다.

    나중에 올린 카드가 위로, 먼저 올린 카드가 아래로 쌓인다(요청 1-1, 1-2).
    업로드는 한 번에 여러 건이 같은 초에 들어와 `added_at`만으로는 순서가 흔들리므로,
    2차 키로 카드 번호를 함께 내림차순 정렬해 순서를 고정한다.
    """
    all_items = [item for item in items if has_item_data(item)]
    all_items.sort(key=lambda item: (item.get("added_at", ""), item.get("no", 0)), reverse=True)
    visible_items = [item for item in all_items if item_matches_search(item, query)]
    return all_items, visible_items


def sort_new_items(items):
    """신규품목 창은 최초 등록이 빠른 항목부터 안정적으로 표시한다."""
    return sorted(items, key=lambda item: (
        item.get("registered_at") or item.get("added_at", ""),
        item.get("draft_no", 0),
    ))


def normalize_part_no(text):
    """품번 비교용 표기. 앞뒤 공백과 사이 공백을 없애고 대문자로 맞춘다.

    엑셀에서 올라온 품번은 ` A-1024 `처럼 공백이 붙어 오는 일이 잦고, 손으로 친 것과
    대소문자가 다를 수 있다. 사람 눈에 같은 품번이면 중복으로 보여야 하므로 여기서 맞춘다.
    """
    return "".join(str(text or "").split()).upper()


def find_duplicate_part_nos(items):
    """두 번 이상 나오는 품번의 집합(v0.1.3, 정규화된 표기).

    빈 품번은 세지 않는다 — 아직 안 적은 카드끼리 중복으로 물들면 새 카드를 만들 때마다
    화면이 붉어진다. 검색·더보기로 가려진 카드도 포함해 `data` 전체를 본다(짝이 화면 밖에
    있어도 중복은 중복이다).
    """
    counts = {}
    for item in items:
        key = normalize_part_no(item.get("part_no"))
        if key:
            counts[key] = counts.get(key, 0) + 1
    return {key for key, count in counts.items() if count > 1}


def parse_version(text):
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", str(text))
    if not match:
        return None
    return tuple(int(part) for part in match.groups())
