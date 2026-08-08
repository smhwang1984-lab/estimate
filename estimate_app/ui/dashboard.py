"""메인 화면(카드 목록)과 전체 흐름을 붙잡고 있는 클래스."""

import os
import shutil
import subprocess
import tempfile
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

from .. import APP_TITLE, APP_VERSION
from ..core import config, excel_io, paths, pdf_export, session, updater
from ..core.model import create_blank_item, filter_items, get_next_no, has_item_data
from ..core.pricing import calc_total_amount
from .popup import open_item_popup
from .table import (COLUMNS, build_header, build_header_underline, create_row_slot,
                    hide_row_slot, render_empty_message, update_row_slot)
from .theme import Theme


class EstimateApp:
    def __init__(self, root):
        self.root = root
        self.theme = Theme()
        self.root.title(f"{APP_TITLE} v{APP_VERSION}")
        self.root.geometry(self.theme.layout["window_size"])
        self.root.minsize(self.theme.layout["min_width"], self.theme.layout["min_height"])
        self._apply_window_icon()

        self.data = []
        self.rates = config.load_rates()
        self.display_page_size = self.theme.layout["page_size"]
        self.display_limit = self.display_page_size
        self.session_restored_count = 0
        self.session_saved_at = None
        self.is_saving = False
        self.search_after_id = None
        self.selected_nos = set()
        # 표 갱신 구조(v0.0.8): 행 위젯을 destroy 후 재생성하지 않고 풀로 재사용한다
        # (33행 기준 첫 그리기 약 3.9초 -> 위젯을 새로 만들지 않으면 훨씬 가벼워짐, 검색
        # 시 카드가 깜빡이던 것도 이 방식으로 같이 사라진다).
        self.row_slots = []
        self.no_to_slot = {}
        self.more_button_frame = None
        self.more_button = None
        self.empty_frame = None
        self.open_popups = {}

        self.theme.apply(self.root)
        self.maximize_window()
        self.build_dashboard()
        self.restore_session()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        # ESC로 선택 취소(요청: "선택 체크박스 후 esc누르면 선택 취소"). 팝업은 별도
        # Toplevel이라 여기서 건 바인딩과 서로 간섭하지 않는다(포커스가 팝업에 있으면
        # 팝업의 <Escape> 바인딩만 반응한다).
        self.root.bind("<Escape>", lambda event: self.clear_selection())
        # 저장된 항목이 많으면 표를 다 그리는 데 몇 초가 걸린다. 그 동안 아무것도 안 뜬 것처럼
        # 보이지 않도록 창을 먼저 띄우고, 목록은 곧바로 이어서 채운다.
        self.summary_var.set("목록을 불러오는 중입니다...")
        self.root.after_idle(lambda: self.refresh_table(True))
        self.root.after(800, self.check_for_update)

    # ---------- 창 기본 동작 ----------

    def on_close(self):
        self.save_session()
        self.root.destroy()

    def maximize_window(self):
        try:
            self.root.state("zoomed")
        except tk.TclError:
            pass

    def _apply_window_icon(self):
        # spec의 EXE(icon=...)는 실행 파일·바탕화면 아이콘만 바꾼다. 창 좌상단·작업표시줄
        # 아이콘은 Tk가 따로 그리므로 root.iconbitmap()을 별도로 불러야 한다.
        ico_path = paths.get_asset_path("estimate.ico")
        try:
            self.root.iconbitmap(ico_path)
        except tk.TclError:
            pass

    # ---------- 화면 구성 ----------

    def build_dashboard(self):
        c = self.theme.colors
        self.root.configure(bg=c["bg"])

        # 헤더 바. PIL 없이 Canvas.create_line만으로 grad_from -> grad_to 좌->우 그라데이션을
        # 그린다(v0.0.8: 밝은 그라데이션 테마, 배포 용량 증가 0MB). 텍스트는 Canvas 항목이라
        # textvariable을 못 쓰므로 summary_var에 trace를 걸어 itemconfigure로 밀어 넣는다.
        header_height = 112
        self.header_canvas = tk.Canvas(self.root, height=header_height,
                                       highlightthickness=0, bg=c["grad_fallback"])
        self.header_canvas.pack(fill=tk.X)
        self._header_width = 0

        self.header_title_id = self.header_canvas.create_text(
            18, 24, anchor="w", text=APP_TITLE, fill=c["panel_fg"], font=self.theme.header_title)
        self.summary_var = tk.StringVar()
        self.summary_var.trace_add("write", lambda *args: self._sync_header_summary())
        self.header_summary_id = self.header_canvas.create_text(
            18, 60, anchor="w", text="", fill=c["panel_muted_fg"], font=self.theme.normal)
        self.header_canvas.create_text(
            18, 86, anchor="w", text="행을 클릭하면 팝업창에 항목 정보 전체와 상세 입력이 표시됩니다.",
            fill=c["panel_muted_fg"], font=self.theme.small)

        actions = tk.Frame(self.header_canvas, bg=c["panel_2"])
        ttk.Button(actions, text="기계 시트 업로드", command=self.upload_excel_file).pack(side=tk.LEFT, padx=4)
        ttk.Button(actions, text="새 항목 추가", command=self.add_row).pack(side=tk.LEFT, padx=4)
        ttk.Button(actions, text="날짜별 누적 저장", command=self.save_to_excel).pack(side=tk.LEFT, padx=4)
        self.header_actions_id = self.header_canvas.create_window(
            0, header_height // 2, anchor="e", window=actions)

        self.header_canvas.bind("<Configure>", self._on_header_configure)

        tk.Frame(self.root, bg=c["line"], height=1).pack(fill=tk.X)

        search = tk.Frame(self.root, bg=c["bg"], padx=16, pady=12)
        search.pack(fill=tk.X)
        tk.Label(search, text="Search", bg=c["bg"], fg=c["text"], font=self.theme.bold).pack(side=tk.LEFT, padx=(0, 8))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.schedule_refresh())
        ttk.Entry(search, textvariable=self.search_var, width=42).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(search, text="검색 초기화", command=self.clear_search).pack(side=tk.LEFT)
        tk.Label(search, text="Search는 품번/품명/기종 대상, 공백/쉼표로 여러 조건 입력 가능",
                 bg=c["bg"], fg=c["muted"]).pack(side=tk.LEFT, padx=(12, 0))

        extra_actions = tk.Frame(search, bg=c["bg"])
        extra_actions.pack(side=tk.RIGHT)
        tk.Label(extra_actions, text="보조 기능", bg=c["bg"], fg=c["muted"],
                 font=self.theme.small).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(extra_actions, text="신규 입력 다운로드", command=self.add_download_row).pack(side=tk.LEFT, padx=4)
        ttk.Button(extra_actions, text="전체 선택", command=self.select_visible_items).pack(side=tk.LEFT, padx=4)
        ttk.Button(extra_actions, text="선택 해제", command=self.clear_selection).pack(side=tk.LEFT, padx=4)
        ttk.Button(extra_actions, text="선택 다운로드", command=self.export_selected_items).pack(side=tk.LEFT, padx=4)

        # 현황판 영역. 스크롤바를 먼저 오른쪽에 붙이고, 남은 폭 안에
        # [구역 제목 / 고정 헤더 / 스크롤되는 본문]을 쌓아야 헤더와 본문의 열이 어긋나지 않는다.
        board = tk.Frame(self.root, bg=c["bg"])
        board.pack(fill=tk.BOTH, expand=True)
        self.row_scrollbar = ttk.Scrollbar(board, orient=tk.VERTICAL)
        self.row_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        column = tk.Frame(board, bg=c["bg"])
        column.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        pane_head = tk.Frame(column, bg=c["pane_head_bg"])
        pane_head.pack(fill=tk.X)
        tk.Label(pane_head, text="■ 견적 현황", bg=c["pane_head_bg"], fg=c["pane_head_fg"],
                 font=self.theme.pane_head, padx=14, pady=4).pack(anchor="w")
        tk.Frame(column, bg=c["line"], height=1).pack(fill=tk.X)

        build_header(column, self.theme).pack(fill=tk.X)
        build_header_underline(column, self.theme).pack(fill=tk.X)

        self.row_canvas = tk.Canvas(column, bg=c["row_bg"], highlightthickness=0)
        self.row_canvas.configure(yscrollcommand=self.row_scrollbar.set)
        self.row_scrollbar.configure(command=self.row_canvas.yview)
        self.row_canvas.pack(fill=tk.BOTH, expand=True)
        self.row_container = tk.Frame(self.row_canvas, bg=c["row_bg"])
        self.row_container.columnconfigure(0, weight=1)
        self.row_window = self.row_canvas.create_window((0, 0), window=self.row_container, anchor="nw")
        self.row_container.bind("<Configure>", lambda e: self._update_canvas())
        self.row_canvas.bind("<Configure>", lambda e: self._update_canvas())
        self.row_canvas.bind("<Enter>", lambda e: self.row_canvas.bind_all("<MouseWheel>", self._on_mousewheel))
        self.row_canvas.bind("<Leave>", lambda e: self.row_canvas.unbind_all("<MouseWheel>"))

    def _on_header_configure(self, event):
        # 폭이 실제로 달라졌을 때만 그라데이션을 다시 그린다. 안 그러면 창을 끌 때마다
        # 반복해서 다시 칠해 무거워진다(높이 변화는 헤더가 고정 높이라 발생하지 않는다).
        if event.width != self._header_width:
            self._header_width = event.width
            self.theme.paint_gradient(self.header_canvas, event.width, event.height)
        self.header_canvas.coords(self.header_actions_id, event.width - 18, event.height // 2)

    def _sync_header_summary(self):
        if hasattr(self, "header_summary_id"):
            self.header_canvas.itemconfigure(self.header_summary_id, text=self.summary_var.get())

    def _update_canvas(self):
        self.row_canvas.configure(scrollregion=self.row_canvas.bbox("all"))
        self.row_canvas.itemconfigure(self.row_window, width=self.row_canvas.winfo_width())

    def _on_mousewheel(self, event):
        self.row_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    # ---------- 세션 ----------

    def save_session(self):
        search_text = self.search_var.get() if hasattr(self, "search_var") else ""
        session.save(self.data, self.rates, self.selected_nos, search_text)

    def restore_session(self):
        payload = session.load()
        if not payload:
            return
        self.data = payload["items"]
        self.rates.update(payload["rates"])
        self.selected_nos = set(payload["selected_nos"])
        if hasattr(self, "search_var"):
            self.search_var.set(payload["search"])
        self.session_restored_count = len(self.data)
        self.session_saved_at = payload["saved_at"]

    # ---------- 목록 갱신 ----------

    def get_search_text(self):
        return self.search_var.get().strip() if hasattr(self, "search_var") else ""

    def schedule_refresh(self):
        # 타자를 칠 때마다 목록을 다시 그리지 않도록 잠깐 모았다가 한 번만 갱신한다.
        if self.search_after_id:
            self.root.after_cancel(self.search_after_id)
        self.search_after_id = self.root.after(250, lambda: self.refresh_table(True))

    def show_more_cards(self):
        self.display_limit += self.display_page_size
        self.refresh_table(False)

    def _summary_text(self, all_items, visible_items, query):
        selected_count = len([item for item in all_items if item["no"] in self.selected_nos])
        total_amount = calc_total_amount(all_items, self.rates)
        today = datetime.now().strftime("%Y-%m-%d")
        search_note = f"  |  검색 결과 {len(visible_items)}건" if query else ""
        select_note = f"  |  선택 {selected_count}건"
        if self.session_saved_at:
            session_note = f"  |  세션 복원 {self.session_restored_count}건 (저장 {self.session_saved_at})"
        else:
            session_note = "  |  새 세션 (저장된 데이터 없음)"
        return (f"작성일 {today}  |  항목 {len(all_items)}건  |  총 견적금액 {total_amount:,}원"
               f"{search_note}{select_note}{session_note}")

    def update_summary_text(self):
        """표 위젯은 건드리지 않고 상단 요약줄(선택 건수 등)만 다시 계산한다."""
        query = self.get_search_text()
        all_items, visible_items = filter_items(self.data, query)
        self.summary_var.set(self._summary_text(all_items, visible_items, query))

    def refresh_table(self, reset_limit=False):
        """목록을 다시 그린다. 위젯을 지웠다 새로 만들지 않고 슬롯 풀을 재사용한다.

        reset_limit=True는 "목록의 내용 자체가 바뀌었다"는 신호로도 쓴다(검색·검색초기화·
        업로드 등). 그때만 스크롤을 맨 위로 되돌린다 — 더보기·체크 토글에서 스크롤이
        튀면 오히려 불편하기 때문이다.
        """
        if reset_limit:
            self.display_limit = self.display_page_size
        self.search_after_id = None

        query = self.get_search_text()
        all_items, visible_items = filter_items(self.data, query)
        self.selected_nos.intersection_update({item["no"] for item in all_items})
        self.summary_var.set(self._summary_text(all_items, visible_items, query))

        if not all_items:
            self._hide_rows()
            self._show_empty("아직 작성된 견적 항목이 없습니다.",
                             "상단의 '기계 시트 업로드' 또는 '새 항목 추가'를 사용하세요.")
            if reset_limit:
                self.row_canvas.yview_moveto(0)
            return
        if not visible_items:
            self._hide_rows()
            self._show_empty("검색 결과가 없습니다.", "품번, 품명, 기종으로 검색할 수 있습니다.")
            if reset_limit:
                self.row_canvas.yview_moveto(0)
            return

        self._hide_empty()
        shown = visible_items[:self.display_limit]
        while len(self.row_slots) < len(shown):
            self.row_slots.append(create_row_slot(self))

        self.no_to_slot = {}
        for row_index, item in enumerate(shown):
            slot = self.row_slots[row_index]
            update_row_slot(self, slot, item, row_index)
            self.no_to_slot[item["no"]] = slot
        for slot in self.row_slots[len(shown):]:
            hide_row_slot(slot)

        if self.display_limit < len(visible_items):
            self._show_more_button(len(shown), len(visible_items))
        else:
            self._hide_more_button()

        if reset_limit:
            self.row_canvas.yview_moveto(0)

    def row_normal_bg(self, slot):
        """이 슬롯이 지금 보여야 할 '평상시' 배경색(선택/줄무늬 반영)."""
        c = self.theme.colors
        if slot["no"] in self.selected_nos:
            return c["row_selected_bg"]
        return c["row_bg"] if slot["parity"] == 0 else c["row_alt_bg"]

    def _hide_rows(self):
        for slot in self.row_slots:
            hide_row_slot(slot)
        self.no_to_slot = {}
        self._hide_more_button()

    def _show_empty(self, title, detail):
        if self.empty_frame is not None:
            self.empty_frame.destroy()
        self.empty_frame = render_empty_message(self, title, detail)

    def _hide_empty(self):
        if self.empty_frame is not None:
            self.empty_frame.destroy()
            self.empty_frame = None

    def _show_more_button(self, shown_count, total_count):
        if self.more_button_frame is None:
            self.more_button_frame = tk.Frame(self.row_container, bg=self.theme.color("row_bg"), pady=14)
            self.more_button = ttk.Button(self.more_button_frame, command=self.show_more_cards)
            self.more_button.pack(anchor="center")
        self.more_button.configure(text=f"더 보기 ({shown_count}/{total_count})")
        self.more_button_frame.grid(row=shown_count, column=0, columnspan=len(COLUMNS), sticky="ew")

    def _hide_more_button(self):
        if self.more_button_frame is not None:
            self.more_button_frame.grid_remove()

    def update_row_visual(self, no):
        """행 전체를 다시 그리지 않고 체크박스·배경색만 바꾼다(깜빡임 방지)."""
        slot = self.no_to_slot.get(no)
        if not slot:
            return
        selected = no in self.selected_nos
        c = self.theme.colors
        bg = self.row_normal_bg(slot)
        slot["frame"].configure(bg=bg)
        for widget in slot["tinted"]:
            widget.configure(bg=bg)
        box_bg = c["accent"] if selected else c["card_alt"]
        box_fg = c["bg"] if selected else c["muted"]
        border = box_bg if selected else c["checkbox_border"]
        checkbox = slot["checkbox"]
        checkbox.configure(bg=box_bg, highlightbackground=border)
        checkbox.glyph.configure(text=("V" if selected else ""), bg=box_bg, fg=box_fg)

    # ---------- 검색 / 선택 ----------

    def clear_search(self):
        self.search_var.set("")
        self.refresh_table(True)

    def toggle_item_selection(self, no, is_selected):
        if is_selected:
            self.selected_nos.add(no)
        else:
            self.selected_nos.discard(no)
        self.update_row_visual(no)
        self.update_summary_text()

    def select_visible_items(self):
        _, visible_items = filter_items(self.data, self.get_search_text())
        for item in visible_items:
            self.selected_nos.add(item["no"])
            self.update_row_visual(item["no"])
        self.update_summary_text()

    def clear_selection(self):
        for no in list(self.selected_nos):
            self.selected_nos.discard(no)
            self.update_row_visual(no)
        self.update_summary_text()

    # ---------- 카드 추가 / 팝업 ----------

    def add_row(self):
        new_no = get_next_no(self.data)
        self.data.append(create_blank_item(new_no))
        self.refresh_table(True)
        self.open_popup(new_no)

    def add_download_row(self):
        new_no = get_next_no(self.data)
        self.data.append(create_blank_item(new_no))
        self.refresh_table(True)
        self.open_popup(new_no, export_on_save=True)

    def open_popup(self, no, export_on_save=False):
        open_item_popup(self, no, export_on_save)

    def open_next_item(self, no):
        next_no = no + 1
        if not any(row["no"] == next_no for row in self.data):
            self.data.append(create_blank_item(next_no))
        self.refresh_table(True)
        self.open_popup(next_no)

    # ---------- 엑셀 ----------

    def upload_excel_file(self):
        file_path = filedialog.askopenfilename(
            title="업로드할 견적 양식 선택",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")])
        if not file_path:
            return
        try:
            cards = excel_io.read_cards_from_workbook(file_path)
        except Exception as exc:
            messagebox.showerror("업로드 오류", f"선택한 파일을 불러오지 못했습니다.\n\n{exc}")
            return
        if not cards:
            messagebox.showwarning("업로드 안내", "선택한 파일에서 입력된 견적 항목을 찾지 못했습니다.")
            return
        if self.data and not messagebox.askyesno(
                "업로드 확인", f"선택한 파일에서 {len(cards)}개 항목을 찾았습니다.\n현재 카드 목록에 추가하시겠습니까?"):
            return
        next_no = get_next_no(self.data)
        for offset, item in enumerate(cards):
            item["no"] = next_no + offset
            item["excel_row"] = None
            item["save_pending"] = True
            self.data.append(item)
        self.save_session()
        self.refresh_table(True)
        messagebox.showinfo("업로드 완료",
                            f"{len(cards)}개 항목을 카드로 불러왔습니다.\n저장하면 오늘 날짜 누적 파일에 추가됩니다.")

    def save_to_excel(self):
        if self.is_saving:
            messagebox.showwarning("저장 진행 중", "이미 저장 중입니다. 잠시만 기다려 주세요.")
            return
        self.is_saving = True
        try:
            self._save_to_excel_impl()
        finally:
            self.is_saving = False

    def _save_to_excel_impl(self):
        save_items = [item for item in self.data
                      if has_item_data(item) and (item.get("save_pending") or item.get("excel_row"))]
        if not save_items:
            messagebox.showwarning("저장 대상 없음", "입력된 항목이 없어 저장하지 않았습니다.")
            return
        try:
            saved_count, output_path = excel_io.save_daily_accumulated(save_items, self.rates)
        except excel_io.TemplateNotFound as exc:
            messagebox.showerror("파일 오류", f"'{exc}' 파일이 존재하지 않습니다.")
            return
        except excel_io.SheetNotFound as exc:
            messagebox.showerror("시트 오류", f"'{exc}' 시트를 찾을 수 없습니다.")
            return
        except OSError as exc:
            messagebox.showerror("저장 오류", f"파일을 저장하지 못했습니다.\n{exc}")
            return
        for item in save_items:
            item["source_file"] = os.path.basename(output_path)
            item["source_month"] = os.path.basename(os.path.dirname(output_path))
        self.save_session()
        self.refresh_table(False)
        messagebox.showinfo("누적 저장 완료",
                            f"{saved_count}개 항목을 날짜별 파일에 누적 저장했습니다.\n\n{output_path}")

    def choose_output_format(self, parent):
        """엑셀/PDF/둘 다 선택 창. 고른 값('excel'/'pdf'/'both') 또는 취소 시 None."""
        result = {"value": None}
        c = self.theme.colors
        dialog = tk.Toplevel(parent)
        dialog.title("출력 형식 선택")
        dialog.configure(bg=c["panel"])
        dialog.transient(parent)
        dialog.resizable(False, False)
        ttk.Label(dialog, text="어떤 형식으로 저장할까요?", font=self.theme.bold,
                 padding=(20, 18, 20, 4)).pack()
        ttk.Label(dialog, text="PDF는 견적서 시트만 담기며, Microsoft Excel이 설치된 PC에서만 만들 수 있습니다.",
                 style="Muted.TLabel", padding=(20, 0, 20, 12)).pack()

        def pick(value):
            result["value"] = value
            dialog.destroy()

        btns = ttk.Frame(dialog, padding=(20, 0, 20, 18))
        btns.pack()
        ttk.Button(btns, text="엑셀(.xlsx)", command=lambda: pick("excel")).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="PDF", command=lambda: pick("pdf")).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="엑셀 + PDF", command=lambda: pick("both")).pack(side=tk.LEFT, padx=4)
        dialog.protocol("WM_DELETE_WINDOW", lambda: pick(None))
        dialog.update_idletasks()
        px = parent.winfo_rootx() + (parent.winfo_width() - dialog.winfo_width()) // 2
        py = parent.winfo_rooty() + (parent.winfo_height() - dialog.winfo_height()) // 3
        dialog.geometry(f"+{max(0, px)}+{max(0, py)}")
        dialog.grab_set()
        parent.wait_window(dialog)
        return result["value"]

    def export_items(self, items, default_name=None, parent=None):
        if not items:
            messagebox.showwarning("다운로드 대상 없음", "다운로드할 항목을 먼저 선택하거나 입력하세요.", parent=parent)
            return False
        parent = parent or self.root
        output_format = self.choose_output_format(parent)
        if not output_format:
            return False

        base_name = os.path.splitext(default_name or f"선택견적_{datetime.now():%Y-%m-%d}.xlsx")[0]
        wants_pdf = output_format in ("pdf", "both")
        primary_ext = ".pdf" if output_format == "pdf" else ".xlsx"
        chosen_path = filedialog.asksaveasfilename(
            parent=parent,
            title="다운로드 저장 위치 선택",
            defaultextension=primary_ext,
            initialfile=base_name + primary_ext,
            filetypes=([("PDF files", "*.pdf")] if output_format == "pdf"
                      else [("Excel files", "*.xlsx")]))
        if not chosen_path:
            return False

        stem = os.path.splitext(chosen_path)[0]
        xlsx_is_temp = output_format == "pdf"
        pdf_path = chosen_path if output_format == "pdf" else (stem + ".pdf" if wants_pdf else None)

        # 파일 대화상자는 사용자가 직접 입력한 이름(chosen_path)의 겹침만 확인해 준다.
        # PDF 선택 시 자동으로 만들어지는 .xlsx, 엑셀+PDF 선택 시 자동으로 만들어지는 .pdf처럼
        # 화면에 안 보이는 파일을 조용히 덮어썼다가(PDF 전용이면 지우기까지) 사용자의 기존
        # 견적 파일을 날릴 수 있어, 그 경로가 이미 있으면 별도로 물어본다.
        if output_format == "both" and os.path.exists(pdf_path):
            if not messagebox.askyesno(
                    "덮어쓰기 확인",
                    f"'{os.path.basename(pdf_path)}' 파일이 이미 있습니다. 덮어쓸까요?", parent=parent):
                return False

        temp_dir = tempfile.mkdtemp(prefix="est_pdf_") if xlsx_is_temp else None
        xlsx_path = (os.path.join(temp_dir, os.path.basename(stem) + ".xlsx")
                    if xlsx_is_temp else chosen_path)
        try:
            try:
                saved_count = excel_io.export_items(items, self.rates, xlsx_path)
            except excel_io.TemplateNotFound as exc:
                messagebox.showerror("파일 오류", f"'{exc}' 파일이 존재하지 않습니다.", parent=parent)
                return False
            except excel_io.SheetNotFound as exc:
                messagebox.showerror("시트 오류", f"'{exc}' 시트를 찾을 수 없습니다.", parent=parent)
                return False
            except OSError as exc:
                messagebox.showerror("저장 오류", f"파일을 저장하지 못했습니다.\n{exc}", parent=parent)
                return False

            saved_paths = [] if xlsx_is_temp else [xlsx_path]
            if wants_pdf:
                pdf_ok, pdf_error = pdf_export.convert_to_pdf(xlsx_path, pdf_path, excel_io.ESTIMATE_SHEET_NAME)
                if pdf_ok:
                    saved_paths.append(pdf_path)
                elif xlsx_is_temp:
                    # "PDF"만 선택했는데 실패하면 임시 폴더의 xlsx가 finally에서 통째로
                    # 지워져 사용자에게 아무 결과물도 남지 않는다(요청: "pdf 출력 에러
                    # 출력이 안됨" -- 실사용에서 가장 아픈 지점). 최소한 엑셀로라도 건진다.
                    if messagebox.askyesno(
                            "PDF 생성 실패",
                            f"PDF로 만들지 못했습니다.\n{pdf_error}\n\n대신 엑셀 파일로 저장할까요?",
                            parent=parent):
                        fallback_path = filedialog.asksaveasfilename(
                            parent=parent, title="엑셀로 저장할 위치 선택",
                            defaultextension=".xlsx", initialfile=os.path.basename(stem) + ".xlsx",
                            filetypes=[("Excel files", "*.xlsx")])
                        if fallback_path:
                            try:
                                shutil.copy2(xlsx_path, fallback_path)
                                saved_paths.append(fallback_path)
                            except OSError as exc:
                                messagebox.showerror(
                                    "저장 오류", f"엑셀 파일을 저장하지 못했습니다.\n{exc}", parent=parent)
                else:
                    messagebox.showwarning(
                        "PDF 생성 안내",
                        f"PDF로 만들지 못했습니다.\n{pdf_error}\n\n엑셀 파일은 정상 저장되었습니다.",
                        parent=parent)
        finally:
            if temp_dir:
                shutil.rmtree(temp_dir, ignore_errors=True)

        if not saved_paths:
            return False
        messagebox.showinfo("다운로드 완료",
                            f"{saved_count}개 항목을 저장했습니다.\n\n" + "\n".join(saved_paths),
                            parent=parent)
        return True

    def export_selected_items(self):
        selected_items = [item for item in self.data
                          if has_item_data(item) and item["no"] in self.selected_nos]
        self.export_items(selected_items,
                          default_name=f"선택견적_{datetime.now():%Y-%m-%d}.xlsx",
                          parent=self.root)

    # ---------- 업데이트 ----------

    def check_for_update(self):
        found = updater.find_new_installer(APP_VERSION)
        if not found:
            return
        name, installer_path, marker = found
        if not messagebox.askyesno(
                "업데이트 확인",
                f"update 폴더에서 새 설치 파일을 발견했습니다.\n\n"
                f"현재 버전 v{APP_VERSION}\n설치 파일 {name}\n\n"
                f"지금 실행해서 업데이트하시겠습니까?\n"
                f"(설치 중 현재 실행 중인 프로그램은 자동으로 종료 후 재시작됩니다.)"):
            updater.mark_applied(marker)
            return
        try:
            subprocess.Popen([installer_path])
            updater.mark_applied(marker)
        except OSError as exc:
            messagebox.showerror("업데이트 실행 오류", f"설치 파일을 실행할 수 없습니다.\n{exc}")
