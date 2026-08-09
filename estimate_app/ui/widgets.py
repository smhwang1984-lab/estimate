"""여러 화면에서 같이 쓰는 작은 위젯."""

import tkinter as tk


def make_checkbox(parent, theme, on_click):
    """직접 그린 큰 체크박스.

    Windows 기본 tk 체크박스 표시기는 약 13px 고정이라 글꼴을 키워도 커지지 않는다.
    theme.json의 checkbox_size(기본 26px)만큼 정사각형을 Frame으로 그려서 클릭을 받는다.

    v0.0.9 수정: 예전에는 만들 때의 상태(`checked`)를 클로저에 담아 `on_toggle(not checked)`을
    불렀다. 그런데 표는 슬롯을 재사용하고 슬롯을 만들 땐 항상 `checked=False`라서, 어떤 행을
    눌러도 언제나 "켜기"만 전달되어 체크 해제가 되지 않았다(직접 확인한 버그).
    지금은 상태를 여기서 판단하지 않고, 누구를 눌렀는지만 알려 준다 — 켤지 끌지는
    현재 선택 상태를 알고 있는 쪽(대시보드)이 정한다.
    """
    c = theme.colors
    size = theme.layout["checkbox_size"]
    # 처음 그릴 때는 꺼진 모양으로 두고, 실제 상태는 표를 채울 때 다시 칠한다.
    # 선택 시엔 강조색 자체로 눈에 띄니 테두리는 채움색과 맞춰 매끈하게, 선택 전엔
    # checkbox_border로 또렷하게 — line은 밝은 배경끼리 대비가 너무 약해서 안 쓴다.
    holder = tk.Frame(parent, width=size, height=size, bg=c["card_alt"],
                      highlightthickness=2, highlightbackground=c["checkbox_border"],
                      cursor="hand2")
    holder.pack_propagate(False)
    glyph = tk.Label(holder, text="", bg=c["card_alt"], fg=c["muted"],
                     font=(theme.family, theme.fonts["normal_size"], "bold"))
    glyph.pack(expand=True)

    def handler(event):
        on_click()
        return "break"  # 행 전체 클릭(선택 바꾸기)이 뒤따라 실행되지 않게 막는다.

    holder.bind("<Button-1>", handler)
    glyph.bind("<Button-1>", handler)
    # 행 전체 클릭(선택/열기)이 이 위젯을 덮어쓰지 않도록 표시해 둔다.
    holder.is_control = True
    # 토글 후 체크박스 표시만 다시 칠할 때(표 전체를 다시 그리지 않기 위해) 필요하다.
    holder.glyph = glyph
    return holder
