"""견적 현황 표 — 엑셀처럼 한 줄 행으로 그리는 격자 표 (v1.5.0 전면 교체).

v1.4.0까지는 행마다 칸 위젯(라벨·체크박스·구분선 15개 안팎)을 만들어 grid로 배치했다. 40건이면
위젯이 600개를 넘어, 검색·선택·알림 줄 표시마다 Tk가 전부 다시 배치해 0.6~0.9초씩 걸렸다(실측).
v1.5.0은 Canvas 하나에 **화면에 보이는 행만** 그린다. 건수가 수천이어도 그리는 양은 한 화면
분량(약 40행)이라 스크롤·선택·검색이 즉시 반응한다. 윈도우 기본 Treeview 대신 직접 그리는
이유는, Treeview로는 칸 하나만 색칠할 수 없고(가능여부 배지) 열 구분선·NEW 표시를 그릴 수 없어
기존 기능(구분선 켜기/끄기, 가능여부 색, NEW 배지, 열 폭 끌기)을 그대로 지킬 수 없기 때문이다.

바뀌지 않는 규칙(옛 구현의 요청 번호는 dashboard/HANDOVER에 있다)
    선택      클릭=그 행만, Ctrl+클릭=하나씩 더하고 빼기, Shift+클릭=기준 행부터 범위. 체크 칸은
              언제나 그 행 하나만 켜고 끈다. 더블클릭=입력창, 우클릭=메뉴. 선택의 주인은
              app.selected_nos / app.handle_row_click이고 이 표는 그리기와 입력 전달만 한다.
    색 우선순위  hover > 선택 > 품번 중복 > 줄무늬. 중복 행은 품번 글자색도 바꾼다.
    열 폭     끌면 왼쪽 열이 늘고 오른쪽 열이 같은 만큼 줄어든다. 끌기 시작 때 화면에 보이는
              폭을 전부 고정 폭으로 삼고, 손을 떼면 settings.json에 남긴다. 끌지 않은 상태에서는
              품명:Comment가 남는 폭을 3:2로 나눠 갖는다(COLUMNS의 weight).
    구분선    app.display_prefs["dividers"]가 켜져 있을 때만 격자선을 긋는다.

좌표 규칙: 가로 스크롤은 Canvas 기능을 쓰지 않고 self.xoff를 직접 빼서 그린다(머리글과 본문이
같은 값을 쓰므로 어긋날 일이 없다). 세로도 self.top(픽셀)을 직접 쓴다.
"""

import tkinter as tk
from tkinter import font as tkfont, ttk

from ..core import settings as settings_store
from ..core.model import hrc_text
from ..core.pricing import calc_row

MIN_COL_WIDTH = 40
GRAB = 4                 # 열 경계에서 이 픽셀 안이면 폭 조절 손잡이로 본다
SCROLL_ROWS = 3          # 휠 한 칸에 움직이는 행 수
ANIM_MS = 12             # 휠 스크롤 보간 간격
ANIM_EASE = 0.38         # 한 걸음에 남은 거리의 이만큼씩 다가간다

# (제목, 폭 설정 키, 남는 폭을 가져가는 비율). 비율이 0이면 그 폭에 고정된다.
COLUMNS = [
    ("No", "col_no_width", 0),
    ("", "col_check_width", 0),
    ("기종", "col_model_width", 0),
    ("품번", "col_partno_width", 0),
    ("품명", "col_partname_width", 3),
    ("Comment", "col_comment_width", 2),
    ("소재", "col_material_width", 0),
    ("열처리", "col_heat_width", 0),
    ("사이즈", "col_size_width", 0),
    ("등록일", "col_date_width", 0),
    ("가능여부", "col_status_width", 0),
    ("최종단가", "col_price_width", 0),
]

HEADER_KEY_BY_WIDTH = {
    "col_model_width": "model",
    "col_partno_width": "part_no",
    "col_partname_width": "part_name",
    "col_comment_width": "comment",
    "col_material_width": "material",
    "col_heat_width": "heat",
    "col_size_width": "size",
    "col_status_width": "possible",
}

# COLUMNS 순서를 바꾸면 여기도 같이 고쳐야 한다.
(COL_NO, COL_CHECK, COL_MODEL, COL_PARTNO, COL_PARTNAME, COL_COMMENT,
 COL_MATERIAL, COL_HEAT, COL_SIZE, COL_DATE, COL_STATUS, COL_PRICE) = range(12)

_SHIFT, _CONTROL = 0x1, 0x4  # Windows Tk event.state 비트


def shorten(text, max_chars):
    """긴 값을 글자 수로 자른다(전체 값은 입력창에서 확인)."""
    text = str(text)
    if len(text) <= max_chars:
        return text
    return text[:max_chars - 1] + "…"


def one_line(text):
    """줄바꿈이 든 값(Comment 등)을 한 줄로 접는다. 전체는 입력창에서 본다."""
    return " ".join(str(text).split())


def fit_font_text(font, text, max_width_px):
    """실제 글꼴 폭으로 재 가며 칸에 맞게 자른다."""
    text = str(text)
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


def _persist_column_widths(app):
    """settings.json에 지금 열 폭을 남긴다. 끌기를 끝낸 순간(손을 뗄 때)과 종료 때만 쓴다.

    v0.1.4: 반드시 파일에서 다시 읽어 그 위에 열 폭만 얹는다. app.settings는 켤 때 읽은
    사본이라, 서버·공유 폴더를 쓰는 중에 다른 PC가 단가를 고쳤다면 낡은 값이다. 그대로 통째로
    저장하면 열 폭을 끈 것만으로 남의 단가 수정이 날아간다.
    """
    payload = settings_store.load()
    payload["col_widths"] = dict(app.col_widths)
    if settings_store.save(payload):
        # 화면에는 열 폭만 반영한다(방금 읽은 단가까지 밀어 넣으면 금액이 통째로 바뀐다).
        app.settings["col_widths"] = dict(app.col_widths)


class GridTable:
    def __init__(self, parent, app):
        self.app = app
        theme = app.theme
        self.theme = theme
        c = theme.colors

        self.font_cell = tkfont.Font(font=theme.table_cell)
        self.font_bold = tkfont.Font(font=theme.table_cell_bold)
        self.font_head = tkfont.Font(font=theme.table_head)
        self.font_badge = tkfont.Font(font=theme.badge_bold)
        # font.measure/metrics는 한글이 섞이면 호출당 1ms 안팎이라, 한 번 잰 값은 전부 기억해 둔다
        # (캐시 없이 매 프레임 재면 한 화면을 그리는 데 100ms가 넘었다 — 실측).
        self.row_h = max(26, self.font_cell.metrics("linespace") + 12)
        self.badge_line = self.font_badge.metrics("linespace")
        self.new_w = self.font_badge.measure("NEW") + 10
        self.pill_w = {}
        self.head_h = self.row_h + 2
        self.pad = theme.layout["cell_pad_x"]

        self.frame = tk.Frame(parent, bg=c["bg"])
        self.frame.grid_rowconfigure(1, weight=1)
        self.frame.grid_columnconfigure(0, weight=1)
        self.header = tk.Canvas(self.frame, height=self.head_h, bg=c["th_bg"], highlightthickness=0)
        self.body = tk.Canvas(self.frame, bg=c["row_bg"], highlightthickness=0, takefocus=1)
        self.vbar = ttk.Scrollbar(self.frame, orient=tk.VERTICAL, command=self._on_vbar)
        self.hbar = ttk.Scrollbar(self.frame, orient=tk.HORIZONTAL, command=self._on_hbar)
        self.header.grid(row=0, column=0, sticky="ew")
        self.body.grid(row=1, column=0, sticky="nsew")
        self.vbar.grid(row=0, column=1, rowspan=2, sticky="ns")
        self.hbar.grid(row=2, column=0, sticky="ew")

        self.items = []
        self.empty = None
        self.top = 0
        self.target_top = 0
        self.anim_id = None
        self.xoff = 0
        self.widths = []
        self.xs = []
        self.total_w = 0
        self.hover_idx = None
        self.row_rects = {}
        self.fit_cache = {}
        self.drag = None
        self.redraw_pending = False

        body = self.body
        body.bind("<Configure>", lambda e: self._schedule_relayout())
        body.bind("<Button-1>", self._on_click)
        body.bind("<Double-Button-1>", self._on_double)
        body.bind("<Button-3>", self._on_right_click)
        body.bind("<Motion>", self._on_motion)
        body.bind("<Leave>", self._on_leave)
        for canvas in (body, self.header):
            canvas.bind("<Enter>", lambda e: e.widget.bind_all("<MouseWheel>", self._on_wheel))
            canvas.bind("<Leave>", lambda e: e.widget.unbind_all("<MouseWheel>"), add="+")
        self.header.bind("<Configure>", lambda e: self._schedule_relayout())
        self.header.bind("<Motion>", self._on_head_motion)
        self.header.bind("<Button-1>", self._on_head_press)
        self.header.bind("<B1-Motion>", self._on_head_drag)
        self.header.bind("<ButtonRelease-1>", self._on_head_release)

        self.compute_layout()
        self.redraw_header()

    # ---------- 열 배치 ----------

    def _base_widths(self):
        widths = getattr(self.app, "col_widths", {})
        layout = self.theme.layout
        return [max(MIN_COL_WIDTH, int(widths.get(key, layout[key]))) for _, key, _ in COLUMNS]

    def compute_layout(self):
        """열 폭·왼쪽 x를 정한다. 끌어서 정한 열은 그 폭을 지키고, 나머지(품명·Comment)가
        남는 폭을 weight 비율로 나눠 갖는다."""
        base = self._base_widths()
        viewport = max(self.body.winfo_width(), 1)
        overridden = getattr(self.app, "col_width_overridden", set())
        flex = [i for i, (_, key, weight) in enumerate(COLUMNS) if weight > 0 and key not in overridden]
        extra = viewport - sum(base) if viewport > 1 else 0
        if extra > 0 and flex:
            weight_sum = sum(COLUMNS[i][2] for i in flex)
            given = 0
            for pos, i in enumerate(flex):
                share = extra - given if pos == len(flex) - 1 else extra * COLUMNS[i][2] // weight_sum
                base[i] += share
                given += share
        elif extra < 0 and viewport > 1:
            base = self._shrink_to_fit(base, viewport)
        self.widths = base
        self.xs = []
        x = 0
        for width in base:
            self.xs.append(x)
            x += width
        self.total_w = x
        self.xoff = max(0, min(self.xoff, self.total_w - viewport))

    @staticmethod
    def _shrink_to_fit(base, viewport):
        """창이 열 폭 합보다 좁으면 가로 스크롤 대신 모든 열을 비율로 줄인다(최소 폭은 지킨다)."""
        widths = list(base)
        for _ in range(len(widths)):
            over = sum(widths) - viewport
            if over <= 0:
                break
            room = [w - MIN_COL_WIDTH for w in widths]
            total_room = sum(room)
            if total_room <= 0:
                break
            cut = min(over, total_room)
            taken = 0
            for i, r in enumerate(room):
                part = cut - taken if i == len(room) - 1 else cut * r // total_room
                part = min(part, r)
                widths[i] -= part
                taken += part
        return widths

    def _schedule_relayout(self):
        if self.redraw_pending:
            return
        self.redraw_pending = True
        self.frame.after_idle(self.relayout)

    def relayout(self):
        """열 폭·창 크기·설정이 바뀌었을 때. 머리글과 본문을 같이 다시 그린다."""
        self.redraw_pending = False
        try:
            self.compute_layout()
            self.redraw_header()
            self.redraw_body()
        except tk.TclError:
            pass  # 화면을 다시 짓는 중에 예약이 늦게 도착한 경우

    # ---------- 머리글 ----------

    def redraw_header(self):
        theme, c = self.theme, self.theme.colors
        header = self.header
        header.delete("all")
        header.configure(bg=c["th_bg"])
        width = max(header.winfo_width(), self.total_w)
        headers = self.app.settings.get("headers", {})
        for i, (title, key, _) in enumerate(COLUMNS):
            header_key = HEADER_KEY_BY_WIDTH.get(key)
            if header_key:
                title = headers.get(header_key, title)
            x0 = self.xs[i] - self.xoff
            x1 = x0 + self.widths[i]
            if x1 < 0 or x0 > width:
                continue
            text = fit_font_text(self.font_head, title, max(10, self.widths[i] - 2 * self.pad))
            mid = self.head_h // 2 - 1
            if title == "최종단가":
                header.create_text(x1 - self.pad, mid, text=text, anchor="e", fill=c["th_fg"], font=theme.table_head)
            elif title in ("가능여부", "No", "등록일") or i == COL_CHECK:
                header.create_text((x0 + x1) // 2, mid, text=text, anchor="center", fill=c["th_fg"],
                                   font=theme.table_head)
            else:
                header.create_text(x0 + self.pad, mid, text=text, anchor="w", fill=c["th_fg"], font=theme.table_head)
            if i < len(COLUMNS) - 1:
                header.create_line(x1, 5, x1, self.head_h - 6, fill=c["checkbox_border"], tags=(f"sep{i}",))
        header.create_line(0, self.head_h - 1, width, self.head_h - 1, fill=c["th_underline"], width=2)

    def _boundary_at(self, x):
        """머리글 x 좌표가 어느 열 경계(오른쪽 끝) 근처인가. 없으면 None."""
        for i in range(len(COLUMNS) - 1):
            edge = self.xs[i] + self.widths[i] - self.xoff
            if abs(x - edge) <= GRAB:
                return i
        return None

    def _on_head_motion(self, event):
        if self.drag is not None:
            return
        self.header.configure(cursor="sb_h_double_arrow" if self._boundary_at(event.x) is not None else "")

    def _on_head_press(self, event):
        i = self._boundary_at(event.x)
        if i is None:
            return
        # 끌기 시작 때 화면에 보이는 폭을 전부 고정 폭으로 삼는다. 품명·Comment는 기본 상태에서
        # 남는 폭을 나눠 가져 설정의 폭과 실제 폭이 다르다 — 설정 폭을 기준으로 끌면 경계가
        # 튀고 엉뚱한 열이 늘어난다.
        app = self.app
        actual = {key: max(MIN_COL_WIDTH, self.widths[k]) for k, (_, key, _) in enumerate(COLUMNS)}
        app.col_widths.update(actual)
        app.col_width_overridden.update(actual)
        left_key, right_key = COLUMNS[i][1], COLUMNS[i + 1][1]
        self.drag = {"x": event.x_root, "left": app.col_widths[left_key], "right": app.col_widths[right_key],
                     "left_key": left_key, "right_key": right_key}

    def _on_head_drag(self, event):
        drag = self.drag
        if drag is None:
            return
        pair = drag["left"] + drag["right"]
        new_left = max(MIN_COL_WIDTH, min(pair - MIN_COL_WIDTH, drag["left"] + event.x_root - drag["x"]))
        self.app.col_widths[drag["left_key"]] = int(new_left)
        self.app.col_widths[drag["right_key"]] = int(pair - new_left)
        self._schedule_relayout()

    def _on_head_release(self, event):
        if self.drag is None:
            return
        self.drag = None
        self.relayout()
        _persist_column_widths(self.app)

    # ---------- 본문 ----------

    def set_rows(self, items, reset_scroll=False):
        self.items = list(items)
        self.empty = None
        if reset_scroll:
            self._set_top(0, animate=False)
        self.redraw_body()

    def set_empty(self, title, detail, reset_scroll=False):
        self.items = []
        self.empty = (title, detail)
        if reset_scroll:
            self._set_top(0, animate=False)
        self.redraw_body()

    def _fit_raw(self, font, text, max_px):
        key = (id(font), text, max_px)
        hit = self.fit_cache.get(key)
        if hit is None:
            if len(self.fit_cache) > 6000:
                self.fit_cache.clear()
            hit = self.fit_cache[key] = fit_font_text(font, text, max(10, max_px))
        return hit

    def _fit(self, font, text, width):
        return self._fit_raw(font, text, width - 2 * self.pad)

    def row_bg(self, idx, hover=False):
        c = self.theme.colors
        item = self.items[idx]
        if hover:
            return c["row_hover"]
        if item["no"] in self.app.selected_nos:
            return c["row_selected_bg"]
        if self.app.is_duplicate_item(item):
            return c["row_dup_bg"] if idx % 2 == 0 else c["row_dup_alt_bg"]
        return c["row_bg"] if idx % 2 == 0 else c["row_alt_bg"]

    def redraw_body(self):
        body, c = self.body, self.theme.colors
        body.delete("all")
        self.row_rects = {}
        self.hover_idx = None
        view_h, view_w = max(body.winfo_height(), 1), max(body.winfo_width(), 1)
        count = len(self.items)
        self.top = max(0, min(self.top, max(0, count * self.row_h - view_h)))
        self.target_top = max(0, min(self.target_top, max(0, count * self.row_h - view_h)))
        width = max(view_w, self.total_w)

        first = self.top // self.row_h
        last = min(count, (self.top + view_h) // self.row_h + 1)
        for idx in range(first, last):
            self._draw_row(idx, idx * self.row_h - self.top, width, view_w)

        if self.app.display_prefs.get("dividers", True):
            for i in range(len(COLUMNS)):
                x = self.xs[i] + self.widths[i] - self.xoff
                if 0 <= x <= view_w:
                    body.create_line(x, 0, x, view_h, fill=c["col_divider"])
        if not count and self.empty:
            title, detail = self.empty
            cx, cy = view_w // 2, min(view_h // 2, 140)
            body.create_text(cx, cy - 12, text=title, fill=c["text"], font=self.theme.table_cell_bold)
            body.create_text(cx, cy + 14, text=detail, fill=c["muted"], font=self.theme.table_cell)
        self._update_bars(view_w, view_h, count)

    def _draw_row(self, idx, y, width, view_w):
        body, c, theme = self.body, self.theme.colors, self.theme
        app, item, pad = self.app, self.items[idx], self.pad
        mid = y + self.row_h // 2
        selected = item["no"] in app.selected_nos
        duplicate = app.is_duplicate_item(item)
        self.row_rects[idx] = body.create_rectangle(0, y, width, y + self.row_h, fill=self.row_bg(idx), outline="")
        if app.display_prefs.get("dividers", True):
            body.create_line(0, y + self.row_h - 1, width, y + self.row_h - 1, fill=c["col_divider"])
        _, _, final_price = calc_row(item, app.rates)

        def cell(i):
            x0 = self.xs[i] - self.xoff
            return x0, self.widths[i], x0 + self.widths[i]

        def visible(i):
            x0, w, x1 = cell(i)
            return x1 >= 0 and x0 <= view_w

        def text_cell(i, text, font=None, fill=None, muted=False):
            if not visible(i):
                return
            x0, w, _ = cell(i)
            font = font or self.font_cell
            body.create_text(x0 + pad, mid, text=self._fit(font, text, w), anchor="w", font=font,
                             fill=fill or (c["muted"] if muted else c["text"]))

        if visible(COL_NO):
            x0, w, _ = cell(COL_NO)
            body.create_text(x0 + w // 2, mid, text=str(idx + 1), fill=c["muted"], font=theme.table_cell)

        if visible(COL_CHECK):
            x0, w, _ = cell(COL_CHECK)
            size = min(16, self.row_h - 12)
            bx, by = x0 + (w - size) // 2, mid - size // 2
            box_bg = c["accent"] if selected else c["card_alt"]
            body.create_rectangle(bx, by, bx + size, by + size, fill=box_bg,
                                  outline=c["accent"] if selected else c["checkbox_border"])
            if selected:
                body.create_line(bx + 3, by + size // 2, bx + size // 2 - 1, by + size - 4, bx + size - 3, by + 3,
                                 fill=c["bg"], width=2)

        text_cell(COL_MODEL, item["model"] or "-")
        if visible(COL_PARTNO):
            x0, w, _ = cell(COL_PARTNO)
            px = x0 + pad
            if item.get("is_new_registration"):
                bw = self.new_w
                bh = self.badge_line + 2
                body.create_rectangle(px, mid - bh // 2, px + bw, mid + bh // 2, fill=c["new_bg"], outline=c["new_border"])
                body.create_text(px + bw // 2, mid, text="NEW", fill=c["new_fg"], font=theme.badge_bold)
                px += bw + 6
            label = item["part_no"] or f"NO. {idx + 1} 미입력"
            body.create_text(px, mid, text=self._fit_raw(self.font_bold, label, x0 + w - px - pad),
                             anchor="w", font=theme.table_cell_bold,
                             fill=c["row_dup_fg"] if duplicate else c["text"])
        text_cell(COL_PARTNAME, item["part_name"] or "품명 미입력")
        text_cell(COL_COMMENT, one_line(item.get("comment", "")) or "-")
        text_cell(COL_MATERIAL, item["material"] or "-")
        text_cell(COL_HEAT, hrc_text(item) or "-")
        text_cell(COL_SIZE, item["size"] or "-")
        if visible(COL_DATE):
            x0, w, _ = cell(COL_DATE)
            body.create_text(x0 + w // 2, mid, text=self._fit(self.font_cell, item["created_at"], w),
                             font=theme.table_cell, fill=c["muted"])
        if visible(COL_STATUS):
            x0, w, _ = cell(COL_STATUS)
            status_bg, status_fg, status_border = theme.get_status_colors(item["possible"])
            label = shorten(item["possible"], 9)
            if label not in self.pill_w:
                self.pill_w[label] = self.font_badge.measure(label) + 18
            pw = min(w - 10, self.pill_w[label])
            ph = self.badge_line + 4
            cx = x0 + w // 2
            body.create_rectangle(cx - pw // 2, mid - ph // 2, cx + pw // 2, mid + ph // 2,
                                  fill=status_bg, outline=status_border)
            body.create_text(cx, mid, text=label, fill=status_fg, font=theme.badge_bold)
        if visible(COL_PRICE):
            x0, w, x1 = cell(COL_PRICE)
            body.create_text(x1 - pad, mid, text=f"{final_price:,}", anchor="e", fill=c["accent"],
                             font=theme.table_num_bold)

    def _update_bars(self, view_w, view_h, count):
        total_h = count * self.row_h
        if total_h <= view_h:
            self.vbar.set(0, 1)
        else:
            self.vbar.set(self.top / total_h, (self.top + view_h) / total_h)
        if self.total_w <= view_w:
            self.hbar.set(0, 1)
            self.hbar.grid_remove()   # 열이 다 보이면 가로 스크롤바는 숨긴다
        else:
            self.hbar.grid()
            self.hbar.set(self.xoff / self.total_w, (self.xoff + view_w) / self.total_w)

    # ---------- 스크롤 ----------

    def _max_top(self):
        return max(0, len(self.items) * self.row_h - max(self.body.winfo_height(), 1))

    def _set_top(self, value, animate=True):
        value = max(0, min(int(value), self._max_top()))
        self.target_top = value
        if animate:
            if self.anim_id is None:
                self.anim_id = self.frame.after(ANIM_MS, self._animate)
            return
        if self.anim_id is not None:
            self.frame.after_cancel(self.anim_id)
            self.anim_id = None
        if value != self.top or self.items:
            self.top = value
            self.redraw_body()

    def _animate(self):
        """휠 스크롤을 부드럽게 보간한다. 한 걸음에 남은 거리의 일부씩 다가가다 가까워지면 멈춘다."""
        self.anim_id = None
        distance = self.target_top - self.top
        if distance == 0:
            return
        step = int(distance * ANIM_EASE)
        if step == 0:
            step = 1 if distance > 0 else -1
        self.top += step
        self.redraw_body()
        if self.top != self.target_top:
            self.anim_id = self.frame.after(ANIM_MS, self._animate)

    def _on_wheel(self, event):
        direction = -1 if event.delta > 0 else 1
        base = self.target_top if self.anim_id is not None else self.top
        self._set_top(base + direction * SCROLL_ROWS * self.row_h)

    def _on_vbar(self, action, *args):
        if action == "moveto":
            self._set_top(float(args[0]) * len(self.items) * self.row_h, animate=False)
        elif action == "scroll":
            amount, unit = int(args[0]), args[1]
            step = self.row_h if unit == "units" else max(self.row_h, self.body.winfo_height() - self.row_h)
            self._set_top(self.top + amount * step, animate=False)

    def _on_hbar(self, action, *args):
        view_w = max(self.body.winfo_width(), 1)
        limit = max(0, self.total_w - view_w)
        if action == "moveto":
            self.xoff = int(max(0.0, min(1.0, float(args[0]))) * self.total_w)
        elif action == "scroll":
            amount, unit = int(args[0]), args[1]
            self.xoff += amount * (40 if unit == "units" else view_w - 40)
        self.xoff = max(0, min(self.xoff, limit))
        self.redraw_header()
        self.redraw_body()

    def scroll_to_top(self):
        self._set_top(0, animate=False)

    # ---------- 입력 ----------

    def _row_at(self, y):
        idx = (y + self.top) // self.row_h
        return idx if 0 <= idx < len(self.items) else None

    def _col_at(self, x):
        x += self.xoff
        for i in range(len(COLUMNS)):
            if self.xs[i] <= x < self.xs[i] + self.widths[i]:
                return i
        return None

    def _on_click(self, event):
        self.body.focus_set()
        idx = self._row_at(event.y)
        if idx is None:
            return
        no = self.items[idx]["no"]
        if self._col_at(event.x) == COL_CHECK or event.state & _CONTROL:
            self.app.handle_row_click(no, "toggle")
        elif event.state & _SHIFT:
            self.app.handle_row_click(no, "range")
        else:
            self.app.handle_row_click(no, "plain")

    def _on_double(self, event):
        # Tk는 빠른 두 번째 클릭에 <Button-1>이 아니라 <Double-Button-1>만 보낸다. 체크 칸은 연달아
        # 눌러도 누른 만큼 켜고 꺼져야 하므로 그냥 클릭으로 처리하고, 입력창은 열지 않는다.
        idx = self._row_at(event.y)
        if idx is None:
            return
        if self._col_at(event.x) == COL_CHECK:
            self._on_click(event)
            return
        self.app.open_popup(self.items[idx]["no"])

    def _on_right_click(self, event):
        idx = self._row_at(event.y)
        if idx is not None:
            self.app.open_row_context_menu(self.items[idx]["no"], event)

    def _on_motion(self, event):
        idx = self._row_at(event.y)
        if idx == self.hover_idx:
            return
        self._paint_hover(self.hover_idx, False)
        self.hover_idx = idx
        self._paint_hover(idx, True)

    def _on_leave(self, event):
        self._paint_hover(self.hover_idx, False)
        self.hover_idx = None

    def _paint_hover(self, idx, on):
        rect = self.row_rects.get(idx) if idx is not None else None
        if rect is not None:
            self.body.itemconfigure(rect, fill=self.row_bg(idx, hover=on))
