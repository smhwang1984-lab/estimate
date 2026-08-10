"""카드를 열었을 때 뜨는 상세 입력 팝업창.

v0.0.9 변경점
    - Comment를 여러 줄로 적을 수 있게 바꾸고(요청 5-1), 아래 손잡이를 끌어 높이를 늘린다.
    - Material은 설정창 목록에서 고르고(요청 6-3), `열처리`를 체크하면 그 아래에
      HRC Min/Max 입력칸이 살아난다(요청 5-2, 5-3).
    - 공정 단가는 더 이상 여기서 못 고친다. 설정창 값이 그대로 쓰인다(요청 6-2).
    - 정보 타일에서 기계 시트 폴더/파일과 엑셀 행을 뺐다(요청 4-3, 4-4).
      NO는 엑셀 행이 아니라 현황판에 보이는 순번이다(요청 4-5).

v0.1.0 변경점
    - 시간·HRC·Qty 입력칸은 숫자(와 소수점) 외의 글자가 아예 들어가지 않는다(요청 2).
      저장 시점 검사(has_unsaved_changes 이후의 float() 변환)는 마지막 방어선으로 남겨 둔다.
    - Size에 비중을 곱해 무게를 함께 보여 준다(요청 4). 직접입력이거나 소재의 비중을
      찾지 못하면 계산할 수 없으므로 무게를 비우고 그 이유를 안내한다.
"""

import math
import tkinter as tk
from tkinter import messagebox, ttk

from ..core import config, settings as settings_store
from ..core.model import calc_weight_kg, parse_number, parse_size
from ..core.pricing import calc_row
from .condition_dialog import open_condition_dialog
from .widgets import numeric_entry as _numeric_entry

SHAPE_BLOCK = "블록"
SHAPE_ROD = "로드"
SHAPE_CUSTOM = "직접입력"

COMMENT_MIN_LINES = 2
COMMENT_MAX_LINES = 20


def display_no_text(app, no):
    """현황판에 보이는 순번을 글자로. 아직 목록에 없는 새 카드는 '신규'로 보여 준다."""
    display_no = app.get_display_no(no)
    return str(display_no) if display_no else "신규"


def build_info_panel(app, parent, item):
    """팝업 상단에 항목 정보를 펼쳐 놓는다. 금액 3종은 입력에 따라 실시간으로 바뀐다."""
    info_box = ttk.LabelFrame(parent, text="항목 정보", padding=10)
    info_box.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
    sum_time, unit_price, final_price = calc_row(item, app.rates)
    summary_vars = {
        "sum_time": tk.StringVar(value=f"{sum_time:.1f} h"),
        "unit_price": tk.StringVar(value=f"{int(unit_price):,} 원"),
        "final_price": tk.StringVar(value=f"{final_price:,} 원"),
    }
    static_facts = [
        ("NO", display_no_text(app, item["no"])),
        ("작성일", item["created_at"]),
        ("저장 상태", "저장 대기" if item.get("save_pending") else "저장 완료"),
    ]
    live_facts = [
        ("시간합계", summary_vars["sum_time"]),
        ("단가합계", summary_vars["unit_price"]),
        ("최종 견적금액", summary_vars["final_price"]),
    ]
    for col in range(len(static_facts) + len(live_facts)):
        info_box.columnconfigure(col, weight=1)
    for idx, (label, value) in enumerate(static_facts):
        tile = ttk.Frame(info_box, padding=6)
        tile.grid(row=0, column=idx, sticky="nsew", padx=3)
        ttk.Label(tile, text=label, style="Muted.TLabel").pack(anchor="w")
        ttk.Label(tile, text=value, wraplength=170, justify="left").pack(anchor="w", pady=(2, 0))
    for offset, (label, var) in enumerate(live_facts):
        tile = ttk.Frame(info_box, padding=6)
        tile.grid(row=0, column=len(static_facts) + offset, sticky="nsew", padx=3)
        ttk.Label(tile, text=label, style="Muted.TLabel").pack(anchor="w")
        ttk.Label(tile, textvariable=var, style="Value.TLabel").pack(anchor="w", pady=(2, 0))
    return summary_vars


def _build_material_section(app, parent, item):
    """Material 선택과 열처리 경도 입력. (소재 변수, 열처리 변수, Min, Max)를 돌려준다."""
    box = ttk.LabelFrame(parent, text="Material (소재) 입력", padding=10)
    box.pack(fill=tk.X, pady=(0, 10))
    box.columnconfigure(1, weight=1)

    material_var = tk.StringVar(value=item.get("material", ""))
    ttk.Label(box, text="Material").grid(row=0, column=0, sticky="e", padx=6, pady=6)
    # 목록에서 고르되 목록에 없는 소재는 직접 적을 수 있게 readonly로 잠그지 않는다.
    ttk.Combobox(box, textvariable=material_var, values=list(app.settings["materials"]),
                 width=30).grid(row=0, column=1, columnspan=3, sticky="ew", padx=6, pady=6)

    heat_var = tk.BooleanVar(value=bool(item.get("heat_treat")))
    hrc_min_var = tk.StringVar(value=str(item.get("hrc_min", "")))
    hrc_max_var = tk.StringVar(value=str(item.get("hrc_max", "")))

    heat_check = ttk.Checkbutton(box, text="열처리", variable=heat_var)
    heat_check.grid(row=1, column=0, columnspan=2, sticky="w", padx=6, pady=(4, 0))

    # 열처리를 체크했을 때만 보이는 줄. 요청대로 체크박스 "아래에" 붙인다.
    hrc_row = ttk.Frame(box)
    hrc_row.grid(row=2, column=0, columnspan=4, sticky="w", padx=6, pady=(2, 2))
    ttk.Label(hrc_row, text="HRC").pack(side=tk.LEFT, padx=(6, 6))
    min_entry = _numeric_entry(hrc_row, hrc_min_var, width=6)
    min_entry.pack(side=tk.LEFT)
    ttk.Label(hrc_row, text="~").pack(side=tk.LEFT, padx=6)
    max_entry = _numeric_entry(hrc_row, hrc_max_var, width=6)
    max_entry.pack(side=tk.LEFT)
    ttk.Label(hrc_row, text="Min / Max 경도", style="Muted.TLabel").pack(side=tk.LEFT, padx=(10, 0))

    def sync_hrc_state(*args):
        state = "normal" if heat_var.get() else "disabled"
        min_entry.configure(state=state)
        max_entry.configure(state=state)

    heat_var.trace_add("write", sync_hrc_state)
    sync_hrc_state()
    return material_var, heat_var, hrc_min_var, hrc_max_var


def _build_comment_section(app, parent, item):
    """여러 줄 Comment 입력칸. 아래 손잡이를 끌어 높이를 직접 늘릴 수 있다(요청 5-1)."""
    c = app.theme.colors
    box = ttk.LabelFrame(parent, text="Comment", padding=10)
    box.pack(fill=tk.X, pady=(0, 10))

    holder = tk.Frame(box, bg=c["panel"])
    holder.pack(fill=tk.X)
    scrollbar = ttk.Scrollbar(holder, orient=tk.VERTICAL)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    text = tk.Text(holder, height=2, wrap="word", bg=c["card_alt"], fg=c["text"],
                   insertbackground=c["text"], highlightthickness=1,
                   highlightbackground=c["line"], relief="flat",
                   font=(app.theme.family, app.theme.fonts["normal_size"]))
    text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    text.configure(yscrollcommand=scrollbar.set)
    scrollbar.configure(command=text.yview)
    text.insert("1.0", item.get("comment", ""))

    # 손잡이. 위아래로 끌면 줄 수가 바뀐다. Tk의 Text는 픽셀이 아니라 줄 수로 높이를 잡으므로
    # 끌어 옮긴 픽셀을 한 줄 높이로 나눠 줄 수로 환산한다.
    grip = tk.Frame(box, height=7, bg=c["line"], cursor="sb_v_double_arrow")
    grip.pack(fill=tk.X, pady=(4, 0))
    drag_state = {"y": 0, "lines": COMMENT_MIN_LINES}

    def start_drag(event):
        drag_state["y"] = event.y_root
        drag_state["lines"] = int(text.cget("height"))

    def on_drag(event):
        line_height = max(1, text.winfo_height() // max(1, int(text.cget("height"))))
        delta_lines = (event.y_root - drag_state["y"]) // line_height
        new_lines = max(COMMENT_MIN_LINES, min(COMMENT_MAX_LINES, drag_state["lines"] + delta_lines))
        text.configure(height=new_lines)

    grip.bind("<Button-1>", start_drag)
    grip.bind("<B1-Motion>", on_drag)
    ttk.Label(box, text="회색 손잡이를 끌면 입력칸이 커집니다.",
              style="Muted.TLabel").pack(anchor="w", pady=(6, 0))
    return text


def _build_size_section(app, parent, item, material_var):
    """Size 입력 영역. (최종 Size 변수, 무게를 다시 계산해 돌려주는 함수)를 돌려준다.

    v0.1.0: 치수 x 소재 비중으로 무게를 계산해 보여 준다(요청 4). 직접입력이거나
    설정창에 소재 비중이 없으면 계산할 수 없으므로 무게를 비우고 이유를 안내한다.
    """
    size_box = ttk.LabelFrame(parent, text="Size (소재 규격) 입력", padding=10)
    size_box.pack(fill=tk.X)

    shape_var = tk.StringVar(value=SHAPE_BLOCK)
    t_var, w_var, l_var, d_var = tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar()
    custom_size_var = tk.StringVar()
    final_size_var = tk.StringVar(value=item["size"])
    weight_var = tk.StringVar(value="")

    # 이미 입력돼 있던 Size 문자열을 보고 어느 형상으로 적었는지 되짚어 칸을 채워 준다
    # (core/model.parse_size() -- 가공조건 산출기와 이 파서를 공유한다, v0.1.1).
    parsed_shape, parsed_dims = parse_size(item["size"])
    shape_labels = {"block": SHAPE_BLOCK, "rod": SHAPE_ROD, "custom": SHAPE_CUSTOM}
    if parsed_shape in shape_labels:
        shape_var.set(shape_labels[parsed_shape])
    if parsed_shape == "rod":
        if "d" in parsed_dims:
            d_var.set(parsed_dims["d"])
        if "l" in parsed_dims:
            l_var.set(parsed_dims["l"])
    elif parsed_shape == "block":
        if "t" in parsed_dims:
            t_var.set(parsed_dims["t"])
        if "w" in parsed_dims:
            w_var.set(parsed_dims["w"])
        if "l" in parsed_dims:
            l_var.set(parsed_dims["l"])
    elif parsed_shape == "custom":
        custom_size_var.set(parsed_dims.get("text", ""))

    radio_frame = ttk.Frame(size_box)
    radio_frame.pack(fill=tk.X, pady=(0, 6))
    ttk.Label(radio_frame, text="형상 선택").pack(side=tk.LEFT, padx=(0, 8))
    ttk.Radiobutton(radio_frame, text="블록 (T x W x L)", value=SHAPE_BLOCK, variable=shape_var).pack(side=tk.LEFT, padx=6)
    ttk.Radiobutton(radio_frame, text="로드/원봉 (D x L)", value=SHAPE_ROD, variable=shape_var).pack(side=tk.LEFT, padx=6)
    ttk.Radiobutton(radio_frame, text="직접 입력", value=SHAPE_CUSTOM, variable=shape_var).pack(side=tk.LEFT, padx=6)

    input_subframe = ttk.Frame(size_box, padding=5)
    input_subframe.pack(fill=tk.X)

    def update_size_preview(*args):
        shape = shape_var.get()
        if shape == SHAPE_BLOCK:
            t_val, w_val, l_val = t_var.get().strip(), w_var.get().strip(), l_var.get().strip()
            if t_val or w_val or l_val:
                if t_val and w_val and l_val:
                    final_size_var.set(f"{t_val}T * {w_val}W * {l_val}L")
                else:
                    final_size_var.set(f"{t_val} * {w_val} * {l_val}")
            else:
                final_size_var.set("")
        elif shape == SHAPE_ROD:
            d_val, l_val = d_var.get().strip(), l_var.get().strip()
            if d_val or l_val:
                if d_val and l_val:
                    final_size_var.set(f"Ø{d_val} * {l_val}L")
                else:
                    final_size_var.set(f"Ø{d_val} * {l_val}")
            else:
                final_size_var.set("")
        else:
            final_size_var.set(custom_size_var.get().strip())

    for variable in (t_var, w_var, l_var, d_var, custom_size_var):
        variable.trace_add("write", update_size_preview)

    def render_size_inputs(*args):
        for widget in input_subframe.winfo_children():
            widget.destroy()
        shape = shape_var.get()
        if shape == SHAPE_BLOCK:
            ttk.Label(input_subframe, text="T (두께)").grid(row=0, column=0, padx=3, pady=2)
            _numeric_entry(input_subframe, t_var, width=10).grid(row=0, column=1, padx=5, pady=2)
            ttk.Label(input_subframe, text="W (폭)").grid(row=0, column=2, padx=3, pady=2)
            _numeric_entry(input_subframe, w_var, width=10).grid(row=0, column=3, padx=5, pady=2)
            ttk.Label(input_subframe, text="L (길이)").grid(row=0, column=4, padx=3, pady=2)
            _numeric_entry(input_subframe, l_var, width=10).grid(row=0, column=5, padx=5, pady=2)
        elif shape == SHAPE_ROD:
            ttk.Label(input_subframe, text="D (외경/Ø)").grid(row=0, column=0, padx=3, pady=2)
            _numeric_entry(input_subframe, d_var, width=12).grid(row=0, column=1, padx=5, pady=2)
            ttk.Label(input_subframe, text="L (길이)").grid(row=0, column=2, padx=3, pady=2)
            _numeric_entry(input_subframe, l_var, width=12).grid(row=0, column=3, padx=5, pady=2)
        else:
            ttk.Label(input_subframe, text="Size 규격").grid(row=0, column=0, padx=3, pady=2)
            ttk.Entry(input_subframe, textvariable=custom_size_var, width=35).grid(row=0, column=1, padx=5, pady=2)
        update_size_preview()

    shape_var.trace_add("write", render_size_inputs)
    render_size_inputs()

    preview = ttk.Frame(size_box)
    preview.pack(fill=tk.X, pady=(4, 0))
    ttk.Label(preview, text="최종 반영 Size", style="Muted.TLabel").pack(side=tk.LEFT, padx=(0, 8))
    ttk.Label(preview, textvariable=final_size_var, style="Value.TLabel").pack(side=tk.LEFT)

    def _dims_complete():
        shape = shape_var.get()
        if shape == SHAPE_BLOCK:
            return all(v.get().strip() for v in (t_var, w_var, l_var))
        if shape == SHAPE_ROD:
            return all(v.get().strip() for v in (d_var, l_var))
        return False

    def get_weight():
        """치수 x 소재 비중으로 무게(kg)를 계산한다. 직접입력이거나 비중을 못 찾으면 None."""
        if shape_var.get() == SHAPE_CUSTOM or not _dims_complete():
            return None
        density = settings_store.resolve_density(material_var.get(), app.settings.get("densities", []))
        if density is None:
            return None
        if shape_var.get() == SHAPE_BLOCK:
            return calc_weight_kg("block", t=parse_number(t_var.get()), w=parse_number(w_var.get()),
                                  l=parse_number(l_var.get()), density=density)
        return calc_weight_kg("rod", d=parse_number(d_var.get()), l=parse_number(l_var.get()), density=density)

    def update_weight_preview(*args):
        if shape_var.get() == SHAPE_CUSTOM:
            weight_var.set("직접입력은 치수를 몰라 계산할 수 없습니다.")
            return
        if not _dims_complete():
            weight_var.set("")
            return
        weight = get_weight()
        weight_var.set(f"{weight:.2f} kg" if weight is not None
                       else "비중 미등록 (설정 > 소재 비중에서 추가)")

    weight_row = ttk.Frame(size_box)
    weight_row.pack(fill=tk.X, pady=(4, 0))
    ttk.Label(weight_row, text="무게(1개)", style="Muted.TLabel").pack(side=tk.LEFT, padx=(0, 8))
    ttk.Label(weight_row, textvariable=weight_var, style="Value.TLabel").pack(side=tk.LEFT)

    for variable in (t_var, w_var, l_var, d_var, material_var, shape_var):
        variable.trace_add("write", update_weight_preview)
    update_weight_preview()

    # v0.1.1: 이 카드의 Material·Size를 가공조건 산출기로 보낸다(카드는 고치지 않는다,
    # 사용자 결정 -- plan.md 2026-08-09 v0.1.1 항목). 팝업이 이미 grab_set() 중이므로
    # 산출기가 grab을 넘겨받았다가 닫을 때 돌려준다(condition_dialog._rehome_grab).
    action_row = ttk.Frame(size_box)
    action_row.pack(fill=tk.X, pady=(8, 0))
    ttk.Button(action_row, text="가공조건 산출기 열기",
              command=lambda: open_condition_dialog(
                  app, item=item, popup=parent.winfo_toplevel())).pack(side=tk.LEFT)
    ttk.Label(action_row, text="현재 저장된 Material·Size를 계산기로 보냅니다. 계산 결과는 카드에 반영되지 않습니다.",
              style="Muted.TLabel", wraplength=340, justify="left").pack(side=tk.LEFT, padx=(10, 0))

    return final_size_var, get_weight


def open_item_popup(app, no):
    item = next((row for row in app.data if row["no"] == no), None)
    if not item:
        return
    # 같은 카드를 두 번 열지 않고, 이미 떠 있으면 앞으로 가져온다.
    existing = app.open_popups.get(no)
    if existing is not None and existing.winfo_exists():
        existing.lift()
        existing.focus_force()
        return

    popup = tk.Toplevel(app.root)
    app.open_popups[no] = popup
    popup.title(f"[NO. {display_no_text(app, no)}] 견적 항목 입력")
    # 화면 배율이 커도 팝업이 화면 밖으로 넘치지 않도록 표시 영역에 맞춰 크기를 정한다.
    # v0.0.9: Material·열처리·여러 줄 Comment가 들어오면서 세로가 길어져, 예전 상한(1180x860)
    # 으로는 하단 저장 버튼과 오른쪽 단가·금액 칸이 잘렸다. 화면이 허락하는 만큼 키운다.
    width = min(1360, max(960, popup.winfo_screenwidth() - 80))
    height = min(1240, max(680, popup.winfo_screenheight() - 90))
    pos_x = max(0, (popup.winfo_screenwidth() - width) // 2)
    pos_y = max(0, (popup.winfo_screenheight() - height) // 6)
    popup.geometry(f"{width}x{height}+{pos_x}+{pos_y}")
    popup.minsize(min(960, width), min(680, height))
    popup.configure(bg=app.theme.color("bg"))
    popup.grab_set()
    popup.bind("<Destroy>", lambda event, card_no=no: app.open_popups.pop(card_no, None) if event.widget is popup else None)

    frame = ttk.Frame(popup, padding=16)
    frame.pack(fill=tk.BOTH, expand=True)
    # 오른쪽(공정별 시간)은 숫자 네 칸이 다 보여야 하므로 최소 폭을 고정으로 확보하고,
    # 남는 폭은 왼쪽(기본 정보/소재/Comment/Size)이 가져간다. 비율(weight)로만 나누면
    # 왼쪽 입력칸들의 요구 폭이 커서 오른쪽이 눌리고 금액 칸이 잘렸다.
    frame.columnconfigure(0, weight=1, minsize=520)
    frame.columnconfigure(1, weight=0, minsize=440)
    # 입력 영역만 늘어나고 맨 아래 저장 버튼 줄은 창이 작아도 항상 보이게 한다.
    frame.rowconfigure(1, weight=1)

    summary_vars = build_info_panel(app, frame, item)

    left = ttk.Frame(frame)
    left.grid(row=1, column=0, sticky="nsew", padx=(0, 18))
    fields = {}

    info = ttk.LabelFrame(left, text="기본 정보", padding=10)
    info.pack(fill=tk.X, pady=(0, 10))
    info.columnconfigure(1, weight=1)
    info.columnconfigure(3, weight=1)

    headers = app.settings.get("headers", {})
    text_rows = [
        (f"{headers.get('part_no', '품번')} *", "part_no", 0, 0),
        (f"{headers.get('part_name', '품명')} *", "part_name", 0, 2),
        (headers.get("model", "기종"), "model", 1, 0),
    ]
    for label, key, row, col in text_rows:
        ttk.Label(info, text=label).grid(row=row, column=col, sticky="e", padx=6, pady=6)
        fields[key] = tk.StringVar(value=item[key])
        ttk.Entry(info, textvariable=fields[key], width=18).grid(
            row=row, column=col + 1, sticky="ew", padx=6, pady=6)

    ttk.Label(info, text=f"{headers.get('qty', 'Qty')}").grid(row=1, column=2, sticky="e", padx=6, pady=6)
    fields["qty"] = tk.StringVar(value=str(item["qty"]))
    _numeric_entry(info, fields["qty"], width=18, allow_decimal=False).grid(
        row=1, column=3, sticky="ew", padx=6, pady=6)

    ttk.Label(info, text=headers.get("possible", "가능여부")).grid(row=2, column=0, sticky="e", padx=6, pady=6)
    fields["possible"] = tk.StringVar(value=item["possible"])
    ttk.Combobox(info, textvariable=fields["possible"], values=["가능", "불가", "검토필요"],
                 state="readonly", width=15).grid(row=2, column=1, sticky="w", padx=6, pady=6)

    material_var, heat_var, hrc_min_var, hrc_max_var = _build_material_section(app, left, item)
    comment_text = _build_comment_section(app, left, item)
    final_size_var, get_weight = _build_size_section(app, left, item, material_var)

    machine_fields = config.get_machine_fields()
    times = ttk.LabelFrame(frame, text="각 공정별 시간 입력", padding=10)
    times.grid(row=1, column=1, sticky="nsew")
    # 시간/단가/금액 칸에 최소 폭을 준다. 안 주면 공정 이름 열이 남는 폭을 다 가져가
    # 오른쪽 숫자가 '70,0…'처럼 잘린다.
    times.columnconfigure(0, weight=0, minsize=90)
    for col in (1, 2, 3):
        times.columnconfigure(col, weight=1, minsize=86)
    amount_vars = {}
    for col, header in enumerate(["공정", "시간(h)", "단가(원)", "금액(원)"]):
        ttk.Label(times, text=header, style="Head.TLabel", padding=(6, 4)).grid(
            row=0, column=col, sticky="ew", padx=3, pady=(0, 6))
    for idx, (key, label) in enumerate(machine_fields):
        row_index = idx + 1
        ttk.Label(times, text=label).grid(row=row_index, column=0, sticky="w", padx=6, pady=4)
        fields[key] = tk.StringVar(value=(str(item[key]) if item[key] > 0 else ""))
        _numeric_entry(times, fields[key], width=10).grid(
            row=row_index, column=1, sticky="ew", padx=4, pady=4)
        # v0.0.9: 단가는 설정창에서만 고친다. 여기서는 읽기 전용으로 보여 주기만 한다.
        ttk.Label(times, text=f"{int(app.rates[key]):,}", anchor="e").grid(
            row=row_index, column=2, sticky="ew", padx=4, pady=4)
        amount_vars[key] = tk.StringVar(value="0")
        ttk.Label(times, textvariable=amount_vars[key], style="Value.TLabel", anchor="e").grid(
            row=row_index, column=3, sticky="ew", padx=4, pady=4)
    # wraplength를 주지 않으면 이 한 줄이 오른쪽 영역 전체 폭을 밀어내 왼쪽 입력칸이 눌린다.
    ttk.Label(times, text="단가는 설정창에서 정한 값이 모든 카드에 적용됩니다.",
              style="Muted.TLabel", wraplength=340, justify="left").grid(
        row=len(machine_fields) + 1, column=0, columnspan=4, sticky="w", padx=6, pady=(8, 0))

    def update_amounts(*args):
        sum_time, cost_sum, has_error = 0.0, 0.0, False
        for key, _ in machine_fields:
            hours = parse_number(fields[key].get())
            if hours is None or hours < 0:
                amount_vars[key].set("입력오류")
                has_error = True
                continue
            rate = app.rates[key]
            amount_vars[key].set(f"{int(hours * rate):,}")
            sum_time += hours
            cost_sum += hours * rate
        qty = parse_number(fields["qty"].get())
        if qty is None or qty <= 0:
            qty = 1
        unit_price = cost_sum * qty
        summary_vars["sum_time"].set("입력오류" if has_error else f"{sum_time:.1f} h")
        summary_vars["unit_price"].set("입력오류" if has_error else f"{int(unit_price):,} 원")
        summary_vars["final_price"].set("입력오류" if has_error else f"{int(unit_price // 1000 * 1000):,} 원")

    for key, _ in machine_fields:
        fields[key].trace_add("write", update_amounts)
    fields["qty"].trace_add("write", update_amounts)
    update_amounts()

    def read_comment():
        return comment_text.get("1.0", "end-1c")

    # ESC로 닫기. 값을 바꾼 채로 실수로 누르면 입력이 통째로 날아갈 수 있어,
    # 열 때 찍어 둔 스냅샷과 달라졌을 때만 확인한다.
    # Comment는 tk.Text라 StringVar가 없어 따로 챙긴다.
    initial_snapshot = {key: var.get() for key, var in fields.items()}
    initial_snapshot["_size"] = final_size_var.get()
    initial_snapshot["_comment"] = read_comment()
    initial_snapshot["_material"] = material_var.get()
    initial_snapshot["_heat"] = heat_var.get()
    initial_snapshot["_hrc"] = (hrc_min_var.get(), hrc_max_var.get())

    def has_unsaved_changes():
        if final_size_var.get() != initial_snapshot["_size"]:
            return True
        if read_comment() != initial_snapshot["_comment"]:
            return True
        if material_var.get() != initial_snapshot["_material"]:
            return True
        if heat_var.get() != initial_snapshot["_heat"]:
            return True
        if (hrc_min_var.get(), hrc_max_var.get()) != initial_snapshot["_hrc"]:
            return True
        return any(var.get() != initial_snapshot[key] for key, var in fields.items())

    def close_popup(event=None):
        if has_unsaved_changes() and not messagebox.askyesno(
                "입력 확인", "저장하지 않은 변경 사항이 있습니다.\n저장하지 않고 닫으시겠습니까?", parent=popup):
            return
        if not has_item_data(item):
            app.data = [row for row in app.data if row["no"] != no]
            app.selected_nos.discard(no)
            app.save_session()
            app.refresh_table(True)
        popup.destroy()

    popup.bind("<Escape>", close_popup)
    popup.protocol("WM_DELETE_WINDOW", close_popup)
    def save_and_close(next_item=False):
        if not fields["part_no"].get().strip() or not fields["part_name"].get().strip():
            messagebox.showerror("입력 오류", "품번과 품명은 필수 입력 항목입니다.", parent=popup)
            return
        try:
            qty_value = int(fields["qty"].get().strip())
            if qty_value <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("입력 오류", "수량(Qty)은 1 이상의 정수로 입력하셔야 합니다.", parent=popup)
            return
        mach_values = {}
        for key, label in machine_fields:
            value = fields[key].get().strip()
            try:
                mach_values[key] = float(value) if value else 0.0
            except ValueError:
                messagebox.showerror("입력 오류", "공수 시간은 숫자로 입력해 주세요 (예: 1.5).", parent=popup)
                return
        hrc_min = hrc_min_var.get().strip()
        hrc_max = hrc_max_var.get().strip()
        if heat_var.get():
            for text in (hrc_min, hrc_max):
                if text and parse_number(text) is None:
                    messagebox.showerror("입력 오류", "HRC 경도는 숫자로 입력해 주세요 (예: 58).", parent=popup)
                    return

        item["part_no"] = fields["part_no"].get().strip()
        item["part_name"] = fields["part_name"].get().strip()
        item["model"] = fields["model"].get().strip()
        item["material"] = material_var.get().strip()
        item["heat_treat"] = bool(heat_var.get())
        item["hrc_min"] = hrc_min if heat_var.get() else ""
        item["hrc_max"] = hrc_max if heat_var.get() else ""
        item["size"] = final_size_var.get().strip()
        item["weight"] = get_weight()
        item["comment"] = read_comment().strip()
        item["possible"] = fields["possible"].get().strip()
        item["qty"] = qty_value
        item["save_pending"] = True
        item.update(mach_values)

        app.save_session()
        app.refresh_table(True)
        popup.destroy()
        if next_item:
            app.open_next_item(no)

    btns = ttk.Frame(frame)
    btns.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(18, 0))
    ttk.Button(btns, text="저장 후 다음 항목 입력", command=lambda: save_and_close(True)).pack(side=tk.LEFT)
    ttk.Button(btns, text="저장", command=lambda: save_and_close(False)).pack(side=tk.RIGHT)
