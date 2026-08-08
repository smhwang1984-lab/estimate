"""견적 양식(.xlsx) 읽기·쓰기.

v0.0.7부터 열 위치를 코드에 고정하지 않는다. `resolve_columns()`가 6행 헤더 문구를 읽어
이 파일이 실제로 어떤 배치인지 그때그때 판단한다. 예전에 쓰던 다른 배치의 양식
(기종 열이 없거나, 치구/프로그램이 한 칸으로 합쳐진 구버전 등)을 업로드해도
엉뚱한 열에 값이 들어가지 않게 하기 위해서다.

행이 모자라면 openpyxl의 insert_rows를 쓰지 않는다. 병합 범위가 따라가지 않는 것을
직접 재현해 확인했다(8건째부터 기계 시트 푸터가 밀리고 견적서가 #REF!가 나던 원인).
대신 '합계 행부터 그 아래(푸터 포함)를 통째로 아래로 옮기고, 비게 된 자리에
서식과 수식을 갖춘 새 데이터 행을 채우는' 방식(shift_block_down)을 쓴다.

    5행: 공정별 단가   6행: 헤더   7행부터: 입력 행   헤더 열의 '합계' 문구가 있는 행 = 합계 행
"""

import os
from copy import copy
from datetime import datetime

from openpyxl.styles import Alignment
from openpyxl.utils import get_column_letter, range_boundaries

from . import paths
from .config import MACHINE_KEYS
from .model import create_blank_item, safe_float, safe_int

SHEET_NAME = "기계"
ESTIMATE_SHEET_NAME = "견적서"
TEMPLATE_NAME = "견적용.xlsx"

HEADER_ROW = 6
FIRST_DATA_ROW = 7
RATE_ROW = 5
ES_FIRST_ROW = 15
ES_ROW_OFFSET = ES_FIRST_ROW - FIRST_DATA_ROW  # 견적서 행 - 기계 행
ES_COLS = {"no": 2, "part_no": 3, "part_name": 5, "final_price": 7}  # 견적서 자체 열은 항상 고정

# 헤더 문구가 살짝 달라도(구버전 양식 등) 찾아내기 위한 부분 일치 키워드.
# 앞쪽 항목이 우선한다 -- '프로그램 및치구'처럼 한 칸에 합쳐진 헤더는 먼저 매칭되는
# 키가 그 칸을 차지하고, 나머지 하나는 이 파일에서 열이 없는 것으로 처리한다
# (두 키에 같은 값을 중복으로 넣으면 금액이 두 배로 계산되므로).
MACHINE_KEYWORDS = [
    ("m_prog", ("프로그램",)),
    ("m_jig", ("치구",)),
    ("m_5axis", ("5축",)),
    ("m_4axis", ("4축",)),
    ("m_3axis", ("3축",)),
    ("m_lathe", ("선반",)),
    ("m_general", ("범용",)),
    ("m_finish", ("사상",)),
    ("m_cmm", ("CMM", "3차원")),
    ("m_grind", ("연삭", "연마", "와이어", "EDM")),
]


def _openpyxl():
    """openpyxl은 불러오는 데만 3초 가까이 걸린다.

    프로그램을 켤 때가 아니라 엑셀을 실제로 읽고 쓸 때 처음 불러오도록 미뤄서
    시작 시간을 줄인다(요청: "프로그램이 무거워").
    """
    import openpyxl
    return openpyxl


class TemplateNotFound(Exception):
    pass


class SheetNotFound(Exception):
    pass


def get_template_path():
    path = paths.get_resource_path(TEMPLATE_NAME)
    if not os.path.exists(path):
        raise TemplateNotFound(path)
    return path


def get_dated_output_path(create_dir=True):
    today = datetime.now()
    output_dir = os.path.join(paths.get_estimate_root_dir(), f"{today.year}년도", f"{today.month:02d}월")
    if create_dir:
        os.makedirs(output_dir, exist_ok=True)
    return os.path.join(output_dir, f"견적누적_{today:%Y-%m-%d}.xlsx")


def _get_sheet(wb, name):
    if name not in wb.sheetnames:
        raise SheetNotFound(name)
    return wb[name]


# ---------- 열 위치 판단 ----------

def resolve_columns(ws):
    """6행 헤더 문구를 읽어 이 파일의 실제 열 배치를 돌려준다."""
    texts = {}
    for col in range(1, 41):
        value = ws.cell(row=HEADER_ROW, column=col).value
        if value not in (None, ""):
            texts[col] = str(value).strip()

    def find_exact(*labels):
        for col in sorted(texts):
            if texts[col] in labels:
                return col
        return None

    used = set()

    def find_contains(*keywords):
        for col in sorted(texts):
            if col in used:
                continue
            if any(kw in texts[col] for kw in keywords):
                used.add(col)
                return col
        return None

    machine = {}
    for key, keywords in MACHINE_KEYWORDS:
        machine[key] = find_contains(*keywords)

    return {
        "model": find_exact("기종"),
        "part_no": find_exact("품번"),
        "part_name": find_exact("품명"),
        "comment": find_exact("Coment", "Comment"),
        "possible": find_exact("가능여부"),
        "qty": find_exact("Qty"),
        "material": find_exact("Material"),
        "size": find_exact("Size"),
        "unit_price": find_exact("단가"),
        "final_price": find_exact("최종단가"),
        "sum": find_exact("SUM"),
        "machine": machine,
    }


def _max_used_col(cols):
    values = [v for k, v in cols.items() if k != "machine" and v]
    values += [v for v in cols["machine"].values() if v]
    return max(values) if values else 24


def _merge_span(ws, row, col):
    for rng in ws.merged_cells.ranges:
        if rng.min_row <= row <= rng.max_row and rng.min_col <= col <= rng.max_col:
            return rng.max_col - rng.min_col + 1
    return 1


def _print_area_bounds(ws):
    """현재 인쇄 영역의 (좌열, 상행, 우열, 하행). 없으면 None."""
    if not ws.print_area:
        return None
    ref = str(ws.print_area)
    if "!" in ref:
        ref = ref.split("!", 1)[1]
    ref = ref.replace("$", "")
    try:
        return range_boundaries(ref)
    except ValueError:
        return None


def _set_print_area(ws, min_col, min_row, max_col, max_row):
    ws.print_area = (f"${get_column_letter(min_col)}${min_row}:"
                     f"${get_column_letter(max_col)}${max_row}")


# ---------- 블록 이동 (insert_rows 대신 씀. 병합도 함께 옮긴다) ----------

def shift_block_down(ws, from_row, delta, max_col):
    """from_row 이상의 모든 내용(값·서식·행높이·병합)을 delta만큼 아래로 옮긴다."""
    if delta <= 0:
        return
    last_row = max(ws.max_row, from_row)
    merges_to_move = [rng for rng in list(ws.merged_cells.ranges) if rng.min_row >= from_row]
    for rng in merges_to_move:
        ws.unmerge_cells(str(rng))

    for row in range(last_row, from_row - 1, -1):
        target = row + delta
        for col in range(1, max_col + 1):
            src = ws.cell(row=row, column=col)
            dst = ws.cell(row=target, column=col)
            dst.value = src.value
            if src.has_style:
                dst._style = copy(src._style)
            dst.number_format = src.number_format
        if row in ws.row_dimensions:
            ws.row_dimensions[target].height = ws.row_dimensions[row].height

    for row in range(from_row, from_row + delta):
        for col in range(1, max_col + 1):
            ws.cell(row=row, column=col).value = None

    for rng in merges_to_move:
        ws.merge_cells(start_row=rng.min_row + delta, start_column=rng.min_col,
                       end_row=rng.max_row + delta, end_column=rng.max_col)


def copy_row_style(ws, source_row, target_row, max_col):
    for col in range(1, max_col + 1):
        source = ws.cell(row=source_row, column=col)
        target = ws.cell(row=target_row, column=col)
        if source.has_style:
            target._style = copy(source._style)
        if source.number_format:
            target.number_format = source.number_format
    if source_row in ws.row_dimensions:
        ws.row_dimensions[target_row].height = ws.row_dimensions[source_row].height


def apply_row_formulas(ws, row, cols):
    ws.cell(row=row, column=1, value="=ROW()-6")
    machine = cols["machine"]
    letters = {key: get_column_letter(col) for key, col in machine.items() if col}
    keys_present = [key for key in MACHINE_KEYS if key in letters]
    if cols["sum"] and keys_present:
        terms = "+".join(f"{letters[key]}{row}" for key in keys_present)
        ws.cell(row=row, column=cols["sum"], value=f"={terms}")
    if cols["unit_price"] and cols["qty"] and keys_present:
        qty_letter = get_column_letter(cols["qty"])
        terms = "+".join(f"{letters[key]}{row}*${letters[key]}${RATE_ROW}" for key in keys_present)
        ws.cell(row=row, column=cols["unit_price"], value=f"=({terms})*${qty_letter}{row}")
    if cols["final_price"] and cols["unit_price"]:
        unit_letter = get_column_letter(cols["unit_price"])
        ws.cell(row=row, column=cols["final_price"], value=f"=ROUNDDOWN(${unit_letter}{row},-3)")


def merge_size_cell(ws, row, cols):
    """Size 헤더가 여러 칸(I6:K6 등) 병합돼 있으면 데이터 행도 같은 폭으로 병합하고
    가운데 정렬한다. 지금은 값이 I열 한 칸에만 들어가 사이즈 하나가 3열로 쪼개져
    보이는 문제(요청 1번)를 고친다. 헤더가 1칸뿐인 구버전 양식은 손대지 않는다.
    """
    if not cols["size"]:
        return
    span = _merge_span(ws, HEADER_ROW, cols["size"])
    if span <= 1:
        return
    start_col = cols["size"]
    end_col = start_col + span - 1
    # 다시 저장하는 경우 이미 병합돼 있을 수 있다 -- 겹치는 병합을 정리하고 새로 맞춘다
    # (openpyxl은 이미 병합된 범위를 다시 merge_cells 하면 오류를 낸다).
    for rng in [r for r in list(ws.merged_cells.ranges)
               if r.min_row == row and r.max_row == row
               and r.min_col >= start_col and r.max_col <= end_col]:
        ws.unmerge_cells(str(rng))
    ws.merge_cells(start_row=row, start_column=start_col, end_row=row, end_column=end_col)
    ws.cell(row=row, column=start_col).alignment = Alignment(horizontal="center", vertical="center")


def row_has_input_data(ws, row, cols):
    check_cols = [cols[key] for key in
                  ("part_no", "part_name", "comment", "possible", "qty", "material", "size")
                  if cols[key]]
    check_cols += [col for col in cols["machine"].values() if col]
    for col in check_cols:
        if ws.cell(row=row, column=col).value not in (None, ""):
            return True
    return False


def find_summary_row(ws, cols):
    """'합계' 문구가 있는 행을 헤더 문구가 아니라 실제로 찾는다(행이 몇 개든 안전)."""
    label_col = cols.get("unit_price") or cols.get("final_price")
    if not label_col:
        return FIRST_DATA_ROW
    row = FIRST_DATA_ROW
    limit = FIRST_DATA_ROW + 2000
    while row < limit:
        value = ws.cell(row=row, column=label_col).value
        if isinstance(value, str) and "합계" in value.replace(" ", ""):
            return row
        row += 1
    return FIRST_DATA_ROW


def update_summary_formula(ws, cols, summary_row):
    if cols["unit_price"]:
        ws.cell(row=summary_row, column=cols["unit_price"], value="합계")
    if cols["final_price"]:
        letter = get_column_letter(cols["final_price"])
        ws.cell(row=summary_row, column=cols["final_price"],
                value=f"=SUM({letter}{FIRST_DATA_ROW}:{letter}{summary_row - 1})")


def layout_machine_sheet(ws, cols, need_rows):
    """기계 시트에 need_rows개의 데이터 행이 들어갈 자리를 만들고 합계 행을 돌려준다.

    모자라면 합계 행(및 그 아래 푸터)을 통째로 아래로 밀고, 비게 된 자리에
    7행 서식을 복사한 새 데이터 행을 채운다. 인쇄 영역도 늘어난 만큼 넓힌다.
    """
    max_col = _max_used_col(cols)
    summary_row = find_summary_row(ws, cols)
    capacity = summary_row - FIRST_DATA_ROW
    if need_rows > capacity:
        additional = need_rows - capacity
        bounds = _print_area_bounds(ws)
        shift_block_down(ws, summary_row, additional, max_col)
        for row in range(summary_row, summary_row + additional):
            copy_row_style(ws, FIRST_DATA_ROW, row, max_col)
            apply_row_formulas(ws, row, cols)
            merge_size_cell(ws, row, cols)
        summary_row += additional
        if bounds:
            min_col, min_row, max_col_b, max_row_b = bounds
            _set_print_area(ws, min_col, min_row, max_col_b, max_row_b + additional)
    update_summary_formula(ws, cols, summary_row)
    return summary_row


def sync_estimate_sheet(es, gigye_ws, gigye_cols, gigye_summary_row):
    """기계 시트의 실제 데이터 행 수에 맞춰 견적서 시트의 항목 칸 수·참조를 맞춘다."""
    item_count = gigye_summary_row - FIRST_DATA_ROW

    summary_row = ES_FIRST_ROW
    limit = ES_FIRST_ROW + 2000
    while summary_row < limit:
        value = es.cell(row=summary_row, column=ES_COLS["no"]).value
        if isinstance(value, str) and "합계" in value.replace(" ", ""):
            break
        summary_row += 1
    else:
        return  # 예상 밖 구조라 손대지 않는다.

    capacity = summary_row - ES_FIRST_ROW
    if item_count > capacity:
        additional = item_count - capacity
        bounds = _print_area_bounds(es)
        shift_block_down(es, summary_row, additional, 8)
        for row in range(summary_row, summary_row + additional):
            copy_row_style(es, ES_FIRST_ROW, row, 8)
            for rng in (f"C{row}:D{row}", f"E{row}:F{row}", f"G{row}:H{row}"):
                es.merge_cells(rng)
            es.cell(row=row, column=ES_COLS["no"], value="=ROW()-14")
        summary_row += additional
        if bounds:
            min_col, min_row, max_col_b, max_row_b = bounds
            _set_print_area(es, min_col, min_row, max_col_b, max_row_b + additional)

    # 기계 시트에서 실제로 값이 있는 행만 참조로 채운다. 예전에는 "< gigye_summary_row"
    # (양식의 칸 수)만으로 판단해서, 항목보다 빈 칸이 많이 남으면 그 빈 칸을 그대로 참조해
    # 견적서에 품번/품명 '0', 단가 '₩0'인 쓰레기 행이 찍혔다(재현 완료).
    #
    # row_has_input_data만으로 바꿔서도 안 된다 -- 기계 시트 푸터(17~19행)가 데이터
    # 열과 같은 열 위치를 쓴다(예: '사상' 열 Q=17번째 열에 푸터 라벨 '㈜텍스타'가 Q17에
    # 앉아 있다, 'coment :' 라벨은 D18에 있고 D는 품명 열이다). 상한 없이 검사하면 이
    # 푸터 라벨을 항목 데이터로 착각한다(직접 재현 확인). 그래서 "기계 시트의 실제 데이터
    # 구간(FIRST_DATA_ROW ~ gigye_summary_row 미만) 안에 있고, 그 행에 실제 값이 있을 때"
    # 둘 다를 만족해야 참조를 채운다.
    part_no_letter = get_column_letter(gigye_cols["part_no"]) if gigye_cols["part_no"] else None
    part_name_letter = get_column_letter(gigye_cols["part_name"]) if gigye_cols["part_name"] else None
    final_price_letter = get_column_letter(gigye_cols["final_price"]) if gigye_cols["final_price"] else None
    for row in range(ES_FIRST_ROW, summary_row):
        src_row = row - ES_ROW_OFFSET
        has_data = (FIRST_DATA_ROW <= src_row < gigye_summary_row
                   and row_has_input_data(gigye_ws, src_row, gigye_cols))
        # 주의: ws.cell(..., value=None)은 openpyxl에서 "값을 지운다"가 아니라
        # "value 인자를 안 준 것"으로 취급되어 기존 값이 그대로 남는다(직접 재현 확인).
        # 반드시 .value 속성에 직접 대입해야 실제로 비워진다.
        if part_no_letter:
            es.cell(row=row, column=ES_COLS["part_no"]).value = (
                f"=기계!${part_no_letter}{src_row}" if has_data else None)
        if part_name_letter:
            es.cell(row=row, column=ES_COLS["part_name"]).value = (
                f"=기계!${part_name_letter}{src_row}" if has_data else None)
        if final_price_letter:
            es.cell(row=row, column=ES_COLS["final_price"]).value = (
                f"=기계!${final_price_letter}{src_row}" if has_data else None)
    if final_price_letter:
        col_letter = get_column_letter(ES_COLS["final_price"])
        es.cell(row=summary_row, column=ES_COLS["final_price"],
                value=f"=SUM({col_letter}{ES_FIRST_ROW}:{col_letter}{summary_row - 1})")


# ---------- 읽기 ----------

def read_cards_from_workbook(file_path):
    """업로드한 기계 시트에서 입력된 행만 카드로 읽어 온다."""
    wb = _openpyxl().load_workbook(file_path, data_only=False)
    ws = _get_sheet(wb, SHEET_NAME)
    cols = resolve_columns(ws)
    summary_row = find_summary_row(ws, cols)
    abs_path = os.path.abspath(file_path)
    created_at = datetime.fromtimestamp(os.path.getmtime(abs_path)).strftime("%Y-%m-%d")
    source_month = os.path.basename(os.path.dirname(abs_path))
    size_span = _merge_span(ws, HEADER_ROW, cols["size"]) if cols["size"] else 0

    cards = []
    for row in range(FIRST_DATA_ROW, summary_row):
        if not row_has_input_data(ws, row, cols):
            continue
        item = create_blank_item(len(cards) + 1)
        item["created_at"] = created_at
        item["source_file"] = os.path.basename(abs_path)
        item["source_month"] = source_month
        item["save_pending"] = True
        item["excel_row"] = None
        item["excel_file"] = None
        item["model"] = str(ws.cell(row=row, column=cols["model"]).value or "") if cols["model"] else ""
        item["part_no"] = str(ws.cell(row=row, column=cols["part_no"]).value or "") if cols["part_no"] else ""
        item["part_name"] = (str(ws.cell(row=row, column=cols["part_name"]).value or "")
                             if cols["part_name"] else "")
        item["comment"] = str(ws.cell(row=row, column=cols["comment"]).value or "") if cols["comment"] else ""
        item["possible"] = (str(ws.cell(row=row, column=cols["possible"]).value or "가능")
                            if cols["possible"] else "가능")
        item["qty"] = safe_int(ws.cell(row=row, column=cols["qty"]).value, 1) if cols["qty"] else 1
        item["material"] = (str(ws.cell(row=row, column=cols["material"]).value or "")
                            if cols["material"] else "")
        if cols["size"] and size_span:
            size_parts = [ws.cell(row=row, column=cols["size"] + i).value for i in range(size_span)]
            item["size"] = " x ".join(str(v) for v in size_parts if v not in (None, ""))
        for key, col in cols["machine"].items():
            item[key] = safe_float(ws.cell(row=row, column=col).value) if col else 0.0
        cards.append(item)
    return cards


# ---------- 쓰기 ----------

def _write_item_values(ws, row, item, cols):
    # 주의: ws.cell(..., value=None)은 openpyxl에서 "값을 지운다"가 아니라
    # "value 인자를 안 준 것"으로 취급되어 기존 값이 그대로 남는다(직접 재현 확인).
    # 사용자가 필드를 비우고 다시 저장했을 때 이전 값이 남지 않도록 .value에 직접 대입한다.
    def set_cell(col, value):
        ws.cell(row=row, column=col).value = value

    def text_or_none(value):
        value = value.strip() if value else ""
        return value or None

    if cols["model"]:
        set_cell(cols["model"], text_or_none(item["model"]))
    if cols["part_no"]:
        set_cell(cols["part_no"], text_or_none(item["part_no"]))
    if cols["part_name"]:
        set_cell(cols["part_name"], text_or_none(item["part_name"]))
    if cols["comment"]:
        set_cell(cols["comment"], text_or_none(item["comment"]))
    if cols["possible"]:
        set_cell(cols["possible"], item["possible"])
    if cols["qty"]:
        set_cell(cols["qty"], item["qty"])
    if cols["material"]:
        set_cell(cols["material"], text_or_none(item["material"]))
    if cols["size"]:
        set_cell(cols["size"], text_or_none(item["size"]))
    for key, col in cols["machine"].items():
        if not col:
            continue
        value = item[key]
        set_cell(col, value if value > 0 else None)


def write_items_to_sheet(ws, items, rates, update_item_rows, target_file):
    """카드 목록을 시트에 채워 넣는다.

    update_item_rows=True 면 각 카드가 어느 파일의 몇 행에 들어갔는지 기억해 두고
    저장 완료로 표시한다(날짜별 누적 저장). 다른 파일에서 넘어온 excel_row는
    이 파일 기준으로는 무효라 새 자리를 새로 배정한다(날짜가 바뀌면 파일도 바뀌므로).
    False 면 카드를 건드리지 않는다(선택 다운로드).
    """
    cols = resolve_columns(ws)

    for key, col in cols["machine"].items():
        if col:
            ws.cell(row=RATE_ROW, column=col, value=rates[key])

    summary_row = find_summary_row(ws, cols)

    def existing_row(item):
        if not update_item_rows:
            return None
        row = item.get("excel_row")
        if not row or not (FIRST_DATA_ROW <= row < summary_row):
            return None
        if item.get("excel_file") == target_file:
            return row
        if item.get("excel_file") is not None:
            return None  # 다른 파일에서 넘어온 행 번호는 이 파일 기준으로 무효.
        # v0.0.6 이전 세션에는 excel_file이 없었다. 오늘 이어 쓰는 바로 그 파일이 맞는지
        # 그 행의 품번을 대조해 확인한 뒤에만 재사용한다(값이 실제로 일치할 때만 허용해야
        # 엉뚱한 파일의 행 번호를 그대로 써서 다른 항목을 덮어쓰는 일이 없다).
        if not cols["part_no"]:
            return None
        cell_value = ws.cell(row=row, column=cols["part_no"]).value
        if cell_value and str(cell_value).strip() == (item.get("part_no") or "").strip():
            return row
        return None

    reserved = {existing_row(item) for item in items if existing_row(item)}
    free_rows = [row for row in range(FIRST_DATA_ROW, summary_row)
                if row not in reserved and not row_has_input_data(ws, row, cols)]

    new_item_count = sum(1 for item in items if existing_row(item) is None)
    need_new = max(0, new_item_count - len(free_rows))

    if need_new:
        capacity = summary_row - FIRST_DATA_ROW
        summary_row = layout_machine_sheet(ws, cols, capacity + need_new)
        free_rows = [row for row in range(FIRST_DATA_ROW, summary_row)
                    if row not in reserved and not row_has_input_data(ws, row, cols)]
    else:
        update_summary_formula(ws, cols, summary_row)

    saved_count = 0
    for item in items:
        row = existing_row(item)
        if row is None:
            row = free_rows.pop(0)
        if update_item_rows:
            # 품번 대조로 재사용을 허락받은 구버전 세션 항목도 여기서 excel_file이
            # 채워져야 다음 저장부터 정상적으로(대조 없이) 재사용된다.
            item["excel_row"] = row
            item["excel_file"] = target_file
        copy_row_style(ws, FIRST_DATA_ROW, row, _max_used_col(cols))
        apply_row_formulas(ws, row, cols)
        merge_size_cell(ws, row, cols)
        _write_item_values(ws, row, item, cols)
        if update_item_rows:
            item["save_pending"] = False
        saved_count += 1
    update_summary_formula(ws, cols, summary_row)
    return saved_count, summary_row, cols


def _sync_estimate_if_present(wb, gigye_ws, gigye_cols, gigye_summary_row):
    if ESTIMATE_SHEET_NAME in wb.sheetnames:
        sync_estimate_sheet(wb[ESTIMATE_SHEET_NAME], gigye_ws, gigye_cols, gigye_summary_row)


def save_daily_accumulated(items, rates):
    """오늘 날짜 누적 파일에 이어 붙인다. (저장 건수, 파일 경로)를 돌려준다."""
    template_path = get_template_path()
    output_path = get_dated_output_path(True)
    source_path = output_path if os.path.exists(output_path) else template_path
    wb = _openpyxl().load_workbook(source_path)
    ws = _get_sheet(wb, SHEET_NAME)
    target_file = os.path.abspath(output_path)
    saved_count, summary_row, cols = write_items_to_sheet(ws, items, rates, True, target_file)
    _sync_estimate_if_present(wb, ws, cols, summary_row)
    wb.save(output_path)
    return saved_count, output_path


def export_items(items, rates, output_path):
    """빈 양식에 선택한 카드만 담아 별도 파일로 저장한다."""
    template_path = get_template_path()
    wb = _openpyxl().load_workbook(template_path)
    ws = _get_sheet(wb, SHEET_NAME)
    target_file = os.path.abspath(output_path)
    saved_count, summary_row, cols = write_items_to_sheet(ws, items, rates, False, target_file)
    _sync_estimate_if_present(wb, ws, cols, summary_row)
    wb.save(output_path)
    return saved_count
