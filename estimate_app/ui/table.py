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

열 너비는 theme.json의 layout에서 바꾼다.

v0.0.8: 검색·체크·더보기마다 표 전체를 destroy 후 재생성하던 방식(깜빡임의 원인, 33행
기준 약 3.9초)을 버리고, 행 위젯을 "슬롯" 풀로 재사용한다. 슬롯은 create_row_slot()이
한 번만 만들고, 목록이 바뀔 때마다 update_row_slot()이 텍스트·색만 새로 채운다.
클릭·hover 바인딩도 슬롯 생성 시 한 번만 걸어 둔다 — 콜백이 슬롯 딕셔너리(slot["no"])를
그때그때 읽으므로, 슬롯이 다른 항목을 표시하게 재사용돼도 다시 바인딩할 필요가 없다.

v0.0.9: 맨 앞에 화면 순번 No 열을, 품명과 소재 사이에 Comment 열을 넣었다(요청 1-3, 1-4).
선택 방식은 윈도우 탐색기와 같게 바꿨다(요청 2-1, 2-2) — 한 번 클릭은 그 행만 선택,
Ctrl+클릭은 하나씩 더하고 빼기, Shift+클릭은 기준 행부터 범위 선택, 카드를 여는 것은
더블클릭이다.
"""

import tkinter as tk

from ..core.pricing import calc_row
from .widgets import make_checkbox

# (제목, 최소 폭 설정 키, 남는 폭을 가져가는 비율).
# 비율이 0이면 최소 폭에 고정된다. 품명과 Comment만 늘어나며, 창이 넓을 때 품명 한 열이
# 남는 폭을 통째로 삼켜 Comment가 저 멀리 떨어져 보이던 것을 3:2로 나눠 갖게 했다.
COLUMNS = [
    ("No", "col_no_width", 0),
    ("", "col_check_width", 0),
    ("기종", "col_model_width", 0),
    ("품번", "col_partno_width", 0),
    ("품명", "col_partname_width", 3),
    ("Comment", "col_comment_width", 2),
    ("소재", "col_material_width", 0),
    ("사이즈", "col_size_width", 0),
    ("가능여부", "col_status_width", 0),
    ("최종단가", "col_price_width", 0),
]

# 열 인덱스를 이름으로 부르기 위한 표. COLUMNS 순서를 바꾸면 여기도 같이 고쳐야 한다.
COL_NO, COL_CHECK, COL_MODEL, COL_PARTNO = 0, 1, 2, 3
COL_PARTNAME, COL_COMMENT, COL_MATERIAL, COL_SIZE = 4, 5, 6, 7
COL_STATUS, COL_PRICE = 8, 9


def shorten(text, max_chars):
    """열 폭이 밀리지 않도록 긴 값은 잘라서 보여 준다(전체 값은 팝업에서 확인).

    CSS의 line-clamp/말줄임에 해당하는 처리다. Tk 라벨에는 말줄임 기능이 없어 직접 자른다.
    """
    text = str(text)
    if len(text) <= max_chars:
        return text
    return text[:max_chars - 1] + "…"


def one_line(text):
    """줄바꿈이 든 값(Comment 등)을 한 줄로 접는다.

    v0.0.9에서 Comment를 여러 줄로 적을 수 있게 되면서, 개행이 그대로 라벨에 들어가면
    그 행만 세로로 늘어나 표가 어긋난다. 표에서는 한 줄로 접어 보여 주고 전체는 팝업에서 본다.
    """
    return " ".join(str(text).split())


def configure_columns(container, theme):
    """헤더와 각 행이 같은 열 폭을 쓰도록 동일한 규칙을 적용한다."""
    layout = theme.layout
    for idx, (_, width_key, weight) in enumerate(COLUMNS):
        container.columnconfigure(idx, weight=weight, minsize=layout[width_key])


def build_header(parent, theme):
    """스크롤 영역 밖에 두는 고정 헤더(th). CSS의 position:sticky 역할."""
    c = theme.colors
    pad_x, pad_y = theme.layout["cell_pad_x"], theme.layout["cell_pad_y"]

    header = tk.Frame(parent, bg=c["th_bg"])
    configure_columns(header, theme)
    for idx, (title, _, _) in enumerate(COLUMNS):
        if title == "최종단가":
            anchor = "e"
        elif title in ("가능여부", "No"):
            anchor = "center"
        else:
            anchor = "w"
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

    # 맨 앞 순번(요청 1-3). 카드의 내부 번호가 아니라 지금 화면에 보이는 차례다.
    slot["no_label"] = label(COL_NO, theme.table_cell, anchor="center", fg=c["muted"])

    # 선택 체크박스. 콜백이 slot["no"]를 그때그때 읽으므로 슬롯을 재사용해도 다시
    # 만들 필요가 없다(요청: "체크박스 선택 시 화면 새로 고침 및 깜빡임이 발생함").
    slot["checkbox"] = place(
        make_checkbox(row, theme, lambda: app.toggle_item_selection(slot["no"])),
        COL_CHECK, sticky="w")

    slot["model_label"] = label(COL_MODEL, theme.table_cell)

    # 품번 (저장 전이면 NEW 배지) + 그 아래 작성일
    partno_box = tk.Frame(row, bg=c["row_bg"])
    slot["partno_box"] = partno_box
    slot["tinted"].append(partno_box)
    place(partno_box, COL_PARTNO)
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

    slot["partname_label"] = label(COL_PARTNAME, theme.table_cell)
    # Comment는 품명과 소재 사이(요청 1-4).
    slot["comment_label"] = label(COL_COMMENT, theme.table_cell, fg=c["muted"])
    slot["material_label"] = label(COL_MATERIAL, theme.table_cell, fg=c["muted"])
    slot["size_label"] = label(COL_SIZE, theme.table_cell, fg=c["muted"])

    # 가능여부 배지는 자기 색(성공/경고/위험)을 유지해야 하므로 hover 시 물드는 tinted에서 뺀다.
    slot["status_label"] = place(tk.Label(row, font=theme.badge_bold, padx=8, pady=2),
                                 COL_STATUS, sticky="")

    # 최종단가 (오른쪽 정렬). 자릿수가 맞아 보이도록 고정폭 글꼴(num_family)을 쓴다.
    slot["price_label"] = label(COL_PRICE, theme.table_num_bold, anchor="e", fg=c["accent_2"])

    _bind_row_behavior(app, slot)
    return slot


def update_row_slot(app, slot, item, row_index):
    """재사용 중인 슬롯에 항목 데이터를 채운다. 위젯을 새로 만들지 않는다.

    row_index는 화면에 보이는 차례(0부터)이며, 맨 앞 No 열에 +1 해서 표시한다.
    """
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

    paint_checkbox(app, slot, no in app.selected_nos)

    slot["no_label"].configure(text=str(row_index + 1))
    slot["model_label"].configure(text=shorten(item["model"] or "-", 11))

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

    slot["partno_label"].configure(text=shorten(item["part_no"] or f"NO. {row_index + 1} 미입력", 15))
    slot["date_label"].configure(text=item["created_at"])
    slot["partname_label"].configure(text=shorten(item["part_name"] or "품명 미입력", 40))
    slot["comment_label"].configure(text=shorten(one_line(item.get("comment", "")) or "-", 20))
    slot["material_label"].configure(text=shorten(item["material"] or "-", 14))
    slot["size_label"].configure(text=shorten(item["size"] or "-", 17))

    status_bg, status_fg, _ = theme.get_status_colors(item["possible"])
    slot["status_label"].configure(text=shorten(item["possible"], 9), bg=status_bg, fg=status_fg)

    slot["price_label"].configure(text=f"{final_price:,}")

    slot["frame"].grid(row=row_index, column=0, sticky="ew")


def paint_checkbox(app, slot, selected):
    """체크박스 칸의 색과 글리프만 다시 칠한다(행 전체를 다시 그리지 않기 위해)."""
    c = app.theme.colors
    box_bg = c["accent"] if selected else c["card_alt"]
    box_fg = c["bg"] if selected else c["muted"]
    border = box_bg if selected else c["checkbox_border"]
    checkbox = slot["checkbox"]
    checkbox.configure(bg=box_bg, highlightbackground=border)
    checkbox.glyph.configure(text=("V" if selected else ""), bg=box_bg, fg=box_fg)


def hide_row_slot(slot):
    slot["frame"].grid_remove()


def _bind_row_behavior(app, slot):
    """행 hover 색과 선택·열기 동작을 슬롯 생성 시 한 번만 건다.

    콜백은 슬롯 딕셔너리(slot["no"])를 호출 시점에 읽으므로, 이 슬롯이 나중에
    다른 항목을 표시하도록 재사용되어도 다시 바인딩할 필요가 없다.

    윈도우 탐색기와 같은 규칙이다(요청 2-1, 2-2).
        클릭             그 행만 선택
        Ctrl+클릭        그 행을 선택에 더하거나 뺀다
        Shift+클릭       마지막 기준 행부터 이 행까지 범위 선택
        더블클릭         카드 열기
    Tk는 더블클릭 때 <Button-1>을 먼저 한 번 발생시키므로 첫 클릭의 선택도 함께 일어난다.
    탐색기도 같은 동작이라 그대로 둔다(지연 타이머를 넣으면 클릭 반응만 굼떠진다).
    """
    def on_enter(event):
        _paint(app, slot, app.theme.colors["row_hover"])

    def on_leave(event):
        _paint(app, slot, app.row_normal_bg(slot))

    def click(mode):
        def handler(event):
            if slot["no"] is not None:
                app.handle_row_click(slot["no"], mode)
            return "break"
        return handler

    def on_double(event):
        if slot["no"] is not None:
            app.open_popup(slot["no"])
        return "break"

    on_plain = click("plain")
    on_ctrl = click("toggle")
    on_shift = click("range")

    def bind_all(widget):
        # 체크박스처럼 자체 클릭 동작이 있는 위젯(is_control)은 건드리지 않는다.
        if getattr(widget, "is_control", False):
            return
        widget.bind("<Button-1>", on_plain)
        widget.bind("<Control-Button-1>", on_ctrl)
        widget.bind("<Shift-Button-1>", on_shift)
        widget.bind("<Double-Button-1>", on_double)
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
