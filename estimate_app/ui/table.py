"""TSERP 현황판(py/web/style.css의 #tbl)과 같은 모양의 목록 표.

웹 쪽 규칙을 Tkinter로 옮긴 것이라 대응 관계를 적어 둔다.

    th                     고정 헤더. 배경 th_bg, 하단 2px th_underline, 고정폭 글꼴 18px bold
    td                     셀. 17px
    tr.datarow:hover       행 전체 배경이 row_hover 로 바뀐다
    tr.datarow.selected    행 전체 배경이 row_selected_bg 로 바뀐다 (v0.0.8: 위/아래 구분선 대신
                           배경을 옅게 물들이는 방식으로 바꿨다 — 선택 행이 많으면 줄이 두꺼운
                           블록처럼 보여 어색하다는 지적을 반영했다)
    .newbadge              저장 전 항목 표시
    .badge                 가능여부 표시

열 구성은 기종 / 품번 / 품명 세 가지를 주 열로 두고, 견적 도구라 판단에 필요한
가능여부와 최종단가를 옆에 붙였다. 열 너비는 theme.json의 layout에서 바꾼다.

v0.0.8: 검색·체크·더보기마다 표 전체를 destroy 후 재생성하던 방식(깜빡임의 원인, 33행
기준 약 3.9초)을 버리고, 행 위젯을 "슬롯" 풀로 재사용한다. 슬롯은 create_row_slot()이
한 번만 만들고, 목록이 바뀔 때마다 update_row_slot()이 텍스트·색만 새로 채운다.
클릭·hover 바인딩도 슬롯 생성 시 한 번만 걸어 둔다 — 콜백이 슬롯 딕셔너리(slot["no"])를
그때그때 읽으므로, 슬롯이 다른 항목을 표시하게 재사용돼도 다시 바인딩할 필요가 없다.
"""

import tkinter as tk

from ..core.pricing import calc_row
from .widgets import make_checkbox

# (제목, 폭 설정 키, 늘어나는 열인지). 폭 키가 None이면 남는 폭을 나눠 갖는다.
COLUMNS = [
    ("", "col_check_width", False),
    ("기종", "col_model_width", False),
    ("품번", "col_partno_width", False),
    ("품명", None, True),
    ("소재", "col_material_width", False),
    ("사이즈", "col_size_width", False),
    ("가능여부", "col_status_width", False),
    ("최종단가", "col_price_width", False),
]


def shorten(text, max_chars):
    """열 폭이 밀리지 않도록 긴 값은 잘라서 보여 준다(전체 값은 팝업에서 확인).

    CSS의 line-clamp/말줄임에 해당하는 처리다. Tk 라벨에는 말줄임 기능이 없어 직접 자른다.
    """
    text = str(text)
    if len(text) <= max_chars:
        return text
    return text[:max_chars - 1] + "…"


def configure_columns(container, theme):
    """헤더와 각 행이 같은 열 폭을 쓰도록 동일한 규칙을 적용한다."""
    layout = theme.layout
    for idx, (_, width_key, stretch) in enumerate(COLUMNS):
        if stretch:
            container.columnconfigure(idx, weight=1, minsize=180)
        else:
            container.columnconfigure(idx, weight=0, minsize=layout[width_key])


def build_header(parent, theme):
    """스크롤 영역 밖에 두는 고정 헤더(th). CSS의 position:sticky 역할."""
    c = theme.colors
    pad_x, pad_y = theme.layout["cell_pad_x"], theme.layout["cell_pad_y"]

    header = tk.Frame(parent, bg=c["th_bg"])
    configure_columns(header, theme)
    for idx, (title, _, _) in enumerate(COLUMNS):
        anchor = "e" if title == "최종단가" else ("center" if title == "가능여부" else "w")
        tk.Label(header, text=title, bg=c["th_bg"], fg=c["th_fg"], font=theme.table_head,
                 anchor=anchor).grid(row=0, column=idx, sticky="ew", padx=pad_x, pady=pad_y)
    return header


def build_header_underline(parent, theme):
    """헤더 아래 2px 파란 줄(border-bottom: 2px solid #4fb0ff)."""
    return tk.Frame(parent, bg=theme.color("th_underline"), height=2)


def render_empty_message(app, title, detail):
    theme = app.theme
    c = theme.colors
    empty = tk.Frame(app.row_container, bg=c["card"], highlightthickness=1,
                     highlightbackground=c["line"], padx=28, pady=28)
    empty.grid(row=0, column=0, columnspan=len(COLUMNS), sticky="ew", pady=10)
    tk.Label(empty, text=title, bg=c["card"], fg=c["text"], font=theme.card_title).pack(anchor="w")
    tk.Label(empty, text=detail, bg=c["card"], fg=c["muted"]).pack(anchor="w", pady=(8, 0))
    return empty


def create_row_slot(app):
    """행 위젯 한 벌을 만든다. 이후 update_row_slot()이 이 위젯들을 재사용해서
    텍스트·색만 바꾼다 — 검색·체크·더보기마다 다시 만들지 않는다.

    셀마다 감싸는 프레임을 두지 않고 라벨을 행 프레임에 바로 배치한다
    (품번 칸만 배지·날짜를 함께 담아야 해서 프레임을 쓴다).
    """
    theme = app.theme
    c = theme.colors
    layout = theme.layout
    pad_x, pad_y = layout["cell_pad_x"], layout["cell_pad_y"]

    row = tk.Frame(app.row_container, bg=c["row_bg"])
    configure_columns(row, theme)

    slot = {"frame": row, "no": None, "parity": 0, "new_badge": None, "tinted": []}

    def place(widget, column, sticky="ew"):
        widget.grid(row=0, column=column, sticky=sticky, padx=pad_x, pady=pad_y)
        return widget

    def label(column, font, anchor="w", fg=c["text"]):
        widget = tk.Label(row, bg=c["row_bg"], fg=fg, font=font, anchor=anchor)
        slot["tinted"].append(widget)
        place(widget, column)
        return widget

    # 선택 체크박스. 콜백이 slot["no"]를 그때그때 읽으므로 슬롯을 재사용해도 다시
    # 만들 필요가 없다(요청: "체크박스 선택 시 화면 새로 고침 및 깜빡임이 발생함").
    slot["checkbox"] = place(
        make_checkbox(row, theme, False, lambda checked: app.toggle_item_selection(slot["no"], checked)),
        0, sticky="w")

    slot["model_label"] = label(1, theme.table_cell)

    # 품번 (저장 전이면 NEW 배지) + 그 아래 작성일
    partno_box = tk.Frame(row, bg=c["row_bg"])
    slot["partno_box"] = partno_box
    slot["tinted"].append(partno_box)
    place(partno_box, 2)
    partno_top = tk.Frame(partno_box, bg=c["row_bg"])
    partno_top.pack(anchor="w", fill=tk.X)
    slot["partno_top"] = partno_top
    slot["tinted"].append(partno_top)
    partno_label = tk.Label(partno_top, bg=c["row_bg"], fg=c["text"], font=theme.table_cell_bold, anchor="w")
    partno_label.pack(side=tk.LEFT)
    slot["partno_label"] = partno_label
    slot["tinted"].append(partno_label)
    date_label = tk.Label(partno_box, bg=c["row_bg"], fg=c["muted"], font=theme.table_sub, anchor="w")
    date_label.pack(anchor="w")
    slot["date_label"] = date_label
    slot["tinted"].append(date_label)

    slot["partname_label"] = label(3, theme.table_cell)
    slot["material_label"] = label(4, theme.table_cell, fg=c["muted"])
    slot["size_label"] = label(5, theme.table_cell, fg=c["muted"])

    # 가능여부 배지는 자기 색(성공/경고/위험)을 유지해야 하므로 hover 시 물드는 tinted에서 뺀다.
    slot["status_label"] = place(tk.Label(row, font=theme.badge_bold, padx=8, pady=2), 6, sticky="")

    # 최종단가 (오른쪽 정렬). 자릿수가 맞아 보이도록 고정폭 글꼴(num_family)을 쓴다.
    slot["price_label"] = label(7, theme.table_num_bold, anchor="e", fg=c["accent_2"])

    _bind_row_behavior(app, slot)
    return slot


def update_row_slot(app, slot, item, row_index):
    """재사용 중인 슬롯에 항목 데이터를 채운다. 위젯을 새로 만들지 않는다."""
    theme = app.theme
    c = theme.colors
    no = item["no"]
    slot["no"] = no
    slot["parity"] = row_index % 2
    _, _, final_price = calc_row(item, app.rates)

    bg = app.row_normal_bg(slot)
    slot["frame"].configure(bg=bg)
    for widget in slot["tinted"]:
        widget.configure(bg=bg)

    selected = no in app.selected_nos
    box_bg = c["accent"] if selected else c["card_alt"]
    box_fg = c["bg"] if selected else c["muted"]
    border = box_bg if selected else c["checkbox_border"]
    checkbox = slot["checkbox"]
    checkbox.configure(bg=box_bg, highlightbackground=border)
    checkbox.glyph.configure(text=("V" if selected else ""), bg=box_bg, fg=box_fg)

    slot["model_label"].configure(text=shorten(item["model"] or "-", 14))

    if item.get("save_pending"):
        if slot["new_badge"] is None:
            badge = tk.Label(slot["partno_top"], text="NEW", bg=c["new_bg"], fg=c["new_fg"],
                             font=theme.small, padx=5, pady=0, highlightthickness=1,
                             highlightbackground=c["new_border"])
            badge.pack(side=tk.LEFT, padx=(0, 6), before=slot["partno_label"])
            slot["new_badge"] = badge
            slot["bind_all"](badge)  # 나중에 생긴 위젯도 hover/click 대상에 포함시킨다
    elif slot["new_badge"] is not None:
        slot["new_badge"].destroy()
        slot["new_badge"] = None

    slot["partno_label"].configure(text=shorten(item["part_no"] or f"NO. {no} 미입력", 18))
    slot["date_label"].configure(text=item["created_at"])
    slot["partname_label"].configure(text=shorten(item["part_name"] or "품명 미입력", 46))
    slot["material_label"].configure(text=shorten(item["material"] or "-", 16))
    slot["size_label"].configure(text=shorten(item["size"] or "-", 22))

    status_bg, status_fg, _ = theme.get_status_colors(item["possible"])
    slot["status_label"].configure(text=shorten(item["possible"], 9), bg=status_bg, fg=status_fg)

    slot["price_label"].configure(text=f"{final_price:,}")

    slot["frame"].grid(row=row_index, column=0, sticky="ew")


def hide_row_slot(slot):
    slot["frame"].grid_remove()


def _bind_row_behavior(app, slot):
    """행 hover 색과 클릭(팝업 열기)을 슬롯 생성 시 한 번만 건다.

    콜백은 슬롯 딕셔너리(slot["no"])를 호출 시점에 읽으므로, 이 슬롯이 나중에
    다른 항목을 표시하도록 재사용되어도 다시 바인딩할 필요가 없다.
    """
    def on_enter(event):
        _paint(app, slot, app.theme.colors["row_hover"])

    def on_leave(event):
        _paint(app, slot, app.row_normal_bg(slot))

    def on_click(event):
        if slot["no"] is not None:
            app.open_popup(slot["no"])

    def bind_all(widget):
        # 체크박스처럼 자체 클릭 동작이 있는 위젯(is_control)은 건드리지 않는다.
        if getattr(widget, "is_control", False):
            return
        widget.bind("<Button-1>", on_click)
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)
        for child in widget.winfo_children():
            bind_all(child)

    bind_all(slot["frame"])
    slot["bind_all"] = bind_all


def _paint(app, slot, color):
    slot["frame"].configure(bg=color)
    for widget in slot["tinted"]:
        widget.configure(bg=color)
