"""메인 화면(카드 목록)과 전체 흐름을 붙잡고 있는 클래스."""

import os
import queue
import subprocess
import threading
import tkinter as tk
from copy import deepcopy
from datetime import datetime
from tkinter import filedialog, font as tkfont, messagebox, ttk

from .. import APP_TITLE, APP_VERSION
from ..core import (datastore, display_prefs as display_prefs_store, editlock, excel_io, library, paths, remote,
                    session, settings as settings_store, updater)
from ..core.model import (create_blank_item, filter_items, find_duplicate_part_nos,
                          has_item_data, normalize_part_no)
from ..core.pricing import calc_total_amount
from .condition_dialog import open_condition_dialog
from .library_dialog import open_library_dialog, save_single_card
from .new_items_dialog import open_new_items_dialog
from .password_dialog import unlock as unlock_edit
from .restore_dialog import open_restore_dialog
from .popup import open_item_popup
from .settings_dialog import open_settings_dialog
from .sync import SyncManager
from .table import GridTable, fit_font_text
from .theme import Theme


def _download_file_name(items):
    """다운로드 기본 파일명. v0.1.9 요청: `선택견적_날짜` 대신 대표 품번이 드러나야 한다.

    대표는 맨 위(첫) 항목의 품번이다 -- export_selected_items가 화면에 보이는 차례
    그대로 담으므로, 맨 위 카드가 엑셀에서도 첫 줄이자 사용자가 고른 것 중 가장 먼저
    눈에 띄는 항목이다. 품번이 비어 있으면 품명, 둘 다 없으면 "미입력"으로 대신한다.
    나머지 건수는 "…외 n건"(대표를 뺀 수)으로 붙인다 -- 1건이면 "외 0건" 대신 아예 뺀다.
    """
    lead = items[0] if items else {}
    label = str(lead.get("part_no") or lead.get("part_name") or "미입력").strip() or "미입력"
    label = library.sanitize_title(label) or "미입력"
    rest = len(items) - 1
    suffix = f"{label}외 {rest}건" if rest > 0 else label
    return f"견적_{datetime.now():%Y-%m-%d}({suffix}).xlsx"


class EstimateApp:
    def __init__(self, root):
        self.root = root
        # v0.1.8: 다크/라이트·표 구분선·글자 배율은 이 PC에만 저장하는 별도 파일이다
        # (settings.json은 공유 폴더로 옮길 수 있어 화면 취향까지 같이 담으면 안 된다).
        self.display_prefs = display_prefs_store.load()
        self.theme = Theme(self.display_prefs["theme_mode"], self.display_prefs["font_scale"])
        self.root.title(f"{APP_TITLE} v{APP_VERSION}")
        self.root.geometry(self.theme.layout["window_size"])
        self.root.minsize(self.theme.layout["min_width"], self.theme.layout["min_height"])
        self._apply_window_icon()

        self.data = []
        self.new_items = []
        self.data_state = None
        self.settings_loading = False
        self.settings_load_queue = queue.Queue()
        self.settings_load_error = None
        self.export_in_progress = False
        # v0.0.9: 단가·Material 목록·회사 정보의 주인은 설정창이다(core/settings.py).
        # 세션에는 더 이상 단가를 담지 않는다 — 담아 두면 옛 세션이 새 설정을 덮어쓴다.
        location = datastore.load_location()
        if location["enabled"]:
            # 공유 폴더 판정은 느릴 수 있다. 화면은 기본값으로 먼저 만들고 실제 설정은
            # 백그라운드에서 읽어, 끊긴 SMB 경로 때문에 첫 화면이 멈추지 않게 한다.
            self.settings = settings_store.defaults()
            self.data_state = {"dir": location["path"], "shared": True,
                               "server": remote.is_server_url(location["path"]),
                               "ok": False, "reason": datastore.REASON_UNREACHABLE}
            self.settings_loading = True
        else:
            self.settings = settings_store.load()
            self.data_state = datastore.get_state()
        self.rates = self.settings["rates"]
        # v0.1.0: 현황판 열 폭(요청 3-3). 사용자가 헤더 구분선을 끌어 고친 값만 여기 담기고,
        # 그 열은 col_width_overridden에 표시돼 창 크기가 바뀌어도 폭을 지킨다. 아직 아무도
        # 안 건드린 열은 theme.json 기본값과 원래 weight 비율을 그대로 따른다.
        self.col_widths = dict(self.settings.get("col_widths", {}))
        self.col_width_overridden = set(self.col_widths.keys())
        self.session_restored_count = 0
        self.session_saved_at = None
        self.search_after_id = None
        self.selected_nos = set()
        # 화면에 보이는 차례. 맨 앞 No 열과 Shift 범위 선택이 이 순서를 기준으로 돈다.
        self.visible_nos = []
        self.display_nos = {}
        self.anchor_no = None
        # v1.5.0: 표는 Canvas 하나에 보이는 행만 그리는 GridTable이다(ui/table.py).
        self.table = None
        self.open_popups = {}
        self.settings_window = None
        # v0.1.4: 견적 보관함(core/library.py). 방금 불러오거나 저장한 견적이 무엇인지
        # 기억해 둔다 -- 저장할 때 "내가 불러온 뒤 남이 고쳤는지"를 mtime으로 판단하는 데 쓴다.
        self.library_window = None
        self.new_items_window = None
        self.library_current = None
        # v0.1.1: 가공조건 산출기(Mill/Lathe). 카드 데이터를 읽기만 하고 고치지 않으므로
        # 세션·저장 경로와는 무관하다.
        self.condition_window = None
        # v0.1.2: 삭제 되돌리기. 메모리에만 둔다(세션 파일에는 안 남긴다) -- 프로그램을
        # 껐다 켜면 되돌릴 수 없다. 단일 단계만 기억한다(스택 아님).
        self.last_deleted = []
        self.row_context_menu = None
        self.context_menu_no = None
        # v0.1.3: 품번이 겹치는 카드의 품번 집합(정규화 표기). refresh_table에서 다시 계산해
        # 두고, 표가 행을 그릴 때 참조한다 -- 행마다 목록 전체를 훑지 않기 위해서다.
        self.duplicate_part_nos = set()
        # v1.4.0: 견적 서버 실시간 동기화(ui/sync.py)와 그 알림 줄. 알림 줄은 화면을 다시 지어도
        # (다크/라이트 전환) 떠 있던 내용을 되살릴 수 있게 내용을 따로 들고 있는다.
        self.sync = SyncManager(self)
        # v1.5.0: 알림은 화면 맨 아래 고정 높이 줄(strip)에 그린다. 줄이 생겼다 사라지지 않으므로 알림이
        # 뜨고 질 때 표가 밀리지 않는다. notice_spec은 임시 알림, sync_status는 평소에 보이는
        # 자동 저장 상태다(둘 다 없으면 기본 안내).
        self.strip = None
        self.notice_spec = None
        self.notice_hide_id = None
        self.sync_status = None

        self.theme.apply(self.root)
        self.maximize_window()
        self.build_dashboard()
        self.restore_session()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        # ESC로 선택 취소(요청: "선택 체크박스 후 esc누르면 선택 취소"). 팝업은 별도
        # Toplevel이라 여기서 건 바인딩과 서로 간섭하지 않는다(포커스가 팝업에 있으면
        # 팝업의 <Escape> 바인딩만 반응한다).
        self.root.bind("<Escape>", lambda event: self.clear_selection())
        # v0.1.2: 삭제 되돌리기. app.root에만 건다(bind_all 아님) -- 카드 팝업·설정창·
        # 산출기 같은 다른 Toplevel에 포커스가 있을 때(텍스트 편집 중일 수 있다)는
        # Ctrl+Z가 여기로 안 온다.
        self.root.bind("<Control-z>", lambda event: self.undo_delete())
        # v0.1.8: 표 글자 크기 배율 단축키(요청). Ctrl+=/-는 Shift 여부와 무관하게 같은
        # keysym("plus"/"minus")으로 들어오는 배열이 많아 두 조합을 함께 걸어 둔다.
        for seq in ("<Control-plus>", "<Control-equal>", "<Control-KP_Add>"):
            self.root.bind(seq, lambda event: self._nudge_font_scale(display_prefs_store.FONT_SCALE_STEP))
        for seq in ("<Control-minus>", "<Control-KP_Subtract>"):
            self.root.bind(seq, lambda event: self._nudge_font_scale(-display_prefs_store.FONT_SCALE_STEP))
        self.root.bind("<Control-0>", lambda event: self.apply_font_scale(display_prefs_store.DEFAULT_FONT_SCALE))
        # 저장된 항목이 많으면 표를 다 그리는 데 몇 초가 걸린다. 그 동안 아무것도 안 뜬 것처럼
        # 보이지 않도록 창을 먼저 띄우고, 목록은 곧바로 이어서 채운다.
        self.summary_var.set("목록을 불러오는 중입니다...")
        if self.settings_loading:
            self._start_settings_load()
        else:
            # v0.1.4: 공유 폴더 경고를 업데이트 확인보다 먼저 띄운다(설정이 기본값으로 보이는
            # 이유를 먼저 알려야 사용자가 값을 다시 입력하는 헛수고를 안 한다).
            self.root.after(400, self.check_data_location)
        self.root.after_idle(lambda: self.refresh_table(True))
        self.root.after(800, self.check_for_update)
        self.root.after(600, self.sync.start)

    # ---------- 창 기본 동작 ----------

    def _ask_close_without_save(self, heading, reason, title):
        """자동 저장을 못 했을 때 종료할지 묻는다(v1.3.0). '예'면 True.

        v1.2.0은 여기서 무조건 종료를 취소했다. 서버(NAS)가 재부팅 중이면 저장이 계속 실패해
        작업 관리자로만 끌 수 있었다. 작업 중인 카드는 이어서 save_session()이 이 PC에 남기므로
        저장하지 않고 꺼도 다음 실행 때 그대로 열린다 — 보관함에 반영되지 않을 뿐이다.
        기본 선택은 '아니요'(종료 취소)로 둬서 습관적으로 Enter를 눌러도 기존처럼 멈춘다.
        """
        return messagebox.askyesno(
            heading,
            f"{reason}\n\n"
            f"보관함에 저장하지 않고 종료할까요?\n"
            f"작업 중인 카드는 이 PC에 남아 다음 실행 때 그대로 열립니다."
            f" 보관함의 '{title}'에는 반영되지 않습니다.\n\n"
            f"[아니요]를 누르면 종료를 취소합니다.",
            icon="warning", default="no", parent=self.root)

    def _autosave_current_library(self):
        """마지막 보관함 파일만 종료 직전에 원자적으로 덮어쓴다.

        True면 종료를 계속한다(저장 성공, 또는 실패했지만 사용자가 그래도 종료를 골랐다).
        """
        current = self.library_current
        if not current:
            return True
        if not self.can_edit():
            return True   # v1.7.0: 읽기 전용 PC는 서버에 쓰지 않는다(쓰면 암호 없이 덮어쓰는 셈이다)
        title = str(current.get("title") or "").strip()
        path = str(current.get("path") or "").strip()
        if not title or not path:
            return self._ask_close_without_save(
                "자동 저장 오류", "마지막 견적의 저장 위치를 확인할 수 없습니다.", title or "마지막 견적")
        existing_mtime = library.get_mtime(path)
        if library.is_changed_by_other(current, path, existing_mtime):
            stamp = datetime.fromtimestamp(existing_mtime).strftime("%Y-%m-%d %H:%M:%S")
            return self._ask_close_without_save(
                "자동 저장 중단",
                f"'{title}'이 다른 곳에서 저장됐습니다 ({stamp}).\n"
                "덮어쓰지 않도록 자동 저장을 멈췄습니다. 내용을 확인한 뒤 보관함에서 직접 저장해 주세요.",
                title)
        result = library.save_entry(title, self.data, path=path)
        if result is None:
            detail = f"\n{datastore.describe()}" if library.is_server_path(path) else f"\n{path}"
            if library.get_last_error() == remote.REASON_CONFLICT:
                detail = ("\n그 사이 다른 PC가 같은 견적을 서버에 저장했습니다."
                          " 보관함에서 내용을 확인한 뒤 직접 저장해 주세요.")
            return self._ask_close_without_save(
                "자동 저장 오류", f"견적을 보관함에 저장하지 못했습니다.{detail}", title)
        self.set_library_current({"title": title, "path": result["path"], "mtime": result["mtime"]})
        return True

    def on_close(self):
        if not self._autosave_current_library():
            return
        if self.sync.stop_event is not None:
            self.sync.stop_event.set()
        self.save_column_settings()
        self.save_session(sync=False)
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
        """v1.5.0: 윈도우 프로그램·엑셀 같은 배치. 도구 모음 → 검색줄 → 표 → 동기화 줄 → 상태 표시줄.

        v0.1.8의 규칙은 그대로다: 다크/라이트 전환은 이 컨테이너 하나만 지우고 다시 짓는다
        (설정창·팝업 같은 Toplevel은 root의 자식이라 root를 비우면 같이 닫힌다 — _rebuild_dashboard_ui).
        """
        c = self.theme.colors
        self.root.configure(bg=c["bg"])
        self.main_container = tk.Frame(self.root, bg=c["bg"])
        self.main_container.pack(fill=tk.BOTH, expand=True)

        self._build_toolbar()
        self._build_search_bar()
        self._build_bottom_bars()
        self.table = GridTable(self.main_container, self)
        self.table.frame.pack(fill=tk.BOTH, expand=True)
        self._paint_strip()

    def _tool_button(self, parent, text, command, style="Tool.TButton", padx=1):
        button = ttk.Button(parent, text=text, command=command, style=style)
        button.pack(side=tk.LEFT, padx=padx)
        return button

    def _tool_separator(self, parent):
        tk.Frame(parent, bg=self.theme.colors["line"], width=1).pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=3)

    def _build_toolbar(self):
        """기능은 그대로, 단추만 묶음별로 모았다: 보관함·내려받기 | 선택 | 삭제 | 도구 …… 보기·설정."""
        c = self.theme.colors
        bar = tk.Frame(self.main_container, bg=c["panel"], padx=8, pady=5)
        bar.pack(fill=tk.X)
        left = tk.Frame(bar, bg=c["panel"])
        left.pack(side=tk.LEFT)
        self._tool_button(left, "견적 불러오기", lambda: self.open_library("load"))
        self._tool_button(left, "견적 저장", lambda: self.open_library("save"), "ToolPrimary.TButton")
        self._tool_button(left, "선택 다운로드", self.export_selected_items)
        self._tool_separator(left)
        self._tool_button(left, "신규품목", self.open_new_items)
        self._tool_button(left, "전체 선택", self.select_visible_items)
        self._tool_button(left, "선택 해제", self.clear_selection)
        self._tool_separator(left)
        # v0.1.2: 되돌릴 수 없는 동작이라 다른 단추와 선으로 떼어 둔다(오클릭 방지).
        # v0.1.3: "삭제 취소" 단추는 없앴다 — Ctrl+Z와 삭제 확인창 안내가 그 자리를 대신한다.
        self._tool_button(left, "선택 삭제", self.delete_selected_items, "ToolDanger.TButton")
        self._tool_separator(left)
        self._tool_button(left, "가공조건 산출기", self.open_condition_dialog)
        self._tool_separator(left)
        self._tool_button(left, "데이터 백업", self.backup_now)
        self._tool_button(left, "백업에서 복원", self.restore_backup)
        right = tk.Frame(bar, bg=c["panel"])
        right.pack(side=tk.RIGHT)
        # v1.7.0: 서버에 편집 암호가 걸려 있을 때만 보이는 잠금 단추(읽기 전용 / 편집 가능).
        self.edit_slot = tk.Frame(right, bg=c["panel"])
        self.edit_slot.pack(side=tk.LEFT)
        self._paint_edit_button()
        theme_label = "☀ 라이트 모드" if self.theme.mode == "light" else "🌙 다크 모드"
        self._tool_button(right, theme_label, self.toggle_theme_mode)
        self._tool_button(right, "설정", self.open_settings)
        tk.Frame(self.main_container, bg=c["line"], height=1).pack(fill=tk.X)

    def _build_search_bar(self):
        c = self.theme.colors
        bar = tk.Frame(self.main_container, bg=c["bg"], padx=10, pady=6)
        bar.pack(fill=tk.X)
        tk.Label(bar, text="검색", bg=c["bg"], fg=c["text"], font=self.theme.bold).pack(side=tk.LEFT, padx=(0, 8))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.schedule_refresh())
        ttk.Entry(bar, textvariable=self.search_var, width=34).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(bar, text="초기화", command=self.clear_search, style="Tool.TButton").pack(side=tk.LEFT)
        tk.Label(bar, text="품번/품명/기종 대상 · 공백/쉼표로 여러 조건", bg=c["bg"], fg=c["muted"],
                 font=self.theme.small_plain).pack(side=tk.LEFT, padx=(12, 0))
        tk.Label(bar, text="클릭: 선택  ·  더블클릭: 입력창  ·  Ctrl/Shift: 여러 건  ·  Ctrl+Z: 삭제 되돌리기",
                 bg=c["bg"], fg=c["muted"], font=self.theme.small_plain).pack(side=tk.RIGHT)
        tk.Frame(self.main_container, bg=c["line"], height=1).pack(fill=tk.X)

    def _build_bottom_bars(self):
        """맨 아래 두 줄. 아래부터 [상태 표시줄: 건수·위치] / [동기화 줄: 자동 저장 상태·알림].
        둘 다 높이가 고정이라 내용이 바뀌어도 표가 움직이지 않는다."""
        c = self.theme.colors
        status = tk.Frame(self.main_container, bg=c["panel_2"])
        status.pack(side=tk.BOTTOM, fill=tk.X)
        self.summary_var = tk.StringVar()
        self.location_var = tk.StringVar()
        tk.Label(status, textvariable=self.summary_var, bg=c["panel_2"], fg=c["text"], anchor="w",
                 padx=10, pady=3, font=self.theme.small_plain).pack(side=tk.LEFT)
        tk.Label(status, textvariable=self.location_var, bg=c["panel_2"], fg=c["muted"], anchor="e",
                 padx=10, pady=3, font=self.theme.small_plain).pack(side=tk.RIGHT)
        tk.Frame(self.main_container, bg=c["line"], height=1).pack(side=tk.BOTTOM, fill=tk.X)
        strip = tk.Frame(self.main_container, bg=c["panel"], height=32)
        strip.pack(side=tk.BOTTOM, fill=tk.X)
        strip.pack_propagate(False)
        self.strip = strip
        self.strip_font = tkfont.Font(font=self.theme.small_plain)
        self.strip_buttons = tk.Frame(strip, bg=c["panel"])
        self.strip_buttons.pack(side=tk.RIGHT, padx=6)
        self.strip_label = tk.Label(strip, anchor="w", padx=12, font=self.theme.small_plain)
        self.strip_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.strip_text = ""
        strip.bind("<Configure>", lambda e: self._fit_strip_text())
        tk.Frame(self.main_container, bg=c["line"], height=1).pack(side=tk.BOTTOM, fill=tk.X)

    # ---------- 화면 표시(v0.1.8: 다크/라이트, 구분선, 글자 배율) ----------

    def toggle_theme_mode(self):
        other = "dark" if self.theme.mode == "light" else "light"
        self.apply_theme_mode(other)

    def _guard_open_popups(self):
        """입력창이 열려 있으면 화면을 통째로 다시 짓지 않는다(견적 불러오기와 같은 이유:
        popup.py의 save_and_close()가 붙잡아 둔 카드를 편집 중일 수 있다)."""
        if self.open_popups:
            messagebox.showwarning(
                "전환할 수 없음",
                f"항목 입력창 {len(self.open_popups)}개가 열려 있습니다.\n"
                f"입력창을 모두 닫은 뒤 다시 시도해 주세요.")
            return False
        return True

    def _rebuild_dashboard_ui(self):
        """본문(main_container) 하나만 지웠다 새로 짓는다 -- root를 통째로 비우면 설정창·
        입력창 같은 별도 Toplevel까지 같이 닫힌다(Toplevel도 root의 자식이라 winfo_children
        대상에 걸린다). 다크/라이트 전환과 표 글자 배율 변경이 함께 쓴다 -- 둘 다 위젯에
        이미 박힌 색·글꼴을 바꾸는 거라 다시 짓는 것 말고는 반영할 방법이 없다.
        """
        search_text = self.get_search_text()
        selection = set(self.selected_nos)
        self.main_container.destroy()
        self.table = None
        self.strip = None

        self.theme.apply(self.root)
        self.build_dashboard()
        if search_text:
            self.search_var.set(search_text)
        self.selected_nos = selection
        self.refresh_table(True)

    def apply_theme_mode(self, mode):
        """다크/라이트를 바꾸고 화면을 즉시 다시 그린다."""
        if mode == self.theme.mode or not self._guard_open_popups() or not self.theme.reload(mode):
            return
        self.display_prefs["theme_mode"] = mode
        display_prefs_store.save(self.display_prefs)
        self._rebuild_dashboard_ui()

    def apply_font_scale(self, font_scale):
        """표 글자 크기 배율(70~150%)을 바꾸고 화면을 즉시 다시 그린다."""
        font_scale = display_prefs_store.clamp_font_scale(font_scale)
        if not self._guard_open_popups() or not self.theme.set_font_scale(font_scale):
            return
        self.display_prefs["font_scale"] = font_scale
        display_prefs_store.save(self.display_prefs)
        self._rebuild_dashboard_ui()

    def _nudge_font_scale(self, delta):
        self.apply_font_scale(self.theme.font_scale + delta)

    def apply_divider_pref(self, enabled):
        """열 구분선 on/off. 슬롯 색만 바꾸면 되므로 화면을 다시 짓지 않는다."""
        enabled = bool(enabled)
        if enabled == self.display_prefs.get("dividers", True):
            return
        self.display_prefs["dividers"] = enabled
        display_prefs_store.save(self.display_prefs)
        if self.table is not None:
            self.table.redraw_body()

    # ---------- 설정 ----------

    def open_settings(self):
        if self.settings_loading:
            messagebox.showinfo("설정 확인 중", "공유 설정을 불러오는 중입니다. 잠시 뒤 다시 열어 주세요.")
            return
        # v1.4.0(A): 설정창은 켤 때 읽어 둔 값이 아니라 서버의 지금 값으로 연다. 낡은 값으로 열면
        # 회사명 하나만 고쳐 저장해도 다른 PC가 바꾼 단가가 옛 값으로 되돌아간다.
        if datastore.location_is_server() and self.sync.connected is not False:
            self.root.configure(cursor="watch")
            self.root.update_idletasks()
            try:
                fresh = settings_store.load()
            finally:
                self.root.configure(cursor="")
            if not settings_store.get_load_error():
                self.settings_load_error = None
                self.apply_settings(fresh)
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

    # ---------- 견적 보관함 (v0.1.4) ----------

    def open_library(self, mode):
        # v1.7.0: 저장카드는 하나 -- 저장은 창 없이 바로, 불러오기만 목록 창을 연다.
        if mode == "save":
            save_single_card(self)
        else:
            open_library_dialog(self, mode)

    # ---------- 편집 권한 (v1.7.0) ----------

    def can_edit(self):
        """수정·입력을 해도 되는가. 로컬 모드나 암호가 없는 서버는 항상 True, 암호가 걸린 서버는
        암호를 입력한 PC만 True. 화면의 모든 수정·저장·삭제 입구가 이 값을 먼저 본다."""
        return (not datastore.location_is_server()) or editlock.can_edit()

    def require_edit(self, action="이 작업", parent=None):
        """수정 입구에서 부른다. 읽기 전용이면 안내하고 암호를 물어, 편집 권한을 얻었을 때만 True."""
        if self.can_edit():
            return True
        parent = parent or self.root
        if messagebox.askyesno(
                "읽기 전용",
                f"{action}은(는) 편집 암호를 입력한 PC에서만 할 수 있습니다.\n\n"
                f"지금 편집 암호를 입력할까요?", parent=parent):
            return unlock_edit(self, parent) and self.can_edit()
        return False

    def toggle_edit_lock(self):
        if not self.can_edit():
            unlock_edit(self)
            return
        if self.library_dirty() and not messagebox.askyesno(
                "편집 잠그기",
                "아직 서버에 저장되지 않은 변경이 있습니다.\n잠그면 이 변경은 서버에 올라가지 않습니다. 잠글까요?",
                default="no"):
            return
        editlock.clear_token()
        self.update_edit_ui()
        self.show_notice("🔒 읽기 전용으로 전환했습니다.", "info", auto_hide=True)

    def _paint_edit_button(self):
        slot = getattr(self, "edit_slot", None)
        if slot is None or not slot.winfo_exists():
            return
        for child in slot.winfo_children():
            child.destroy()
        if not (datastore.location_is_server() and editlock.is_protected()):
            return
        if self.can_edit():
            text, style = "🔓 편집 가능 (잠그기)", "Tool.TButton"
        else:
            text, style = "🔒 읽기 전용 (암호 입력)", "ToolPrimary.TButton"
        ttk.Button(slot, text=text, command=self.toggle_edit_lock, style=style).pack(side=tk.LEFT, padx=1)

    def update_edit_ui(self):
        """권한 상태가 바뀌었을 때(암호 입력·잠금·다른 PC의 암호 변경) 단추와 상태 표시줄을 갱신한다."""
        self._paint_edit_button()
        self.update_summary_text()

    # ---------- 데이터 백업 (v1.7.0) ----------

    def backup_now(self):
        """[데이터 백업] 단추. 서버에 백업 파일을 만들고 결과를 동기화 줄에 알린다."""
        if getattr(self, "backup_running", False):
            return
        if not self.require_edit("데이터 백업"):
            return
        if not datastore.location_is_server():
            messagebox.showinfo(
                "서버 연결 필요",
                "데이터 백업은 견적 서버에 연결했을 때 쓸 수 있습니다.\n\n"
                "[설정 > 데이터 위치]에서 서버 주소를 지정해 주세요.", parent=self.root)
            return
        self.backup_running = True
        self.show_notice("데이터 백업 만드는 중…", "info")
        base = datastore.get_data_dir()
        box = []

        def work():
            box.append(remote.create_backup(base))

        threading.Thread(target=work, daemon=True, name="estimate-backup").start()
        self.root.after(150, lambda: self._finish_backup(box))

    def restore_backup(self):
        """[백업에서 복원] 단추. 서버의 백업 목록에서 시점을 골라 서버 데이터를 되돌린다(v1.8.0)."""
        open_restore_dialog(self)

    def _finish_backup(self, box):
        if not box:
            self.root.after(150, lambda: self._finish_backup(box))
            return
        self.backup_running = False
        info, error = box[0]
        if error is None:
            kb = max(1, int(info.get("size", 0)) // 1024)
            self.show_notice(f"✓ 백업 완료 {str(info.get('created_at', ''))[11:19]} — "
                             f"{info['name']} ({kb:,}KB, 서버 backup 폴더)", "success", auto_hide=True)
        elif error == remote.REASON_MISSING:
            self.show_notice("백업 실패 — 서버 버전이 낮습니다. 서버를 1.2.0 이상으로 올려 주세요.", "danger", auto_hide=True)
        else:
            self.show_notice("백업 실패 — 서버에 연결하지 못했거나 서버가 백업을 만들지 못했습니다.", "danger", auto_hide=True)

    # ---------- 동기화 알림 줄 / 보관함 참조 (v1.4.0) ----------

    def show_notice(self, text, level="info", actions=None, auto_hide=False):
        """동기화 줄에 임시 알림을 띄운다. level: success / warn / danger / info.

        메시지 상자 대신 쓰는 이유: 동기화 알림은 다른 PC 때문에 아무 때나 생긴다. 그때마다
        창을 띄우면 입력 중인 사람의 손을 멈춘다. auto_hide면 몇 초 뒤 사라지고, 사라지면 평소
        자동 저장 상태(set_sync_status)가 다시 보인다. v1.5.0부터는 줄을 끼워 넣지 않고 고정된
        줄의 내용만 바꾼다 — 알림이 뜨고 질 때 표가 밀려 다시 그려지던 끊김이 없다.
        """
        self.hide_notice(repaint=False)
        self.notice_spec = {"text": text, "level": level, "actions": actions, "auto_hide": auto_hide}
        self._paint_strip()
        if auto_hide:
            self.notice_hide_id = self.root.after(8000, self.hide_notice)

    def hide_notice(self, repaint=True):
        if self.notice_hide_id is not None:
            try:
                self.root.after_cancel(self.notice_hide_id)
            except tk.TclError:
                pass
            self.notice_hide_id = None
        self.notice_spec = None
        if repaint:
            self._paint_strip()

    def set_sync_status(self, text, level="idle"):
        """평소에 동기화 줄에 보이는 자동 저장 상태. 임시 알림이 떠 있으면 그것이 우선이다."""
        self.sync_status = {"text": text, "level": level} if text else None
        if self.notice_spec is None:
            self._paint_strip()

    def _default_sync_status(self):
        if datastore.location_is_server():
            if self.library_current:
                return {"text": "✓ 서버와 동기화됨 — 고치면 바로 자동 저장됩니다", "level": "idle"}
            return {"text": "견적 보관함에 한 번 저장하면 그때부터 서버와 자동 동기화됩니다", "level": "idle"}
        return {"text": "작업 중인 카드는 이 PC에 자동으로 보관됩니다", "level": "idle"}

    def _strip_colors(self, level):
        c = self.theme.colors
        return {
            "success": (c["success_bg"], c["success_fg"]),
            "warn": (c["warn_bg"], c["warn_fg"]),
            "danger": (c["danger_bg"], c["danger_fg"]),
            "info": (c["panel_2"], c["text"]),
        }.get(level, (c["panel"], c["muted"]))

    def _paint_strip(self):
        if self.strip is None:
            return
        notice = self.notice_spec
        spec = notice or self.sync_status or self._default_sync_status()
        bg, fg = self._strip_colors(spec["level"])
        try:
            self.strip.configure(bg=bg)
            self.strip_buttons.configure(bg=bg)
            self.strip_label.configure(bg=bg, fg=fg)
            for widget in self.strip_buttons.winfo_children():
                widget.destroy()
            if notice:
                ttk.Button(self.strip_buttons, text="닫기", style="Strip.TButton",
                           command=self.hide_notice).pack(side=tk.RIGHT, padx=(6, 0))
                for label, command in reversed(notice.get("actions") or []):
                    ttk.Button(self.strip_buttons, text=label, style="Strip.TButton",
                               command=command).pack(side=tk.RIGHT, padx=(6, 0))
            self.strip_text = spec["text"]
            self.strip.update_idletasks()
            self._fit_strip_text()
        except tk.TclError:
            pass

    def _fit_strip_text(self):
        if self.strip is None:
            return
        try:
            room = self.strip.winfo_width() - self.strip_buttons.winfo_reqwidth() - 40
            self.strip_label.configure(text=fit_font_text(self.strip_font, self.strip_text, max(120, room)))
        except tk.TclError:
            pass

    def set_library_current(self, entry):
        """화면이 지금 어느 보관함 견적인지 기억한다. 내용 지문(sig)을 같이 남겨, 그 뒤에
        카드를 고쳤는지(library_dirty)를 알 수 있게 한다. None이면 연결을 끊는다."""
        if not entry:
            self.library_current = None
            self.sync.reset_baseline()
            return
        entry = dict(entry)
        entry["sig"] = library.content_signature(self.data)
        self.library_current = entry
        self.sync.reset_baseline()

    def library_dirty(self):
        """불러오거나 저장한 뒤 카드를 고쳐서 아직 보관함에 반영 안 된 변경이 있는가."""
        current = self.library_current
        if not current:
            return False
        return library.content_signature(self.data) != current.get("sig")

    def apply_library_entry(self, payload, path, quiet=False):
        """보관함에서 불러온 견적으로 현재 카드 목록을 통째로 바꾼다. 성공하면 True.

        되돌리기(Ctrl+Z)는 삭제 전용이라 여기서는 쓰지 않는다 -- 물어보고 바꾸는 동작이라
        되돌리기까지 붙이면 "지금 화면이 어느 견적인지"가 흐려진다. 대신 바꾸기 전에
        library_dialog가 반드시 확인을 받는다.

        입력창(팝업)이 열려 있으면 바꾸지 않는다 -- delete_items와 똑같은 이유다.
        popup.py의 save_and_close()는 팝업을 열 때 붙잡아 둔 item dict를 직접 고치는데,
        그 카드가 app.data에서 통째로 빠지면 저장을 눌러도 오류 없이 조용히 사라진다.
        """
        if self.open_popups:
            if quiet:  # 실시간 동기화가 부른 경우. 알림은 sync가 알림 줄로 띄운다.
                return False
            messagebox.showwarning(
                "불러올 수 없음",
                f"항목 입력창 {len(self.open_popups)}개가 열려 있습니다.\n"
                f"입력창을 모두 닫은 뒤 다시 불러와 주세요.\n\n"
                f"(입력창은 지금 카드를 직접 고치고 있어서, 목록이 통째로 바뀌면 그 입력이"
                f" 저장되지 않고 사라집니다.)")
            return False
        self.data = payload["items"]
        self.selected_nos = set()
        self.anchor_no = None
        self.last_deleted = []
        # 불러온 견적은 이미 저장된 것이므로 NEW 배지를 붙이지 않는다.
        for item in self.data:
            item["save_pending"] = False
            item["is_new_registration"] = False
        self.set_library_current({"title": payload["title"], "path": path, "mtime": payload["mtime"]})
        self.save_session(sync=False)
        self.refresh_table(True)
        return True

    def _start_settings_load(self):
        def worker():
            try:
                loaded = settings_store.load()
                state = datastore.get_state()
                error = settings_store.get_load_error()
            except OSError:
                loaded = settings_store.defaults()
                state = dict(self.data_state or {"dir": "", "shared": True,
                                                 "ok": False,
                                                 "reason": datastore.REASON_UNREACHABLE})
                error = datastore.REASON_UNREACHABLE
            self.settings_load_queue.put((loaded, state, error))

        threading.Thread(target=worker, daemon=True).start()
        self.root.after(80, self._poll_settings_load)

    def _poll_settings_load(self):
        try:
            loaded, state, error = self.settings_load_queue.get_nowait()
        except queue.Empty:
            if self.settings_loading:
                self.root.after(80, self._poll_settings_load)
            return
        self._finish_settings_load(loaded, state, error)

    def _finish_settings_load(self, loaded, state, error):
        self.settings_loading = False
        self.settings = loaded
        self.rates = loaded["rates"]
        self.data_state = state
        self.settings_load_error = error
        self.col_widths = dict(loaded.get("col_widths", {}))
        self.col_width_overridden = set(self.col_widths.keys())
        if self.table is not None:
            self.table.relayout()
        self.refresh_table(False)
        if error:
            self.root.after(100, self.check_data_location)

    def check_data_location(self):
        """공유 폴더를 못 읽었으면 시작할 때 알린다(v0.1.4).

        이 경고가 없으면 사용자는 기본 단가가 뜬 화면을 보고 "설정이 초기화됐다"고 판단해
        값을 다시 입력하게 된다. 그 상태에서는 설정 저장이 막혀 있다는 것도 같이 알린다.
        """
        error = settings_store.get_load_error() or self.settings_load_error
        if not error:
            return
        state = self.data_state or datastore.get_state()
        where = "서버" if state.get("server") else "폴더"
        target = "견적 서버" if state.get("server") else "공유 폴더"
        messagebox.showwarning(
            "설정을 읽지 못했습니다",
            f"{datastore.describe(state)}\n\n{where}: {state['dir']}\n\n"
            f"지금 화면의 단가·소재 목록은 기본값입니다. 잘못된 값이 {target}에 덮어써지지"
            f" 않도록 설정 저장을 막아 두었습니다.\n\n"
            f"네트워크 연결을 확인한 뒤 프로그램을 다시 켜거나, [설정 > 데이터 위치]에서"
            f" {where}를 다시 지정해 주세요.")


    # ---------- 열 제목 / 열 폭 ----------

    def update_header_labels(self):
        """열 제목은 settings["headers"]에서 읽어 표 머리글을 다시 그린다."""
        if self.table is not None:
            self.table.redraw_header()

    def apply_settings(self, new_settings):
        """설정창에서 저장한 값을 화면 전체에 반영한다."""
        self.settings = new_settings
        self.rates = new_settings["rates"]
        if self.table is not None:
            self.table.relayout()
        self.refresh_table(False)

    def save_column_settings(self):
        if self.settings_loading:
            return
        from .table import _persist_column_widths
        _persist_column_widths(self)

    def reset_column_widths(self):
        self.col_widths = {}
        self.col_width_overridden = set()
        if self.table is not None:
            self.table.relayout()
        self.save_column_settings()
        self.refresh_table(False)

    # ---------- 세션 ----------

    def save_session(self, sync=True):
        """작업 중 상태를 이 PC에 남긴다. 카드를 고친 모든 자리가 이걸 부르므로, v1.4.0부터는
        여기서 실시간 동기화의 자동 저장도 예약한다(sync=False면 하지 않는다)."""
        search_text = self.search_var.get() if hasattr(self, "search_var") else ""
        session.save(self.data, self.selected_nos, search_text, self.library_current,
                     self.new_items)
        if sync:
            self.sync.schedule_push()

    def restore_session(self):
        payload = session.load()
        if not payload:
            return
        self.data = payload["items"]
        self.new_items = payload.get("new_items", [])
        self.selected_nos = set(payload["selected_nos"])
        # v0.1.4: 보관함 참조도 되살린다. 이게 없으면 프로그램을 껐다 켠 뒤 같은 견적을
        # 저장할 때 "다른 사람이 고쳤습니다" 경고가 조용히 죽는다(session.py 첫머리 참고).
        self.library_current = payload.get("library")
        # v1.3.0: 데이터 위치를 서버↔폴더로 바꾸기 전에 남은 참조면 버린다. 그대로 두면 종료할
        # 때 자동 저장이 엉뚱한 위치에 쓰려다 실패해 종료가 계속 취소된다.
        if self.library_current and not library.belongs_to_location(self.library_current.get("path")):
            self.library_current = None
        # v1.5.0: 변경 내용 표시(동기화 줄)의 기준점. 껐다 켜기 전에 안 올린 변경이 있었다면 기준을
        # 알 수 없어 비워 둔다(그때는 '변경사항 있음'만 표시한다).
        if self.library_current and not self.library_dirty():
            self.sync.reset_baseline()
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

    def _set_status_texts(self, all_items, visible_items, query):
        """하단 상태 표시줄: 왼쪽은 이 목록의 건수·금액, 오른쪽은 데이터 위치·보관함·세션."""
        selected_count = len([item for item in all_items if item["no"] in self.selected_nos])
        total_amount = calc_total_amount(all_items, self.rates)
        today = datetime.now().strftime("%Y-%m-%d")
        # v0.1.3: 중복 품번은 행 색으로 표시하지만, 짝이 화면 밖(검색)에 있으면 눈에 안 띈다.
        # 건수를 같이 적어 "어딘가에 겹친 게 있다"는 것을 알린다.
        duplicate_count = len([item for item in all_items if self.is_duplicate_item(item)])
        left = [f"작성일 {today}", f"항목 {len(all_items)}건"]
        if query:
            left.append(f"검색 결과 {len(visible_items)}건")
        left.append(f"선택 {selected_count}건")
        if duplicate_count:
            left.append(f"품번 중복 {duplicate_count}건")
        left.append(f"총 견적금액 {total_amount:,}원")

        # v0.1.4: 공유 폴더·서버를 쓰는 중인지, 지금 화면이 보관함의 어느 견적인지 한눈에 보이게
        # 한다 — 네트워크에서는 "내가 지금 무엇을 고치고 있는가"가 사고를 막는 정보다.
        state = self.data_state
        if state is None:
            state = datastore.get_state()
            self.data_state = state
        place = "견적 서버" if state.get("server") else "공유 폴더"
        right = []
        if state.get("server") and editlock.is_protected():
            right.append("🔓 편집 가능" if editlock.can_edit() else "🔒 읽기 전용")
        if getattr(self, "settings_loading", False):
            right.append("공유 설정 확인 중")
        elif state["shared"]:
            right.append(f"● {place} 연결됨" if state["ok"] else f"● {place} 연결 안 됨")
        if self.library_current:
            right.append(f"보관함 '{self.library_current['title']}'")
        if self.session_saved_at:
            right.append(f"세션 복원 {self.session_restored_count}건 (저장 {self.session_saved_at})")
        else:
            right.append("새 세션")
        self.summary_var.set("   │   ".join(left))
        self.location_var.set("   │   ".join(right))

    def update_summary_text(self):
        """표는 건드리지 않고 하단 상태 표시줄(선택 건수 등)만 다시 계산한다."""
        query = self.get_search_text()
        all_items, visible_items = filter_items(self.data, query)
        self.duplicate_part_nos = find_duplicate_part_nos(all_items)
        self._set_status_texts(all_items, visible_items, query)

    def refresh_table(self, reset_limit=False):
        """목록을 다시 그린다. 표는 보이는 행만 그리므로 건수가 많아도 한 화면 분량만 든다.

        reset_limit=True는 "목록의 내용 자체가 바뀌었다"는 신호다(검색·검색 초기화·견적 불러오기
        등). 그때만 스크롤을 맨 위로 되돌린다 — 체크 토글 같은 곳에서 스크롤이 튀면 불편하다.
        (v1.5.0: "더 보기"로 40건씩 끊어 보이던 방식은 없앴다. 전부 스크롤로 본다.)
        """
        self.search_after_id = None
        if self.table is None:
            return

        query = self.get_search_text()
        all_items, visible_items = filter_items(self.data, query)
        self.selected_nos.intersection_update({item["no"] for item in all_items})
        # 색을 칠하기 전에 중복 집합을 먼저 갱신한다 — 표가 그릴 때 이 값을 본다.
        self.duplicate_part_nos = find_duplicate_part_nos(all_items)
        self._set_status_texts(all_items, visible_items, query)

        # 화면 순번은 여기서 한 번만 정하고, 팝업 제목·정보 타일도 이 값을 쓴다.
        self.visible_nos = [item["no"] for item in visible_items]
        self.display_nos = {no: index + 1 for index, no in enumerate(self.visible_nos)}

        if not all_items:
            self.table.set_empty("아직 작성된 견적 항목이 없습니다.", "상단의 '신규품목'을 사용하세요.",
                                 reset_scroll=reset_limit)
        elif not visible_items:
            self.table.set_empty("검색 결과가 없습니다.", "품번, 품명, 기종으로 검색할 수 있습니다.",
                                 reset_scroll=reset_limit)
        else:
            self.table.set_rows(visible_items, reset_scroll=reset_limit)

    def is_duplicate_item(self, item):
        """이 카드의 품번이 목록 안에서 겹치는가(v0.1.3)."""
        key = normalize_part_no(item.get("part_no"))
        return bool(key) and key in self.duplicate_part_nos

    # ---------- 검색 / 선택 ----------

    def clear_search(self):
        self.search_var.set("")
        self.refresh_table(True)

    def set_selection(self, new_selection):
        """선택 집합을 통째로 바꾸되, 실제로 달라진 행만 다시 칠한다."""
        new_selection = set(new_selection)
        changed = self.selected_nos.symmetric_difference(new_selection)
        self.selected_nos = new_selection
        if changed and self.table is not None:
            self.table.redraw_body()
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
        self.open_new_items(add_immediately=True)

    def open_new_items(self, add_immediately=False):
        if not self.require_edit("신규품목 입력"):
            return
        open_new_items_dialog(self, add_immediately=add_immediately)

    def open_popup(self, no):
        open_item_popup(self, no)

    def open_next_item(self, no):
        """연속 신규 등록은 반드시 신규품목 전용 창에서 이어 간다."""
        self.open_new_items(add_immediately=True)

    # ---------- 삭제 / 되돌리기 (v0.1.2) ----------

    def delete_selected_items(self):
        if not self.require_edit("항목 삭제"):
            return
        if not self.selected_nos:
            messagebox.showinfo("선택 없음", "삭제할 항목을 먼저 선택하세요.")
            return
        self.delete_items(self.selected_nos)

    def open_row_context_menu(self, no, event):
        """행 우클릭 메뉴. 슬롯마다 만들지 않고 앱에 하나만 만들어 재사용한다(표 슬롯이
        재사용되는 구조라 슬롯마다 달면 메뉴가 계속 쌓인다 -- 인수인계서 함정 6/7번과
        같은 이유). 메뉴 항목은 self.context_menu_no를 호출 시점에 읽는다.

        선택 밖 행을 우클릭하면 그 행만 선택하고, 선택 안 행이면 지금 선택을 그대로
        둔다(윈도우 탐색기 규칙, 요청 2-1). "삭제"는 그 뒤의 self.selected_nos를
        그대로 쓰므로 별도 분기가 필요 없다 -- 여기서 이미 의도한 대상으로 정리됐다.
        """
        if no not in self.selected_nos:
            self.handle_row_click(no, "plain")
        self.context_menu_no = no
        if self.row_context_menu is None:
            c = self.theme.colors
            menu = tk.Menu(self.root, tearoff=0, bg=c["card_alt"], fg=c["text"],
                           activebackground=c["accent"], activeforeground=c["bg"],
                           bd=0, relief="flat")
            menu.add_command(label="입력창 열기", command=lambda: self.open_popup(self.context_menu_no))
            menu.add_separator()
            menu.add_command(label="삭제", command=lambda: self.delete_items(self.selected_nos))
            self.row_context_menu = menu
        try:
            self.row_context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            # tk_popup 뒤에 반드시 불러야 한다 -- 안 부르면 메뉴가 grab을 쥔 채 남아
            # 다음 클릭이 먹통이 된다(Tk의 알려진 동작).
            self.row_context_menu.grab_release()

    def delete_items(self, nos):
        """선택 삭제·우클릭 삭제가 공통으로 부르는 실제 삭제.

        대상 중 하나라도 입력창(팝업)이 열려 있으면 아무것도 지우지 않는다 -- popup.py의
        save_and_close()가 팝업을 열 때 붙잡아 둔 item dict를 직접 고치는 구조라(502행
        부근), 그 카드가 app.data에서 먼저 빠지면 저장을 눌러도 오류 없이 조용히
        사라진다. 부분 삭제도 하지 않는다 -- 막힌 게 있으면 전부 취소한다.
        """
        if not self.require_edit("항목 삭제"):
            return
        nos = set(nos)
        index_by_id = {id(row): idx for idx, row in enumerate(self.data)}
        targets = [item for item in self.data if item["no"] in nos]
        if not targets:
            return

        blocked = [item for item in targets if item["no"] in self.open_popups]
        if blocked:
            lines = "\n".join(
                f"  NO.{self.get_display_no(item['no']) or '-'}  {item['part_no'] or '품번 미입력'}"
                for item in blocked)
            messagebox.showwarning(
                "삭제할 수 없음",
                f"다음 항목은 입력창이 열려 있어 지울 수 없습니다:\n{lines}\n\n"
                f"입력창을 닫은 뒤 다시 시도해 주세요.")
            return

        preview = targets[:5]
        lines = "\n".join(
            f"  NO.{self.get_display_no(item['no']) or '-'}  "
            f"{item['part_no'] or '품번 미입력'} / {item['part_name'] or '품명 미입력'}"
            for item in preview)
        if len(targets) > 5:
            lines += f"\n  ...외 {len(targets) - 5}건"
        if not messagebox.askyesno(
                "삭제 확인",
                f"선택한 {len(targets)}건을 삭제할까요?\n\n{lines}\n\n"
                f"방금 삭제한 항목은 현황판에서 Ctrl+Z로 되돌릴 수 있습니다.",
                default="no"):
            return

        self.last_deleted = [{"item": item, "index": index_by_id[id(item)]} for item in targets]
        target_nos = {item["no"] for item in targets}
        self.data = [item for item in self.data if item["no"] not in target_nos]
        self.selected_nos -= target_nos
        if self.anchor_no in target_nos:
            self.anchor_no = None
        self.save_session()
        self.refresh_table(True)

    def undo_delete(self):
        """방금 지운 카드를 되살린다(단일 단계, 세션에는 안 남기고 메모리에만 둔다).

        지운 뒤 `새 항목 추가`/`저장 후 다음 항목`으로 새 카드가
        생겼으면 get_next_no()가 방금 비운 번호를 다시 내줬을 수 있다(요청 확인한
        구조 (6)). 그 경우 되살리면 번호가 겹치므로, 되살리는 이 시점에 겹치는지
        검사한다 -- 번호를 새로 만드는 쪽(add_row 등) 코드를 일일이 손대지 않아도
        되고, 나중에 새 경로가 추가돼도 안전하다.
        """
        if not self.last_deleted:
            return
        if not self.require_edit("삭제 되돌리기"):
            return
        current_nos = {row["no"] for row in self.data}
        if any(entry["item"]["no"] in current_nos for entry in self.last_deleted):
            messagebox.showerror(
                "되돌릴 수 없음",
                "삭제한 뒤 같은 번호의 카드가 새로 만들어져 되돌릴 수 없습니다.")
            self.last_deleted = []
            return

        for entry in sorted(self.last_deleted, key=lambda e: e["index"]):
            index = min(entry["index"], len(self.data))
            self.data.insert(index, entry["item"])
        restored_nos = {entry["item"]["no"] for entry in self.last_deleted}
        self.last_deleted = []
        self.save_session()
        self.refresh_table(True)
        self.set_selection(restored_nos)

    # ---------- 엑셀 ----------

    def _export_parent(self, parent):
        try:
            return parent if parent is not None and parent.winfo_exists() else self.root
        except tk.TclError:
            return self.root

    def _poll_export(self, export_queue, original_items, chosen_path, parent):
        try:
            status, value = export_queue.get_nowait()
        except queue.Empty:
            if self.export_in_progress:
                self.root.after(80, lambda: self._poll_export(export_queue, original_items, chosen_path, parent))
            return

        parent = self._export_parent(parent)
        self.export_in_progress = False
        self.root.configure(cursor="")
        if status == "ok":
            saved_count = value
            # v0.0.9: 날짜별 누적 저장을 없애면서 저장 완료 표시를 여기로 옮겼다.
            # 안 그러면 NEW 배지를 지워 줄 곳이 없어 모든 카드에 영원히 붙어 있게 된다.
            for item in original_items:
                item["save_pending"] = False
                item["is_new_registration"] = False
            self.save_session()
            self.refresh_table(False)
            messagebox.showinfo("다운로드 완료",
                                f"{saved_count}개 항목을 저장했습니다.\n\n{chosen_path}",
                                parent=parent)
            return

        kind, message = value
        if kind == "TemplateNotFound":
            messagebox.showerror("파일 오류", f"'{message}' 파일이 존재하지 않습니다.", parent=parent)
        elif kind == "SheetNotFound":
            messagebox.showerror("시트 오류", f"'{message}' 시트를 찾을 수 없습니다.", parent=parent)
        else:
            messagebox.showerror("저장 오류", f"파일을 저장하지 못했습니다.\n{message}", parent=parent)
        self.refresh_table(False)

    def export_items(self, items, default_name=None, parent=None):
        """고른 항목을 엑셀 견적 파일로 내려받는다(v0.0.9: PDF 출력은 없앴다, 요청 3-1)."""
        if not items:
            messagebox.showwarning("다운로드 대상 없음", "다운로드할 항목을 먼저 선택하거나 입력하세요.", parent=parent)
            return False
        if self.settings_loading:
            messagebox.showinfo("설정 확인 중", "공유 설정을 불러오는 중입니다. 잠시 뒤 다시 내려받아 주세요.", parent=parent)
            return False
        if self.export_in_progress:
            messagebox.showinfo("저장 중", "엑셀 파일을 저장하는 중입니다.", parent=parent)
            return False
        parent = parent or self.root

        base_name = os.path.splitext(default_name or _download_file_name(items))[0]
        chosen_path = filedialog.asksaveasfilename(
            parent=parent,
            title="다운로드 저장 위치 선택",
            defaultextension=".xlsx",
            initialfile=base_name + ".xlsx",
            filetypes=[("Excel files", "*.xlsx")])
        if not chosen_path:
            return False

        original_items = list(items)
        item_snapshot = deepcopy(original_items)
        rates_snapshot = dict(self.rates)
        settings_snapshot = deepcopy(self.settings)
        export_queue = queue.Queue()
        self.export_in_progress = True
        self.root.configure(cursor="watch")
        self.summary_var.set("엑셀 파일을 저장하는 중입니다...")

        def worker():
            try:
                saved_count = excel_io.export_items(item_snapshot, rates_snapshot,
                                                    chosen_path, settings_snapshot)
                export_queue.put(("ok", saved_count))
            except excel_io.TemplateNotFound as exc:
                export_queue.put(("error", ("TemplateNotFound", str(exc))))
            except excel_io.SheetNotFound as exc:
                export_queue.put(("error", ("SheetNotFound", str(exc))))
            except OSError as exc:
                export_queue.put(("error", ("OSError", str(exc))))
            except Exception as exc:
                export_queue.put(("error", ("Exception", str(exc))))

        threading.Thread(target=worker, daemon=True).start()
        self.root.after(80, lambda: self._poll_export(export_queue, original_items, chosen_path, parent))
        return True

    def export_selected_items(self):
        # 화면에 보이는 차례 그대로 엑셀에 담는다(맨 위 카드가 엑셀에서도 첫 줄).
        _, visible_items = filter_items(self.data, self.get_search_text())
        selected_items = [item for item in visible_items
                          if has_item_data(item) and item["no"] in self.selected_nos]
        self.export_items(selected_items,
                          default_name=_download_file_name(selected_items),
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
