"""신규 등록분만 모아 입력·검토·출력한 뒤 본래 현황판으로 이관하는 창."""

import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

from ..core.model import create_blank_item, get_next_no, has_item_data, sort_new_items
from ..core.pricing import calc_row
from .popup import open_item_popup


class NewItemsDialog:
    def __init__(self, app):
        self.app = app
        self.window = tk.Toplevel(app.root)
        app.new_items_window = self
        self.window.title("신규품목 등록")
        self.window.geometry("1120x620")
        self.window.minsize(900, 480)
        self.window.configure(bg=app.theme.color("bg"))
        self.window.protocol("WM_DELETE_WINDOW", self.close)

        frame = ttk.Frame(self.window, padding=16)
        frame.pack(fill=tk.BOTH, expand=True)
        top = ttk.Frame(frame)
        top.pack(fill=tk.X, pady=(0, 12))
        ttk.Label(top, text="신규품목", font=app.theme.header_title).pack(side=tk.LEFT)
        self.summary_var = tk.StringVar()
        ttk.Label(top, textvariable=self.summary_var, style="Muted.TLabel").pack(
            side=tk.LEFT, padx=(16, 0))

        columns = ("registered", "part_no", "part_name", "model", "qty", "material", "possible", "price")
        self.tree = ttk.Treeview(frame, columns=columns, show="headings", selectmode="extended")
        headings = {
            "registered": "등록 시각", "part_no": "품번", "part_name": "품명", "model": "기종",
            "qty": "Qty", "material": "Material", "possible": "가능여부", "price": "최종단가",
        }
        widths = {"registered": 150, "part_no": 150, "part_name": 170, "model": 110,
                  "qty": 55, "material": 130, "possible": 80, "price": 120}
        for key in columns:
            self.tree.heading(key, text=headings[key])
            self.tree.column(key, width=widths[key], minwidth=45,
                             anchor="e" if key in ("qty", "price") else "w")
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind("<Double-1>", lambda event: self.edit_selected())

        buttons = ttk.Frame(frame)
        buttons.pack(fill=tk.X, pady=(14, 0))
        ttk.Button(buttons, text="신규 추가", command=self.add_item).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(buttons, text="선택 수정", command=self.edit_selected).pack(side=tk.LEFT, padx=6)
        ttk.Button(buttons, text="선택 삭제", command=self.delete_selected).pack(side=tk.LEFT, padx=6)
        ttk.Button(buttons, text="신규품목 출력", command=self.export_all).pack(side=tk.RIGHT, padx=(6, 0))
        ttk.Button(buttons, text="본래 창으로 이관", command=self.transfer_all).pack(side=tk.RIGHT, padx=6)
        self.refresh()

    def close(self):
        if any(isinstance(key, tuple) and key[0] == "new" for key in self.app.open_popups):
            messagebox.showwarning("창을 닫을 수 없음", "열려 있는 신규품목 입력창을 먼저 닫아 주세요.",
                                   parent=self.window)
            return
        self.app.new_items_window = None
        self.window.destroy()

    def _next_draft_no(self):
        return max([int(item.get("draft_no", 0)) for item in self.app.new_items], default=0) + 1

    def add_item(self):
        draft_no = self._next_draft_no()
        item = create_blank_item(-draft_no)
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        item["draft_no"] = draft_no
        item["registered_at"] = stamp
        item["added_at"] = stamp
        item["is_new_registration"] = True
        self.app.new_items.append(item)
        self.refresh()
        self._open_item(item)

    def _selected_items(self):
        selected = set(self.tree.selection())
        return [item for item in self.app.new_items if str(item["no"]) in selected]

    def edit_selected(self):
        items = self._selected_items()
        if not items:
            messagebox.showinfo("선택 없음", "수정할 신규품목을 선택하세요.", parent=self.window)
            return
        self._open_item(items[0])

    def _open_item(self, item):
        draft_no = item.get("draft_no", abs(item["no"]))
        open_item_popup(
            self.app, item["no"], items=self.app.new_items,
            popup_key=("new", item["no"]), on_change=self.refresh,
            on_next=self.add_item, title_label=f"신규 {draft_no}")

    def delete_selected(self):
        items = self._selected_items()
        if not items:
            messagebox.showinfo("선택 없음", "삭제할 신규품목을 선택하세요.", parent=self.window)
            return
        blocked = [item for item in items if ("new", item["no"]) in self.app.open_popups]
        if blocked:
            messagebox.showwarning("삭제할 수 없음", "입력창이 열린 품목은 먼저 입력창을 닫아 주세요.",
                                   parent=self.window)
            return
        if not messagebox.askyesno("신규품목 삭제", f"선택한 {len(items)}개 품목을 삭제할까요?",
                                   parent=self.window, default="no"):
            return
        target_ids = {id(item) for item in items}
        self.app.new_items[:] = [item for item in self.app.new_items if id(item) not in target_ids]
        self.app.save_session()
        self.refresh()

    def export_all(self):
        items = [item for item in sort_new_items(self.app.new_items) if has_item_data(item)]
        if self.app.export_items(
                items, default_name=f"신규품목_{datetime.now():%Y-%m-%d}.xlsx", parent=self.window):
            self.refresh()

    def transfer_all(self):
        if any(key[0] == "new" for key in self.app.open_popups if isinstance(key, tuple)):
            messagebox.showwarning("이관할 수 없음", "열려 있는 신규품목 입력창을 모두 닫아 주세요.",
                                   parent=self.window)
            return
        ordered = sort_new_items(self.app.new_items)
        if not ordered:
            messagebox.showinfo("이관 대상 없음", "이관할 신규품목이 없습니다.", parent=self.window)
            return
        incomplete = [item for item in ordered if not has_item_data(item)]
        if incomplete:
            messagebox.showwarning("입력 미완료", "입력이 끝나지 않은 신규품목이 있습니다.", parent=self.window)
            return
        if not messagebox.askyesno(
                "본래 창으로 이관", f"신규품목 {len(ordered)}개를 본래 현황판으로 이관할까요?",
                parent=self.window):
            return

        next_no = get_next_no(self.app.data)
        for item in ordered:
            item["no"] = next_no
            item.pop("draft_no", None)
            item["save_pending"] = True
            self.app.data.append(item)
            next_no += 1
        self.app.new_items.clear()
        self.app.save_session()
        self.app.refresh_table(True)
        self.refresh()
        messagebox.showinfo("이관 완료", f"신규품목 {len(ordered)}개를 본래 현황판으로 이관했습니다.",
                            parent=self.window)

    def refresh(self):
        selected = set(self.tree.selection())
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        ordered = sort_new_items(self.app.new_items)
        valid_count = 0
        total = 0
        for item in ordered:
            _, _, final_price = calc_row(item, self.app.rates)
            if has_item_data(item):
                valid_count += 1
                total += final_price
            registered = str(item.get("registered_at", item.get("added_at", ""))).split(".")[0]
            iid = str(item["no"])
            self.tree.insert("", "end", iid=iid, values=(
                registered, item.get("part_no") or "(미입력)", item.get("part_name") or "(미입력)",
                item.get("model", ""), item.get("qty", 1), item.get("material", ""),
                item.get("possible", "가능"), f"{final_price:,} 원"))
            if iid in selected:
                self.tree.selection_add(iid)
        self.summary_var.set(f"등록 {valid_count}건  |  합계 {total:,}원  |  먼저 등록한 품목부터 표시")


def open_new_items_dialog(app, add_immediately=False):
    dialog = app.new_items_window
    if dialog is not None and dialog.window.winfo_exists():
        dialog.window.lift()
        dialog.window.focus_force()
    else:
        dialog = NewItemsDialog(app)
    if add_immediately:
        dialog.add_item()
    return dialog
