"""assets/theme.json의 값을 실제 Tkinter 스타일로 적용한다.

웹으로 치면 style.css를 읽어 화면에 입히는 자리다.
색이나 글꼴을 바꾸고 싶으면 파이썬 코드가 아니라 theme.json을 고치면 된다.
"""

import tkinter as tk
from tkinter import ttk

from ..core import config


class Theme:
    def __init__(self):
        data = config.load_theme()
        self.colors = data["colors"]
        self.fonts = data["fonts"]
        self.layout = data["layout"]
        family = self.fonts["family"]
        self.family = family
        self.normal = (family, self.fonts["normal_size"])
        self.bold = (family, self.fonts["normal_size"], "bold")
        self.small = (family, self.fonts["small_size"], "bold")
        self.title = (family, self.fonts["title_size"], "bold")
        self.card_title = (family, self.fonts["card_title_size"], "bold")
        # 표 글꼴. Tk에서 크기를 음수로 주면 pt가 아니라 픽셀 단위가 되어
        # TSERP의 CSS px 값(th 18px / td 17px)을 그대로 맞출 수 있다.
        table_family = self.fonts["table_family"]
        self.table_head = (table_family, -self.fonts["table_head_px"], "bold")
        self.table_cell = (table_family, -self.fonts["table_cell_px"])
        self.table_cell_bold = (table_family, -self.fonts["table_cell_px"], "bold")
        self.table_sub = (table_family, -self.fonts["table_sub_px"])
        self.pane_head = (family, -self.fonts["pane_head_px"], "bold")
        self.badge = (family, -self.fonts["badge_px"])
        self.badge_bold = (family, -self.fonts["badge_px"], "bold")
        # 금액처럼 자릿수를 맞춰야 하는 값만 고정폭 글꼴(num_family)을 쓴다.
        num_family = self.fonts.get("num_family", table_family)
        self.table_num_bold = (num_family, -self.fonts["table_cell_px"], "bold")
        self.value_num = (num_family, self.fonts["normal_size"], "bold")
        # 헤더 바 위에 얹는 글자(그라데이션 배경용).
        self.header_title = (family, self.fonts["title_size"], "bold")

    def color(self, key):
        return self.colors[key]

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
        style.configure("TLabelframe", background=c["panel"], foreground=c["text"], bordercolor=c["line"])
        style.configure("TLabelframe.Label", background=c["panel"], foreground=c["accent_2"], font=self.bold)
        style.configure("Value.TLabel", background=c["panel"], foreground=c["accent_2"], font=self.value_num)
        style.configure("Muted.TLabel", background=c["panel"], foreground=c["muted"], font=self.small)
        style.configure("Head.TLabel", background=c["panel_2"], foreground=c["accent_2"], font=self.small)
        root.option_add("*TCombobox*Listbox.background", c["card_alt"])
        root.option_add("*TCombobox*Listbox.foreground", c["text"])
        root.option_add("*TCombobox*Listbox.selectBackground", c["accent"])
        root.option_add("*TCombobox*Listbox.selectForeground", c["bg"])

    def paint_gradient(self, canvas, width, height):
        """캔버스에 grad_from -> grad_to 좌->우 그라데이션을 한 줄씩 그린다.

        PIL 없이 Canvas.create_line만으로 그린다(v0.0.8: 배포 용량을 늘리지 않기 위해).
        폭이 바뀔 때만 다시 부르면 되고, 세로 크기 변화에는 다시 그릴 필요가 없다.
        """
        canvas.delete("gradient")
        if width <= 0 or height <= 0:
            return
        c = self.colors
        r1, g1, b1 = self._hex_to_rgb(c["grad_from"])
        r2, g2, b2 = self._hex_to_rgb(c["grad_to"])
        step = max(1, width // 240)  # 폭이 커도 선을 240개 이하로 묶어 그리기 비용을 낮춘다.
        for x in range(0, width, step):
            t = x / max(1, width - 1)
            r = round(r1 + (r2 - r1) * t)
            g = round(g1 + (g2 - g1) * t)
            b = round(b1 + (b2 - b1) * t)
            canvas.create_line(x, 0, x, height, fill=f"#{r:02x}{g:02x}{b:02x}",
                               width=step + 1, tags="gradient")
        canvas.tag_lower("gradient")  # 제목·요약줄·버튼(먼저 만들어 둔 항목)이 항상 위에 오게

    @staticmethod
    def _hex_to_rgb(hex_color):
        h = hex_color.lstrip("#")
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
