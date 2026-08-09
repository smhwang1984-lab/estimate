"""메인 화면(카드 목록)과 전체 흐름을 붙잡고 있는 클래스."""

import os
import subprocess
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, font as tkfont, messagebox, ttk

from .. import APP_TITLE, APP_VERSION
from ..core import excel_io, paths, session, settings as settings_store, updater
from ..core.model import create_blank_item, filter_items, get_next_no, has_item_data
from ..core.pricing import calc_total_amount
from .condition_dialog import open_condition_dialog
from .popup import open_item_popup
from .settings_dialog import open_settings_dialog
from .table import (COLUMNS, build_header, build_header_underline, create_row_slot,
                    hide_row_slot, paint_checkbox, render_empty_message, update_row_slot)
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
        # v0.0.9: 단가·Material 목록·회사 정보의 주인은 설정창이다(core/settings.py).
        # 세션에는 더 이상 단가를 담지 않는다 — 담아 두면 옛 세션이 새 설정을 덮어쓴다.
        self.settings = settings_store.load()
        self.rates = self.settings["rates"]
        # v0.1.0: 현황판 열 폭(요청 3-3). 사용자가 헤더 구분선을 끌어 고친 값만 여기 담기고,
        # 그 열은 col_width_overridden에 표시돼 창 크기가 바뀌어도 폭을 지킨다. 아직 아무도
        # 안 건드린 열은 theme.json 기본값과 원래 weight 비율을 그대로 따른다.
        self.col_widths = dict(self.settings.get("col_widths", {}))
        self.col_width_overridden = set(self.col_widths.keys())
        self.header_frame = None
        self.display_page_size = self.theme.layout["page_size"]
        self.display_limit = self.display_page_size
        self.session_restored_count = 0
        self.session_saved_at = None
        self.search_after_id = None
        self.selected_nos = set()
        # 화면에 보이는 차례. 맨 앞 No 열과 Shift 범위 선택이 이 순서를 기준으로 돈다.
        self.visible_nos = []
        self.display_nos = {}
        self.anchor_no = None
        # 표 갱신 구조(v0.0.8): 행 위젯을 destroy 후 재생성하지 않고 풀로 재사용한다
        # (33행 기준 첫 그리기 약 3.9초 -> 위젯을 새로 만들지 않으면 훨씬 가벼워짐, 검색
        # 시 카드가 깜빡이던 것도 이 방식으로 같이 사라진다).
        self.row_slots = []
        self.no_to_slot = {}
        self.more_button_frame = None
        self.more_button = None
        self.empty_frame = None
        self.open_popups = {}
        self.settings_window = None
        # v0.1.1: 가공조건 산출기(Mill/Lathe). 카드 데이터를 읽기만 하고 고치지 않으므로
        # 세션·저장 경로와는 무관하다.
        self.condition_window = None

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
        #
        # v0.0.9: 세 줄의 y 좌표를 112px 안에 손으로 박아 두었더니, 배율이 높은 화면
        # (150%/200%)에서 글꼴만 커지고 좌표는 그대로라 제목과 요약줄이 서로 겹쳤다.
        # 실제 글꼴 높이를 재서 줄을 쌓고 캔버스 높이도 거기에 맞춘다.
        pad_y, gap = 12, 6
        line_heights = [tkfont.Font(font=font).metrics("linespace")
                        for font in (self.theme.header_title, self.theme.normal, self.theme.small)]
        centers, cursor = [], pad_y
        for height in line_heights:
            centers.append(cursor + height // 2)
            cursor += height + gap
        header_height = cursor - gap + pad_y

        self.header_canvas = tk.Canvas(self.root, height=header_height,
                                       highlightthickness=0, bg=c["grad_fallback"])
        self.header_canvas.pack(fill=tk.X)
        self._header_width = 0

        self.header_title_id = self.header_canvas.create_text(
            18, centers[0], anchor="w", text=APP_TITLE, fill=c["panel_fg"],
            font=self.theme.header_title)
        self.summary_var = tk.StringVar()
        self.summary_var.trace_add("write", lambda *args: self._sync_header_summary())
        self.header_summary_id = self.header_canvas.create_text(
            18, centers[1], anchor="w", text="", fill=c["panel_muted_fg"], font=self.theme.normal)
        self.header_canvas.create_text(
            18, centers[2], anchor="w",
            text="행을 클릭하면 선택, 더블클릭하면 항목 입력창이 열립니다. Ctrl/Shift로 여러 건을 고를 수 있습니다.",
            fill=c["panel_muted_fg"], font=self.theme.small)

        actions = tk.Frame(self.header_canvas, bg=c["panel_2"])
        ttk.Button(actions, text="기계 시트 업로드", command=self.upload_excel_file).pack(side=tk.LEFT, padx=4)
        ttk.Button(actions, text="새 항목 추가", command=self.add_row).pack(side=tk.LEFT, padx=4)
        ttk.Button(actions, text="설정", command=self.open_settings).pack(side=tk.LEFT, padx=4)
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
        ttk.Button(extra_actions, text="전체 선택", command=self.select_visible_items).pack(side=tk.LEFT, padx=4)
        ttk.Button(extra_actions, text="선택 해제", command=self.clear_selection).pack(side=tk.LEFT, padx=4)
        ttk.Button(extra_actions, text="선택 다운로드", command=self.export_selected_items).pack(side=tk.LEFT, padx=4)
        ttk.Button(extra_actions, text="가공조건 산출기", command=self.open_condition_dialog).pack(side=tk.LEFT, padx=4)

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

        self.header_frame = build_header(column, self)
        self.header_frame.pack(fill=tk.X)
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

    # ---------- 설정 ----------

    def open_settings(self):
        open_settings_dialog(self)

    def open_condition_dialog(self):
        """가공조건 산출기(v0.1.1). 현황판에서 1건 골라 두면 그 카드의 Material·Size를
        읽어 미리 채운다(카드는 고치지 않는다). 2건 이상 골랐으면 어느 카드인지 정할 수
        없어 열지 않는다."""
        if len(self.selected_nos) > 1:
            messagebox.showinfo("여러 건 선택됨",
                                "가공조건 산출기는 카드 1건만 반영할 수 있습니다.\n"
                                "한 건만 선택하거나 선택을 해제한 뒤 다시 눌러 주세요.")
            return
        item = None
        if self.selected_nos:
            no = next(iter(self.selected_nos))
            item = next((row for row in self.data if row["no"] == no), None)
        open_condition_dialog(self, item=item, popup=None)

    def apply_settings(self, new_settings):
        """설정창에서 저장한 값을 화면 전체에 반영한다(요청 6-1)."""
        self.settings = new_settings
        self.rates = new_settings["rates"]
        # 단가가 바뀌면 모든 카드의 금액이 달라지므로 표와 요약줄을 다시 계산한다.
        self.refresh_table(False)

    # ---------- 세션 ----------

    def save_session(self):
        search_text = self.search_var.get() if hasattr(self, "search_var") else ""
        session.save(self.data, self.selected_nos, search_text)

    def restore_session(self):
        payload = session.load()
        if not payload:
            return
        self.data = payload["items"]
        self.selected_nos = set(payload["selected_nos"])
        if hasattr(self, "search_var"):
            self.search_var.set(payload["search"])
        self.session_restored_count = len(self.data)
        self.session_saved_at = payload["saved_at"]

    # ---------- 목록 갱신 ----------

    def get_search_text(self):
        return self.search_var.get().strip() if hasattr(self, "search_var") else ""

    def get_display_no(self, no):
        """현황판에 보이는 순번. 아직 목록에 없으면 None.

        갓 만든 빈 카드는 내용이 없어 목록에 잡히지 않고(`has_item_data`), 검색으로 걸러진
        카드도 마찬가지다. 그때 내부 번호를 대신 보여 주면 화면에는 1~40이 떠 있는데
        입력창 제목만 'NO. 41'로 뜨는 어긋남이 생긴다. 번호가 없다는 사실을 그대로 알린다.
        """
        return self.display_nos.get(no)

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

        # 화면 순번은 여기서 한 번만 정하고, 팝업 제목·정보 타일도 이 값을 쓴다(요청 1-3, 4-5).
        self.visible_nos = [item["no"] for item in shown]
        self.display_nos = {no: index + 1 for index, no in enumerate(self.visible_nos)}

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
        self.visible_nos = []
        self.display_nos = {}
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
        bg = self.row_normal_bg(slot)
        slot["frame"].configure(bg=bg)
        for widget in slot["tinted"]:
            widget.configure(bg=bg)
        paint_checkbox(self, slot, no in self.selected_nos)

    # ---------- 검색 / 선택 ----------

    def clear_search(self):
        self.search_var.set("")
        self.refresh_table(True)

    def set_selection(self, new_selection):
        """선택 집합을 통째로 바꾸되, 실제로 달라진 행만 다시 칠한다."""
        new_selection = set(new_selection)
        changed = self.selected_nos.symmetric_difference(new_selection)
        self.selected_nos = new_selection
        for no in changed:
            self.update_row_visual(no)
        self.update_summary_text()

    def handle_row_click(self, no, mode="plain"):
        """윈도우 탐색기와 같은 선택 규칙(요청 2-1).

            plain    이 행만 선택하고 나머지는 해제한다.
            toggle   Ctrl+클릭. 이 행만 켜거나 끈다.
            range    Shift+클릭. 마지막 기준 행부터 이 행까지 한 번에 고른다.

        범위는 `self.data`의 저장 순서가 아니라 지금 화면에 보이는 순서를 기준으로 잡는다
        (검색·정렬·더보기 상태에 따라 화면 순서가 달라지기 때문).
        """
        if mode == "range" and self.anchor_no in self.visible_nos and no in self.visible_nos:
            start = self.visible_nos.index(self.anchor_no)
            end = self.visible_nos.index(no)
            if start > end:
                start, end = end, start
            self.set_selection(self.visible_nos[start:end + 1])
            return  # 기준 행은 그대로 둬야 범위를 계속 늘렸다 줄였다 할 수 있다.
        if mode == "toggle":
            if no in self.selected_nos:
                self.set_selection(self.selected_nos - {no})
            else:
                self.set_selection(self.selected_nos | {no})
        else:
            self.set_selection({no})
        self.anchor_no = no

    def toggle_item_selection(self, no):
        """체크박스를 눌렀을 때. 체크박스는 언제나 그 행 하나만 켜고 끈다."""
        self.handle_row_click(no, "toggle")

    def select_visible_items(self):
        _, visible_items = filter_items(self.data, self.get_search_text())
        self.set_selection(self.selected_nos | {item["no"] for item in visible_items})

    def clear_selection(self):
        self.set_selection(set())
        self.anchor_no = None

    # ---------- 카드 추가 / 팝업 ----------

    def add_row(self):
        new_no = get_next_no(self.data)
        self.data.append(create_blank_item(new_no))
        self.refresh_table(True)
        self.open_popup(new_no)

    def open_popup(self, no):
        open_item_popup(self, no)

    def open_next_item(self, no):
        """'저장 후 다음 항목 입력' — 언제나 새 빈 카드를 연다.

        예전에는 `no + 1`번 카드가 이미 있으면 그 카드를 열었다. 연속 입력 중에 남의 카드가
        열려 덮어쓰게 되는 동작인데, v0.0.9에서 현황판에 순번이 보이게 되면서 눈에 띄게 됐다.
        비어 있는 번호를 새로 발급해 항상 새 카드로 이어 간다.
        """
        next_no = no + 1
        if any(row["no"] == next_no for row in self.data):
            next_no = get_next_no(self.data)
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
            item["save_pending"] = True
            self.data.append(item)
        self.save_session()
        self.refresh_table(True)
        messagebox.showinfo("업로드 완료",
                            f"{len(cards)}개 항목을 카드로 불러왔습니다.\n"
                            f"방금 올린 항목이 목록 맨 위에 쌓입니다.")

    def export_items(self, items, default_name=None, parent=None):
        """고른 항목을 엑셀 견적 파일로 내려받는다(v0.0.9: PDF 출력은 없앴다, 요청 3-1)."""
        if not items:
            messagebox.showwarning("다운로드 대상 없음", "다운로드할 항목을 먼저 선택하거나 입력하세요.", parent=parent)
            return False
        parent = parent or self.root

        base_name = os.path.splitext(default_name or f"선택견적_{datetime.now():%Y-%m-%d}.xlsx")[0]
        chosen_path = filedialog.asksaveasfilename(
            parent=parent,
            title="다운로드 저장 위치 선택",
            defaultextension=".xlsx",
            initialfile=base_name + ".xlsx",
            filetypes=[("Excel files", "*.xlsx")])
        if not chosen_path:
            return False

        try:
            saved_count = excel_io.export_items(items, self.rates, chosen_path, self.settings)
        except excel_io.TemplateNotFound as exc:
            messagebox.showerror("파일 오류", f"'{exc}' 파일이 존재하지 않습니다.", parent=parent)
            return False
        except excel_io.SheetNotFound as exc:
            messagebox.showerror("시트 오류", f"'{exc}' 시트를 찾을 수 없습니다.", parent=parent)
            return False
        except OSError as exc:
            messagebox.showerror("저장 오류", f"파일을 저장하지 못했습니다.\n{exc}", parent=parent)
            return False

        # v0.0.9: 날짜별 누적 저장을 없애면서 저장 완료 표시를 여기로 옮겼다.
        # 안 그러면 NEW 배지를 지워 줄 곳이 없어 모든 카드에 영원히 붙어 있게 된다.
        for item in items:
            item["save_pending"] = False
        self.save_session()
        self.refresh_table(False)
        messagebox.showinfo("다운로드 완료",
                            f"{saved_count}개 항목을 저장했습니다.\n\n{chosen_path}",
                            parent=parent)
        return True

    def export_selected_items(self):
        # 화면에 보이는 차례 그대로 엑셀에 담는다(맨 위 카드가 엑셀에서도 첫 줄).
        _, visible_items = filter_items(self.data, self.get_search_text())
        selected_items = [item for item in visible_items
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
