"""여러 화면에서 같이 쓰는 작은 위젯."""

import tkinter as tk


def make_checkbox(parent, theme, checked, on_toggle):
    """직접 그린 큰 체크박스.

    Windows 기본 tk 체크박스 표시기는 약 13px 고정이라 글꼴을 키워도 커지지 않는다.
    theme.json의 checkbox_size(기본 26px)만큼 정사각형을 Frame으로 그려서 클릭 토글한다.
    """
    c = theme.colors
    size = theme.layout["checkbox_size"]
    box_bg = c["accent"] if checked else c["card_alt"]
    box_fg = c["bg"] if checked else c["muted"]
    # 선택 시엔 강조색 자체로 눈에 띄니 테두리는 채움색과 맞춰 매끈하게, 선택 전엔
    # checkbox_border로 또렷하게 — line은 밝은 배경끼리 대비가 너무 약해서 안 쓴다.
    border = box_bg if checked else c["checkbox_border"]
    holder = tk.Frame(parent, width=size, height=size, bg=box_bg,
                      highlightthickness=2, highlightbackground=border, cursor="hand2")
    holder.pack_propagate(False)
    glyph = tk.Label(holder, text=("V" if checked else ""), bg=box_bg, fg=box_fg,
                     font=(theme.family, theme.fonts["normal_size"], "bold"))
    glyph.pack(expand=True)
    handler = lambda event: on_toggle(not checked)
    holder.bind("<Button-1>", handler)
    glyph.bind("<Button-1>", handler)
    # 행 전체 클릭(팝업 열기)이 이 위젯을 덮어쓰지 않도록 표시해 둔다.
    holder.is_control = True
    # 토글 후 체크박스 표시만 다시 칠할 때(표 전체를 다시 그리지 않기 위해) 필요하다.
    holder.glyph = glyph
    return holder
