"""카드를 눌렀을 때 뜨는 상세 입력 팝업창."""

import re
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

from ..core import config
from ..core.model import parse_number
from ..core.pricing import calc_row

SHAPE_BLOCK = "블록"
SHAPE_ROD = "로드"
SHAPE_CUSTOM = "직접입력"


def build_info_panel(app, parent, item):
    """팝업 상단에 항목 정보 전체를 펼쳐 놓는다. 금액 3종은 입력에 따라 실시간으로 바뀐다."""
    info_box = ttk.LabelFrame(parent, text="항목 정보", padding=10)
    info_box.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
    sum_time, unit_price, final_price = calc_row(item, app.rates)
    summary_vars = {
        "sum_time": tk.StringVar(value=f"{sum_time:.1f} h"),
        "unit_price": tk.StringVar(value=f"{int(unit_price):,} 원"),
        "final_price": tk.StringVar(value=f"{final_price:,} 원"),
    }
    static_facts = [
        ("NO", str(item["no"])),
        ("작성일", item["created_at"]),
        ("저장 상태", "저장 대기" if item.get("save_pending") else "저장 완료"),
        ("기계 시트 폴더", item["source_month"] or "신규"),
        ("기계 시트 파일", item["source_file"] or "저장 대기"),
        ("엑셀 행", str(item["excel_row"]) if item.get("excel_row") else "-"),
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


def _build_size_section(parent, item):
    """Size 입력 영역. (최종 Size 변수)를 돌려준다."""
    size_box = ttk.LabelFrame(parent, text="Size (소재 규격) 입력", padding=10)
    size_box.pack(fill=tk.X)

    shape_var = tk.StringVar(value=SHAPE_BLOCK)
    t_var, w_var, l_var, d_var = tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar()
    custom_size_var = tk.StringVar()
    final_size_var = tk.StringVar(value=item["size"])

    # 이미 입력돼 있던 Size 문자열을 보고 어느 형상으로 적었는지 되짚어 칸을 채워 준다.
    current_size = item["size"].strip()
    if "Ø" in current_size or "D*" in current_size:
        shape_var.set(SHAPE_ROD)
        matches = re.findall(r"[\d\.]+", current_size)
        if len(matches) >= 2:
            d_var.set(matches[0])
            l_var.set(matches[1])
    elif "T" in current_size or "W" in current_size or "*" in current_size:
        shape_var.set(SHAPE_BLOCK)
        matches = re.findall(r"[\d\.]+", current_size)
        if len(matches) >= 3:
            t_var.set(matches[0])
            w_var.set(matches[1])
            l_var.set(matches[2])
    elif current_size:
        shape_var.set(SHAPE_CUSTOM)
        custom_size_var.set(current_size)

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
            ttk.Entry(input_subframe, textvariable=t_var, width=10).grid(row=0, column=1, padx=5, pady=2)
            ttk.Label(input_subframe, text="W (폭)").grid(row=0, column=2, padx=3, pady=2)
            ttk.Entry(input_subframe, textvariable=w_var, width=10).grid(row=0, column=3, padx=5, pady=2)
            ttk.Label(input_subframe, text="L (길이)").grid(row=0, column=4, padx=3, pady=2)
            ttk.Entry(input_subframe, textvariable=l_var, width=10).grid(row=0, column=5, padx=5, pady=2)
        elif shape == SHAPE_ROD:
            ttk.Label(input_subframe, text="D (외경/Ø)").grid(row=0, column=0, padx=3, pady=2)
            ttk.Entry(input_subframe, textvariable=d_var, width=12).grid(row=0, column=1, padx=5, pady=2)
            ttk.Label(input_subframe, text="L (길이)").grid(row=0, column=2, padx=3, pady=2)
            ttk.Entry(input_subframe, textvariable=l_var, width=12).grid(row=0, column=3, padx=5, pady=2)
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
    return final_size_var


def open_item_popup(app, no, export_on_save=False):
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
    popup.title(f"[NO. {no}] 기계 시트 항목 입력")
    # 화면 배율이 커도 팝업이 화면 밖으로 넘치지 않도록 표시 영역에 맞춰 크기를 정한다.
    width = min(1180, max(900, popup.winfo_screenwidth() - 80))
    height = min(800, max(600, popup.winfo_screenheight() - 120))
    pos_x = max(0, (popup.winfo_screenwidth() - width) // 2)
    pos_y = max(0, (popup.winfo_screenheight() - height) // 3)
    popup.geometry(f"{width}x{height}+{pos_x}+{pos_y}")
    popup.minsize(min(900, width), min(600, height))
    popup.configure(bg=app.theme.color("bg"))
    popup.grab_set()
    popup.bind("<Destroy>", lambda event, card_no=no: app.open_popups.pop(card_no, None) if event.widget is popup else None)

    frame = ttk.Frame(popup, padding=16)
    frame.pack(fill=tk.BOTH, expand=True)
    frame.columnconfigure(0, weight=3)
    frame.columnconfigure(1, weight=2)

    summary_vars = build_info_panel(app, frame, item)

    left = ttk.Frame(frame)
    left.grid(row=1, column=0, sticky="nsew", padx=(0, 18))
    fields = {}

    info = ttk.LabelFrame(left, text="기본 정보", padding=10)
    info.pack(fill=tk.X, pady=(0, 10))
    info.columnconfigure(1, weight=1)
    info.columnconfigure(3, weight=1)

    text_rows = [
        ("품번 *", "part_no", 0, 0),
        ("품명 *", "part_name", 0, 2),
        ("기종", "model", 1, 0),
        ("Material", "material", 1, 2),
    ]
    for label, key, row, col in text_rows:
        ttk.Label(info, text=label).grid(row=row, column=col, sticky="e", padx=6, pady=6)
        fields[key] = tk.StringVar(value=item[key])
        ttk.Entry(info, textvariable=fields[key], width=18).grid(
            row=row, column=col + 1, sticky="ew", padx=6, pady=6)

    ttk.Label(info, text="수량(Qty)").grid(row=2, column=0, sticky="e", padx=6, pady=6)
    fields["qty"] = tk.StringVar(value=str(item["qty"]))
    ttk.Entry(info, textvariable=fields["qty"], width=18).grid(row=2, column=1, sticky="ew", padx=6, pady=6)

    ttk.Label(info, text="가능여부").grid(row=2, column=2, sticky="e", padx=6, pady=6)
    fields["possible"] = tk.StringVar(value=item["possible"])
    ttk.Combobox(info, textvariable=fields["possible"], values=["가능", "불가", "검토필요"],
                 state="readonly", width=15).grid(row=2, column=3, sticky="w", padx=6, pady=6)

    ttk.Label(info, text="Comment").grid(row=3, column=0, sticky="e", padx=6, pady=6)
    fields["comment"] = tk.StringVar(value=item["comment"])
    ttk.Entry(info, textvariable=fields["comment"], width=18).grid(
        row=3, column=1, columnspan=3, sticky="ew", padx=6, pady=6)

    final_size_var = _build_size_section(left, item)

    machine_fields = config.get_machine_fields()
    times = ttk.LabelFrame(frame, text="각 공정별 시간 / 단가 입력", padding=10)
    times.grid(row=1, column=1, sticky="nsew")
    for col in (1, 2, 3):
        times.columnconfigure(col, weight=1)
    rate_fields = {}
    amount_vars = {}
    for col, header in enumerate(["공정", "시간(h)", "단가(원)", "금액(원)"]):
        ttk.Label(times, text=header, style="Head.TLabel", padding=(6, 4)).grid(
            row=0, column=col, sticky="ew", padx=3, pady=(0, 6))
    for idx, (key, label) in enumerate(machine_fields):
        row_index = idx + 1
        ttk.Label(times, text=label).grid(row=row_index, column=0, sticky="w", padx=6, pady=4)
        fields[key] = tk.StringVar(value=(str(item[key]) if item[key] > 0 else ""))
        ttk.Entry(times, textvariable=fields[key], width=10).grid(
            row=row_index, column=1, sticky="ew", padx=4, pady=4)
        rate_fields[key] = tk.StringVar(value=str(int(app.rates[key])))
        ttk.Entry(times, textvariable=rate_fields[key], width=10).grid(
            row=row_index, column=2, sticky="ew", padx=4, pady=4)
        amount_vars[key] = tk.StringVar(value="0")
        ttk.Label(times, textvariable=amount_vars[key], style="Value.TLabel", anchor="e").grid(
            row=row_index, column=3, sticky="ew", padx=4, pady=4)
    ttk.Label(times, text="단가는 견적 양식 5행에 공통 적용됩니다.", style="Muted.TLabel").grid(
        row=len(machine_fields) + 1, column=0, columnspan=4, sticky="w", padx=6, pady=(8, 0))

    def update_amounts(*args):
        sum_time, cost_sum, has_error = 0.0, 0.0, False
        for key, _ in machine_fields:
            hours = parse_number(fields[key].get())
            rate = parse_number(rate_fields[key].get())
            if hours is None or rate is None or hours < 0 or rate < 0:
                amount_vars[key].set("입력오류")
                has_error = True
                continue
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
        rate_fields[key].trace_add("write", update_amounts)
    fields["qty"].trace_add("write", update_amounts)
    update_amounts()

    # ESC로 닫기(요청: "카드 로드 후 닫기 별도 없이 esc 누르면 닫힘"). 값을 바꾼 채로
    # 실수로 누르면 공수 시간 입력이 통째로 날아갈 수 있어, 스냅샷과 달라졌을 때만 확인한다.
    initial_snapshot = {key: var.get() for key, var in fields.items()}
    initial_snapshot.update({f"rate:{key}": var.get() for key, var in rate_fields.items()})
    initial_snapshot["_size"] = final_size_var.get()

    def has_unsaved_changes():
        if final_size_var.get() != initial_snapshot["_size"]:
            return True
        if any(var.get() != initial_snapshot[key] for key, var in fields.items()):
            return True
        return any(var.get() != initial_snapshot[f"rate:{key}"] for key, var in rate_fields.items())

    def close_on_escape(event=None):
        if has_unsaved_changes() and not messagebox.askyesno(
                "입력 확인", "저장하지 않은 변경 사항이 있습니다.\n저장하지 않고 닫으시겠습니까?", parent=popup):
            return
        popup.destroy()

    popup.bind("<Escape>", close_on_escape)

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
        mach_values, rate_values = {}, {}
        for key, label in machine_fields:
            value = fields[key].get().strip()
            try:
                mach_values[key] = float(value) if value else 0.0
            except ValueError:
                messagebox.showerror("입력 오류", "공수 시간은 숫자로 입력해 주세요 (예: 1.5).", parent=popup)
                return
            rate_text = rate_fields[key].get().strip().replace(",", "")
            try:
                rate_value = float(rate_text) if rate_text else 0.0
            except ValueError:
                messagebox.showerror("입력 오류", f"'{label}' 단가는 숫자로 입력해 주세요.", parent=popup)
                return
            if rate_value < 0:
                messagebox.showerror("입력 오류", f"'{label}' 단가는 0 이상으로 입력해 주세요.", parent=popup)
                return
            rate_values[key] = rate_value

        item["part_no"] = fields["part_no"].get().strip()
        item["part_name"] = fields["part_name"].get().strip()
        item["model"] = fields["model"].get().strip()
        item["material"] = fields["material"].get().strip()
        item["size"] = final_size_var.get().strip()
        item["comment"] = fields["comment"].get().strip()
        item["possible"] = fields["possible"].get().strip()
        item["qty"] = qty_value
        item["save_pending"] = True
        item.update(mach_values)
        app.rates.update(rate_values)

        if export_on_save:
            if not app.export_items([item], default_name=f"신규견적_{datetime.now():%Y-%m-%d}.xlsx", parent=popup):
                return
        app.save_session()
        app.refresh_table(True)
        popup.destroy()

        if export_on_save and not messagebox.askyesno(
                "신규 입력 반영", "방금 다운로드한 신규 항목을 현재 카드 목록에도 유지하시겠습니까?", parent=app.root):
            app.data = [row for row in app.data if row["no"] != no]
            app.selected_nos.discard(no)
            app.save_session()
            app.refresh_table(True)
            return
        if next_item:
            app.open_next_item(no)

    btns = ttk.Frame(frame)
    btns.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(18, 0))
    ttk.Button(btns, text="저장 후 다음 항목 입력", command=lambda: save_and_close(True)).pack(side=tk.LEFT)
    ttk.Button(btns, text="저장", command=lambda: save_and_close(False)).pack(side=tk.RIGHT)
