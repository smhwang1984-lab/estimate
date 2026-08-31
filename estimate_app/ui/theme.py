"""assets/theme.json의 값을 실제 Tkinter 스타일로 적용한다.

웹으로 치면 style.css를 읽어 화면에 입히는 자리다.
색이나 글꼴을 바꾸고 싶으면 파이썬 코드가 아니라 theme.json을 고치면 된다.
"""

import tkinter as tk
from tkinter import font as tkfont, ttk

from ..core import config


class Theme:
    def __init__(self, mode=config.DEFAULT_THEME_MODE, font_scale=100):
        self.mode = mode if mode in config.THEME_MODES else config.DEFAULT_THEME_MODE
        self.font_scale = font_scale if font_scale else 100
        data = config.load_theme(self.mode)
        self.colors = data["colors"]
        self.fonts = data["fonts"]
        self.layout = data["layout"]
        self._build_fonts()

    def _build_fonts(self):
        """글꼴 튜플을 전부 (다시) 만든다. __init__과 표 글자 배율 변경이 함께 쓴다.

        v0.1.8: 표 글자 크기 배율(요청)은 현황판 글꼴에만 건다 -- 버튼·안내문까지
        같이 커지면 툴바가 밀려서다(TSERP도 이 배율은 표·상세 패널 전용이다).
        """
        fonts = self.fonts
        family = fonts["family"]
        self.family = family
        self.normal = (family, fonts["normal_size"])
        self.bold = (family, fonts["normal_size"], "bold")
        self.small = (family, fonts["small_size"], "bold")
        self.title = (family, fonts["title_size"], "bold")
        self.card_title = (family, fonts["card_title_size"], "bold")

        # 표 글꼴. Tk에서 크기를 음수로 주면 pt가 아니라 픽셀 단위가 되어
        # TSERP의 CSS px 값(th 18px / td 17px)을 그대로 맞출 수 있다.
        table_family = fonts["table_family"]
        scale = self.font_scale / 100

        def scaled_px(key):
            return max(8, round(fonts[key] * scale))

        self.table_head_px = scaled_px("table_head_px")
        self.table_cell_px = scaled_px("table_cell_px")
        self.table_sub_px = scaled_px("table_sub_px")
        self.badge_px = scaled_px("badge_px")

        self.table_head = (table_family, -self.table_head_px, "bold")
        self.table_cell = (table_family, -self.table_cell_px)
        # 소재 칸 자르기(요청 3-4)가 실제 글꼴 폭으로 재도록 Font 객체도 만들어 둔다
        # (table_cell은 튜플이라 .measure()가 없다).
        self.table_cell_font = tkfont.Font(font=self.table_cell)
        self.table_cell_bold = (table_family, -self.table_cell_px, "bold")
        self.table_sub = (table_family, -self.table_sub_px)
        self.pane_head = (family, -fonts["pane_head_px"], "bold")
        self.badge = (family, -self.badge_px)
        self.badge_bold = (family, -self.badge_px, "bold")
        # 금액처럼 자릿수를 맞춰야 하는 값만 고정폭 글꼴(num_family)을 쓴다.
        num_family = fonts.get("num_family", table_family)
        self.table_num_bold = (num_family, -self.table_cell_px, "bold")
        self.value_num = (num_family, fonts["normal_size"], "bold")
        self.header_title = (family, fonts["title_size"], "bold")

    def color(self, key):
        return self.colors[key]

    def reload(self, mode):
        """다크/라이트를 전환한다. 글꼴·레이아웃은 그대로 두고 팔레트만 다시 읽는다."""
        if mode not in config.THEME_MODES or mode == self.mode:
            return False
        self.mode = mode
        self.colors = config.load_theme(mode)["colors"]
        return True

    def set_font_scale(self, font_scale):
        """표 글자 크기 배율을 바꾼다. 위젯에 이미 박힌 글꼴은 화면을 다시 지어야 반영된다
        (dashboard.apply_font_scale 참고)."""
        if font_scale == self.font_scale:
            return False
        self.font_scale = font_scale
        self._build_fonts()
        return True

    def get_status_colors(self, status):
        """가능여부에 따른 (배경, 글자, 테두리) 색."""
        if status == "불가":
            return self.colors["danger_bg"], self.colors["danger_fg"], self.colors["status_border_danger"]
        if status == "검토필요":
            return self.colors["warn_bg"], self.colors["warn_fg"], self.colors["status_border_warn"]
        return self.colors["success_bg"], self.colors["success_fg"], self.colors["status_border_ok"]

    def apply(self, root):
        """ttk 위젯 전체에 팔레트를 입힌다. 팝업창도 메인 화면과 같은 색으로 보이게 한다."""
        root.option_add("*Font", self.normal)
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        c = self.colors
        style.configure("TFrame", background=c["panel"])
        style.configure("TLabel", background=c["panel"], foreground=c["text"])
        style.configure("TButton", padding=(10, 6), background=c["panel_2"], foreground=c["text"],
                        bordercolor=c["line"], focuscolor=c["accent"])
        style.map("TButton",
                  background=[("active", c["accent"]), ("pressed", c["accent"])],
                  foreground=[("active", c["bg"]), ("pressed", c["bg"])])
        style.configure("TEntry", padding=5, fieldbackground=c["card_alt"], foreground=c["text"],
                        insertcolor=c["text"], bordercolor=c["line"])
        style.configure("TCombobox", padding=5, fieldbackground=c["card_alt"], background=c["card_alt"],
                        foreground=c["text"], arrowcolor=c["accent_2"], bordercolor=c["line"])
        style.map("TCombobox",
                  fieldbackground=[("readonly", c["card_alt"])],
                  foreground=[("readonly", c["text"])],
                  background=[("readonly", c["card_alt"])])
        style.configure("TRadiobutton", background=c["panel"], foreground=c["text"])
        style.map("TRadiobutton", background=[("active", c["panel"])], foreground=[("active", c["accent_2"])])
        style.configure("TCheckbutton", background=c["panel"], foreground=c["text"])
        style.map("TCheckbutton", background=[("active", c["panel"])])
        style.configure("TScrollbar", background=c["panel_2"], troughcolor=c["bg"],
                        bordercolor=c["line"], arrowcolor=c["accent_2"])
        # 설정창 탭(v0.0.9). clam 기본값은 회색 계열이라 밝은 팔레트에서 탭이 배경에 묻힌다.
        style.configure("TNotebook", background=c["panel"], bordercolor=c["line"], tabmargins=(4, 6, 4, 0))
        style.configure("TNotebook.Tab", background=c["panel_2"], foreground=c["muted"],
                        padding=(16, 8), bordercolor=c["line"])
        style.map("TNotebook.Tab",
                  background=[("selected", c["panel"])],
                  foreground=[("selected", c["accent_2"])])
        style.configure("TLabelframe", background=c["panel"], foreground=c["text"], bordercolor=c["line"])
        style.configure("TLabelframe.Label", background=c["panel"], foreground=c["accent_2"], font=self.bold)
        style.configure("Value.TLabel", background=c["panel"], foreground=c["accent_2"], font=self.value_num)
        style.configure("Muted.TLabel", background=c["panel"], foreground=c["muted"], font=self.small)
        style.configure("Head.TLabel", background=c["panel_2"], foreground=c["accent_2"], font=self.small)
        root.option_add("*TCombobox*Listbox.background", c["card_alt"])
        root.option_add("*TCombobox*Listbox.foreground", c["text"])
        root.option_add("*TCombobox*Listbox.selectBackground", c["accent"])
        root.option_add("*TCombobox*Listbox.selectForeground", c["bg"])
