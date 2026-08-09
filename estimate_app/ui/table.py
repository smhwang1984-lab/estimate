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

v0.1.0: 헤더 열 사이에 연한 세로 구분선을 두고, 끌면 좌우 열 폭이 바뀐다(요청 3-2, 3-3).
데이터 행에는 선을 넣지 않는다(요청 3-1) — 구분선은 헤더에만 있다. 폭은 app.col_widths에
살아 있고 끄는 즉시 헤더와 모든 행 슬롯에 같이 반영되며, 손을 떼면 settings.json에 남는다
(다음에 켤 때도 그대로 열린다). 한 번이라도 사용자가 끈 열은 창 크기가 바뀌어도 그 폭을
지키도록 weight를 0으로 고정한다 — 그 전까지는 품명·Comment가 남는 폭을 나눠 갖는다.

v0.1.3: 품번이 겹치는 행은 배경을 주황 계열(row_dup_bg/row_dup_alt_bg)로 물들이고 품번
글자색도 함께 바꾼다(요청 3). 배경 우선순위는 선택 > 중복 > 줄무늬이며, 판정 자체는
dashboard가 목록 전체를 보고 미리 만들어 둔 집합(app.duplicate_part_nos)이 쥐고 있다.
마우스를 올린 동안(row_hover)에는 선택 행과 마찬가지로 잠깐 hover 색이 덮는다.
"""

import tkinter as tk

from ..core import settings as settings_store
from ..core.pricing import calc_row
from .widgets import make_checkbox

MIN_COL_WIDTH = 40

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


def fit_text(theme, text, max_width_px):
    """실제 글꼴 폭으로 재 가며 칸에 맞게 자른다(요청 3-4). shorten()의 상수 글자 수 대신
    쓴다 — 소재 칸이 사용자가 끌어 조절할 수 있게 되면서 상수로는 넓혀도 `…`이 남는다.
    """
    text = str(text)
    font = theme.table_cell_font
    if font.measure(text) <= max_width_px:
        return text
    ellipsis = "…"
    budget = max_width_px - font.measure(ellipsis)
    if budget <= 0:
        return ellipsis
    lo, hi = 0, len(text)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if font.measure(text[:mid]) <= budget:
            lo = mid
        else:
            hi = mid - 1
    return text[:lo] + ellipsis


def configure_columns(container, app):
    """헤더와 각 행이 같은 열 폭을 쓰도록 동일한 규칙을 적용한다.

    v0.1.0: 폭은 theme.json 기본값이 아니라 app.col_widths(설정에 저장, 요청 3-3)를
    먼저 본다. 사용자가 직접 끈 열(app.col_width_overridden)은 weight를 0으로 고정해
    창을 늘려도 그 폭을 지킨다 — 그 전까지는 원래 비율(품명 3 : Comment 2)대로 나눠 갖는다.
    """
    layout = app.theme.layout
    widths = getattr(app, "col_widths", {})
    overridden = getattr(app, "col_width_overridden", set())
    for idx, (_, width_key, weight) in enumerate(COLUMNS):
        width = widths.get(width_key, layout[width_key])
        effective_weight = 0 if width_key in overridden else weight
        container.columnconfigure(idx, weight=effective_weight, minsize=width)


def build_header(parent, app):
    """스크롤 영역 밖에 두는 고정 헤더(th). CSS의 position:sticky 역할.

    v0.1.0: 열 사이에 끌어서 폭을 바꾸는 구분선을 더한다(요청 3-2, 3-3).
    """
    theme = app.theme
    c = theme.colors
    pad_x, pad_y = theme.layout["cell_pad_x"], theme.layout["cell_pad_y"]

    header = tk.Frame(parent, bg=c["th_bg"])
    configure_columns(header, app)
    for idx, (title, _, _) in enumerate(COLUMNS):
        if title == "최종단가":
            anchor = "e"
        elif title in ("가능여부", "No"):
            anchor = "center"
        else:
            anchor = "w"
        tk.Label(header, text=title, bg=c["th_bg"], fg=c["th_fg"], font=theme.table_head,
                 anchor=anchor).grid(row=0, column=idx, sticky="ew", padx=pad_x, pady=pad_y)
    _add_column_resizers(app, header)
    return header


def _apply_column_widths(app):
    """폭이 바뀐 뒤 헤더와 지금 살아 있는 행 슬롯 전부에 같은 값을 적용한다.

    슬롯은 dashboard.row_slots에 담겨 재사용되므로(숨겨 둔 것도 나중에 다시 쓰인다),
    헤더만 고치면 표가 어긋난다 -- 반드시 함께 고친다.
    """
    if getattr(app, "header_frame", None) is not None:
        configure_columns(app.header_frame, app)
    for slot in getattr(app, "row_slots", []):
        configure_columns(slot["frame"], app)


def _persist_column_widths(app):
    """settings.json에 지금 열 폭을 남긴다(요청 3-3). 드래그를 끝낸 순간(손을 뗄 때)만 쓴다
    -- 끄는 동안 매 픽셀마다 파일에 쓰면 느려진다.
    """
    # v0.1.4: 반드시 파일에서 다시 읽어 그 위에 열 폭만 얹는다. app.settings는 프로그램을
    # 켤 때 읽은 사본이라, 공유 폴더를 쓰는 중에 다른 PC가 단가를 고쳤다면 낡은 값이다.
    # 그대로 통째로 저장하면 열 구분선을 끄는 것만으로 남의 단가 수정이 날아간다
    # (파일이 로컬이던 v0.1.3까지는 생길 수 없던 사고다).
    payload = settings_store.load()
    payload["col_widths"] = dict(app.col_widths)
    if settings_store.save(payload):
        # 화면에는 열 폭만 반영한다. 방금 읽어 온 단가까지 app에 밀어 넣으면 열 구분선을
        # 끌었을 뿐인데 표의 금액이 통째로 바뀌어 버린다(그건 설정창이 할 일이다).
        app.settings["col_widths"] = dict(app.col_widths)


def _reposition_resizers(header, handles):
    for idx, handle in handles:
        # row를 같이 안 주면 Tk가 "그 열 하나"가 아니라 그리드 전체 bbox를 돌려준다
        # (직접 겪음 -- 핸들 9개가 전부 같은 자리에 겹쳐 소재 헤더 글자를 가렸다).
        bbox = header.grid_bbox(row=0, column=idx)
        if not bbox:
            continue
        x, _y, w, _h = bbox
        handle.place(x=x + w - 1, y=0, width=2, relheight=1.0)


def _add_column_resizers(app, header):
    """열과 열 사이에 연한 세로 구분선을 두고, 끌면 좌우 폭이 바뀐다(요청 3-2, 3-3).

    데이터 행에는 선을 넣지 않는다(요청 3-1) -- 이 구분선은 헤더 위에만 얹는다(`place`로
    경계 위치에 겹쳐 그린다. 헤더는 grid라 열과 열 사이에 별도 칸을 끼워 넣지 않아도 된다).
    """
    theme = app.theme
    handles = []
    drag_state = {}

    for idx in range(len(COLUMNS) - 1):
        handle = tk.Frame(header, bg=theme.color("line"), cursor="sb_h_double_arrow")
        handles.append((idx, handle))
        left_key = COLUMNS[idx][1]
        right_key = COLUMNS[idx + 1][1]

        def start_drag(event, left_key=left_key, right_key=right_key):
            drag_state["x"] = event.x_root
            drag_state["left"] = app.col_widths.get(left_key, theme.layout[left_key])
            drag_state["right"] = app.col_widths.get(right_key, theme.layout[right_key])

        def on_drag(event, left_key=left_key, right_key=right_key):
            if "x" not in drag_state:
                return
            delta = event.x_root - drag_state["x"]
            new_left = max(MIN_COL_WIDTH, drag_state["left"] + delta)
            actual_delta = new_left - drag_state["left"]
            new_right = drag_state["right"] - actual_delta
            if new_right < MIN_COL_WIDTH:
                new_right = MIN_COL_WIDTH
                new_left = drag_state["left"] + drag_state["right"] - MIN_COL_WIDTH
            app.col_widths[left_key] = int(new_left)
            app.col_widths[right_key] = int(new_right)
            app.col_width_overridden.add(left_key)
            app.col_width_overridden.add(right_key)
            _apply_column_widths(app)
            _reposition_resizers(header, handles)

        def end_drag(event):
            drag_state.clear()
            _persist_column_widths(app)

        handle.bind("<Button-1>", start_drag)
        handle.bind("<B1-Motion>", on_drag)
        handle.bind("<ButtonRelease-1>", end_drag)

    header.bind("<Configure>", lambda e: _reposition_resizers(header, handles))
    header.after_idle(lambda: _reposition_resizers(header, handles))


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
    configure_columns(row, app)

    # duplicate는 여기서 먼저 False로 둔다 -- 마우스가 슬롯 위를 지나가면 <Leave> 콜백이
    # row_normal_bg(slot)을 부르는데, 그게 update_row_slot보다 먼저 일어날 수 있다.
    slot = {"frame": row, "no": None, "parity": 0, "duplicate": False,
            "new_badge": None, "tinted": []}

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
    # v0.1.3: 품번이 겹치는 행은 배경색으로 알린다(요청 3). 판정은 app이 목록 전체를 보고
    # 미리 해 둔 집합에서 가져온다 -- 행마다 다시 세면 카드 수의 제곱만큼 일이 늘어난다.
    slot["duplicate"] = app.is_duplicate_item(item)
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

    # 중복 행은 배경만으로도 눈에 띄지만, 어느 칸 때문에 물들었는지 알 수 있게 품번 글자색도
    # 함께 바꾼다(색맹 사용자를 위해 배경 하나에만 기대지 않는다).
    slot["partno_label"].configure(
        text=shorten(item["part_no"] or f"NO. {row_index + 1} 미입력", 15),
        fg=c["row_dup_fg"] if slot["duplicate"] else c["text"])
    slot["date_label"].configure(text=item["created_at"])
    slot["partname_label"].configure(text=shorten(item["part_name"] or "품명 미입력", 40))
    slot["comment_label"].configure(text=shorten(one_line(item.get("comment", "")) or "-", 20))
    # 요청 3-4: 상수 글자 수 대신 지금 열 폭에서 실제로 들어가는 만큼만 보여 준다.
    # 소재 열이 사용자가 끌어 조절할 수 있게 되면서, 넓혀도 `…`이 남던 것을 없앤다.
    material_width = app.col_widths.get("col_material_width", theme.layout["col_material_width"])
    usable = max(20, material_width - 2 * theme.layout["cell_pad_x"])
    slot["material_label"].configure(text=fit_text(theme, item["material"] or "-", usable))
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
        우클릭           삭제/입력창 열기 메뉴(v0.1.2)
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

    def on_right_click(event):
        if slot["no"] is not None:
            app.open_row_context_menu(slot["no"], event)
        return "break"

    on_plain = click("plain")
    on_ctrl = click("toggle")
    on_shift = click("range")

    def bind_all(widget):
        # 체크박스처럼 자체 클릭 동작이 있는 위젯(is_control)은 왼쪽 클릭 계열만
        # 건드리지 않는다 -- 우클릭 메뉴는 체크박스 위에서도 똑같이 떠야 한다(요청).
        is_control = getattr(widget, "is_control", False)
        if not is_control:
            widget.bind("<Button-1>", on_plain)
            widget.bind("<Control-Button-1>", on_ctrl)
            widget.bind("<Shift-Button-1>", on_shift)
            widget.bind("<Double-Button-1>", on_double)
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)
        widget.bind("<Button-3>", on_right_click)
        for child in widget.winfo_children():
            bind_all(child)

    bind_all(slot["frame"])
    slot["bind_all"] = bind_all


def _paint(app, slot, color):
    slot["frame"].configure(bg=color)
    for widget in slot["tinted"]:
        widget.configure(bg=color)
