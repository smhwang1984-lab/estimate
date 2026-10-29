"""도구 모음 단추 (v1.9.0): 위에 선형 아이콘, 아래에 글자.

아이콘은 그림 파일이 아니라 Canvas에 선으로 직접 그린다. 그래서 라이트/다크 테마 색을 그대로 따르고
(글자색과 같은 색), PC마다 이모지 글꼴이 달라 모양이 바뀌는 일이 없다. 모든 아이콘은 24×24 격자로 설계했다.
"""

import math
import tkinter as tk
from tkinter import font as tkfont

ICON_PX = 22          # 아이콘 한 변(px). 24 격자를 이 크기로 줄여 그린다
PAD_X = 8
PAD_TOP = 5
GAP = 3
PAD_BOTTOM = 4
MIN_WIDTH = 54


def _pts(ctx, *points):
    out = []
    for x, y in points:
        out.extend((ctx["ox"] + x * ctx["s"], ctx["oy"] + y * ctx["s"]))
    return out


def _line(canvas, ctx, *points, width=None):
    canvas.create_line(*_pts(ctx, *points), fill=ctx["fg"], width=width or ctx["lw"],
                       capstyle=tk.ROUND, joinstyle=tk.ROUND)


def _oval(canvas, ctx, x1, y1, x2, y2, fill=False):
    a = _pts(ctx, (x1, y1), (x2, y2))
    canvas.create_oval(*a, outline="" if fill else ctx["fg"], fill=ctx["fg"] if fill else "", width=ctx["lw"])


def _arc(canvas, ctx, x1, y1, x2, y2, start, extent):
    canvas.create_arc(*_pts(ctx, (x1, y1), (x2, y2)), start=start, extent=extent, style=tk.ARC,
                      outline=ctx["fg"], width=ctx["lw"])


def _rect(canvas, ctx, x1, y1, x2, y2, dash=None):
    canvas.create_rectangle(*_pts(ctx, (x1, y1), (x2, y2)), outline=ctx["fg"], width=ctx["lw"], dash=dash)


def _circle_points(cx, cy, r, a0, a1, steps=24):
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / steps)),
             cy - r * math.sin(math.radians(a0 + (a1 - a0) * i / steps))) for i in range(steps + 1)]


def icon_open(c, x):
    _line(c, x, (3, 19), (3, 6), (9, 6), (11, 8.5), (20, 8.5), (20, 12))
    _line(c, x, (3, 19), (5.5, 12), (22, 12), (19.5, 19), (3, 19))


def icon_save(c, x):
    _line(c, x, (4, 4), (17, 4), (20, 7), (20, 20), (4, 20), (4, 4))
    _line(c, x, (8, 4), (8, 9), (15, 9), (15, 4))
    _line(c, x, (7, 20), (7, 14), (17, 14), (17, 20))


def icon_download(c, x):
    _line(c, x, (12, 3.5), (12, 15))
    _line(c, x, (7, 10.5), (12, 15.5), (17, 10.5))
    _line(c, x, (4, 16), (4, 20), (20, 20), (20, 16))


def icon_new(c, x):
    _oval(c, x, 3, 3, 21, 21)
    _line(c, x, (12, 7.5), (12, 16.5))
    _line(c, x, (7.5, 12), (16.5, 12))


def icon_select_all(c, x):
    _rect(c, x, 4, 4, 20, 20)
    _line(c, x, (8, 12.5), (11, 15.5), (16.5, 8.5))


def icon_deselect(c, x):
    _rect(c, x, 4, 4, 20, 20, dash=(3, 3))
    _line(c, x, (9, 9), (15, 15))
    _line(c, x, (15, 9), (9, 15))


def icon_trash(c, x):
    _line(c, x, (3.5, 7), (20.5, 7))
    _line(c, x, (9, 7), (9, 4), (15, 4), (15, 7))
    _line(c, x, (6, 7), (7, 20), (17, 20), (18, 7))
    _line(c, x, (10.5, 11), (10.5, 16))
    _line(c, x, (13.5, 11), (13.5, 16))


def icon_calculator(c, x):
    _rect(c, x, 5, 3, 19, 21)
    _rect(c, x, 8, 6, 16, 10)
    for cx in (9, 12, 15):
        for cy in (14, 18):
            _oval(c, x, cx - 0.9, cy - 0.9, cx + 0.9, cy + 0.9, fill=True)


def icon_database(c, x):
    _oval(c, x, 5, 3.5, 19, 9)
    _line(c, x, (5, 6.25), (5, 17.75))
    _line(c, x, (19, 6.25), (19, 17.75))
    _arc(c, x, 5, 9, 19, 14.5, 180, 180)
    _arc(c, x, 5, 15.25, 19, 20.75, 180, 180)


def icon_history(c, x):
    _arc(c, x, 4, 5, 20, 21, 155, 280)
    # 화살촉: 호의 끝(75도)에서 반시계 방향으로 향한다
    end = math.radians(75)
    ex, ey = 12 + 8 * math.cos(end), 13 - 8 * math.sin(end)
    dx, dy = -math.sin(end), -math.cos(end)
    tx, ty = ex + dx * 2.4, ey + dy * 2.4
    px, py = -dy, dx
    _line(c, x, (tx - dx * 3.6 + px * 2.8, ty - dy * 3.6 + py * 2.8), (tx, ty), (tx - dx * 3.6 - px * 2.8, ty - dy * 3.6 - py * 2.8))
    _line(c, x, (12, 9.5), (12, 13), (14.8, 14.6))


def icon_sun(c, x):
    _oval(c, x, 8, 8, 16, 16)
    for i in range(8):
        a = math.radians(45 * i)
        _line(c, x, (12 + 6.6 * math.cos(a), 12 - 6.6 * math.sin(a)), (12 + 9.2 * math.cos(a), 12 - 9.2 * math.sin(a)))


def icon_moon(c, x):
    c1, r1, c2, r2 = (11, 12), 8.5, (16, 8.5), 6.5
    outer = [p for p in _circle_points(c1[0], c1[1], r1, 0, 360, 72)
             if math.hypot(p[0] - c2[0], p[1] - c2[1]) >= r2]
    inner = [p for p in _circle_points(c2[0], c2[1], r2, 0, 360, 72)
             if math.hypot(p[0] - c1[0], p[1] - c1[1]) <= r1]
    # 원 위의 점은 0도에서 시작하므로 끊긴 자리를 이어 붙여 하나의 호로 만든다
    def ordered(points, cx, cy):
        angles = sorted(((math.degrees(math.atan2(cy - py, px - cx)) % 360, (px, py)) for px, py in points))
        gaps = [((angles[(i + 1) % len(angles)][0] - a) % 360, i) for i, (a, _p) in enumerate(angles)]
        start = max(gaps)[1] + 1
        return [angles[(start + k) % len(angles)][1] for k in range(len(angles))]
    if outer:
        _line(c, x, *ordered(outer, *c1))
    if inner:
        _line(c, x, *ordered(inner, *c2))


def icon_gear(c, x):
    _oval(c, x, 9, 9, 15, 15)
    _oval(c, x, 5.5, 5.5, 18.5, 18.5)
    for i in range(8):
        a = math.radians(45 * i)
        _line(c, x, (12 + 6.5 * math.cos(a), 12 - 6.5 * math.sin(a)), (12 + 9.3 * math.cos(a), 12 - 9.3 * math.sin(a)),
              width=x["lw"] + 1.2)


def icon_lock(c, x):
    _rect(c, x, 5.5, 11, 18.5, 21)
    _arc(c, x, 8, 3, 16, 12, 0, 180)
    _line(c, x, (8, 7.5), (8, 11))
    _line(c, x, (16, 7.5), (16, 11))
    _oval(c, x, 11, 14.5, 13, 16.5, fill=True)


def icon_unlock(c, x):
    _rect(c, x, 5.5, 11, 18.5, 21)
    _arc(c, x, 8, 1, 16, 10, 0, 180)
    _line(c, x, (8, 5.5), (8, 11))
    _line(c, x, (16, 5.5), (16, 8))
    _oval(c, x, 11, 14.5, 13, 16.5, fill=True)


ICONS = {"open": icon_open, "save": icon_save, "download": icon_download, "new": icon_new,
         "select_all": icon_select_all, "deselect": icon_deselect, "trash": icon_trash,
         "calculator": icon_calculator, "database": icon_database, "history": icon_history,
         "sun": icon_sun, "moon": icon_moon, "gear": icon_gear, "lock": icon_lock, "unlock": icon_unlock}


class ToolButton(tk.Canvas):
    """아이콘(위) + 글자(아래) 도구 단추. kind: normal / primary(강조 배경) / danger(붉은 글씨)."""

    def __init__(self, parent, theme, text, icon, command, kind="normal"):
        self.theme = theme
        c = theme.colors
        self.kind = kind
        if kind == "primary":
            self.bg, self.hover, self.press, self.fg = c["accent"], c["accent_2"], c["accent_2"], c["panel"]
        elif kind == "danger":
            self.bg, self.hover, self.press, self.fg = c["panel"], c["danger_bg"], c["danger_bg"], c["danger_fg"]
        else:
            self.bg, self.hover, self.press, self.fg = c["panel"], c["panel_2"], c["line"], c["text"]
        self.font = tkfont.Font(family=theme.family, size=theme.fonts["small_size"])
        self.text = text
        self.icon = icon
        self.command = command
        super().__init__(parent, bg=self.bg, highlightthickness=0, bd=0, cursor="hand2")
        self._pressed = False
        self.bind("<Enter>", lambda _e: self._paint(self.hover))
        self.bind("<Leave>", lambda _e: self._leave())
        self.bind("<ButtonPress-1>", lambda _e: self._down())
        self.bind("<ButtonRelease-1>", self._up)
        self.redraw()

    # tk 위젯처럼 text를 읽고 바꿀 수 있게 한다(화면 테스트와 잠금 단추가 글자로 상태를 본다)
    def cget(self, key):
        if key == "text":
            return self.text
        return super().cget(key)

    def set(self, text=None, icon=None):
        if text is not None:
            self.text = text
        if icon is not None:
            self.icon = icon
        self.redraw()

    def invoke(self):
        if self.command:
            self.command()

    def _leave(self):
        self._pressed = False
        self._paint(self.bg)

    def _down(self):
        self._pressed = True
        self._paint(self.press)

    def _up(self, event):
        was = self._pressed
        self._pressed = False
        inside = 0 <= event.x <= self.winfo_width() and 0 <= event.y <= self.winfo_height()
        self._paint(self.hover if inside else self.bg)
        if was and inside:
            self.invoke()

    def _paint(self, color):
        self.configure(bg=color)

    def redraw(self):
        self.delete("all")
        text_w = max(self.font.measure(part) for part in self.text.split("\n"))
        width = max(MIN_WIDTH, text_w + PAD_X * 2)
        height = PAD_TOP + ICON_PX + GAP + self.font.metrics("linespace") * (self.text.count("\n") + 1) + PAD_BOTTOM
        self.configure(width=width, height=height, bg=self.bg)
        ctx = {"ox": (width - ICON_PX) / 2, "oy": PAD_TOP, "s": ICON_PX / 24, "fg": self.fg,
               "lw": max(1.4, ICON_PX / 12)}
        ICONS[self.icon](self, ctx)
        self.create_text(width / 2, PAD_TOP + ICON_PX + GAP, text=self.text, fill=self.fg, font=self.font,
                         anchor="n", justify="center")
