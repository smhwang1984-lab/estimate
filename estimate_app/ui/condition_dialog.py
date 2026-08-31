"""가공조건 산출기 창 (Mill/Lathe 보조 계산 도구, v0.1.1 신설).

`04.CSS_조건 산출기.hta`(Lathe)와 `01.견적_산출_입력.hta`(Mill 명명 대상, 실제로는
계산식이 없어 새로 설계)를 보조 기능으로 들여온 것이다. 계획을 그대로 따른다
(plan.md 2026-08-09 v0.1.1 항목):

    - 견적 프로그램이 주인이고 계산기가 종속 도구다. 현황판에서 카드를 1건 골라 두고
      열면 그 카드의 Material·Size를 읽어 미리 채운다(카드 데이터는 절대 고치지 않는다
      -- 결과를 카드로 되돌리는 길이 아예 없다, 사용자 결정).
    - 색·글꼴·위젯은 04.hta를 베끼지 않고 지금 앱의 테마(theme.py)를 그대로 쓴다.
      레이아웃(좌 입력 / 우 결과)만 04.hta를 따른다.
    - 현황판에서 열면 모달이 아니다(카드를 계속 바꿔 고를 수 있어야 한다). 카드 팝업
      Size 섹션에서 열면 팝업이 이미 grab_set() 중이므로 이 창이 grab을 넘겨받았다가
      닫을 때 돌려준다.

계산 자체는 core/machining.py(calc_lathe/calc_mill)에 있다 -- 여기는 화면만 맡는다.
"""

import tkinter as tk
from tkinter import ttk

from ..core import machining as mc
from ..core import settings as settings_store
from ..core.model import parse_number, parse_size
from .widgets import numeric_entry

MILL = "Mill"
LATHE = "Lathe"
SHAPE_BLOCK = "블록"
SHAPE_ROD = "로드"

# 04.hta 정적 HTML 기본값(재질 추천값이 아니라 화면에 처음부터 박혀 있던 숫자다 --
# initApp()이 applyRecommendation()을 부르지 않고 doCalc()만 부르므로, 처음 열었을 때는
# 이 값이 그대로 보인다. 이식 원칙(개조하지 않는다)에 따라 그대로 옮겼다).
LATHE_DEFAULTS = {"d_max": "100", "d_min": "50", "v": "198", "g50": "2500",
                  "feed": "0.23", "ap": "2.3", "length": "100"}


def _status_for_percent(pct):
    """부하율(%) -> 현황판 가능여부와 같은 3단계. 04.hta는 4단계(여유/적정/주의/과부하)지만
    theme.get_status_colors()가 3단계(가능/검토필요/불가)만 있어 경계를 다시 잡았다
    (80%/50% -- 04.hta의 '설비 부하율 판정' 80% 기준을 위험 경계로 그대로 쓰고, 중간에
    한 단계를 더 두었다). 색만 다르지 원래 부하율 숫자는 그대로 보여 준다."""
    if pct >= 80:
        return "불가"
    if pct >= 50:
        return "검토필요"
    return "가능"


def _ensure_status_styles(app):
    """부하율 배지용 스타일 3종을 한 번만 등록한다(현황판 가능여부 배지와 같은 색)."""
    style = ttk.Style()
    for status in ("가능", "검토필요", "불가"):
        bg, fg, _border = app.theme.get_status_colors(status)
        style.configure(f"Load{status}.TLabel", background=bg, foreground=fg,
                        font=app.theme.value_num, padding=(6, 2))


def _rehome_grab(dialog, popup):
    """이 산출기 창의 grab을 누구에게서 받아 누구에게 돌려줄지 정리한다.

    현황판에서 열었으면 popup=None -- grab을 아예 잡지 않는다(카드를 계속 바꿔 골라야
    하므로). 카드 팝업에서 열었으면 그 팝업의 grab을 넘겨받고, 닫을 때 되돌려준다.
    """
    previous_popup = getattr(dialog, "_owner_popup", None)
    if previous_popup is not None and previous_popup is not popup:
        try:
            if previous_popup.winfo_exists():
                previous_popup.grab_set()
        except tk.TclError:
            pass
    dialog._owner_popup = popup
    if popup is not None:
        try:
            popup.grab_release()
        except tk.TclError:
            pass
        dialog.grab_set()
    else:
        try:
            dialog.grab_release()
        except tk.TclError:
            pass


def _card_note_text(item, matched_name, table_label):
    if item is None:
        return ""
    material = str(item.get("material", "")).strip() or "(없음)"
    if matched_name:
        return f"카드 Material '{material}' -> {table_label} 재질표의 '{matched_name}'로 자동 매칭했습니다."
    return f"카드 Material '{material}'을(를) {table_label} 재질표에서 찾지 못했습니다. 아래에서 직접 골라 주세요."


# ---------- Lathe 패널 ----------

def _build_lathe_panel(app, parent):
    panel = ttk.Frame(parent)
    panel.columnconfigure(0, weight=1, minsize=460)
    panel.columnconfigure(1, weight=1, minsize=420)

    left = ttk.LabelFrame(panel, text="Lathe 입력", padding=10)
    left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
    left.columnconfigure(1, weight=1)

    materials = app.settings.get("lathe_materials", [])
    machine = app.settings.get("lathe_machine", settings_store.DEFAULT_LATHE_MACHINE)
    base_power = machine.get("power", settings_store.DEFAULT_LATHE_MACHINE["power"])
    machine_max_rpm = machine.get("max_rpm", settings_store.DEFAULT_LATHE_MACHINE["max_rpm"])

    ttk.Label(left, text=f"장비: {machine.get('name', '')} "
                          f"({base_power:g}kW / {machine_max_rpm:g}RPM)",
              style="Muted.TLabel").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

    material_var = tk.StringVar()
    note_var = tk.StringVar()
    scale_note_var = tk.StringVar()
    ttk.Label(left, text="재질").grid(row=1, column=0, sticky="e", padx=6, pady=4)
    material_combo = ttk.Combobox(left, textvariable=material_var, state="readonly",
                                  values=[row["name"] for row in materials], width=28)
    material_combo.grid(row=1, column=1, sticky="ew", padx=6, pady=4)
    ttk.Label(left, textvariable=note_var, style="Muted.TLabel", wraplength=380,
              justify="left").grid(row=2, column=0, columnspan=2, sticky="w", padx=6)

    fields = {}
    field_rows = [
        ("d_max", "소재 최대 직경 D_max (mm)"), ("d_min", "가공 목표 직경 D_min (mm)"),
        ("v", "절삭 속도 V (m/min)"), ("g50", "G50 제한 최고 RPM"),
        ("feed", "회전당 이송 F (mm/rev)"), ("ap", "반경 기준 절입량 Ap (mm)"),
        ("length", "Z축 총 가공 길이 L (mm)"), ("max_power", "설비 허용 동력 (kW)"),
    ]
    for idx, (key, label) in enumerate(field_rows):
        row = idx + 3
        ttk.Label(left, text=label).grid(row=row, column=0, sticky="e", padx=6, pady=4)
        fields[key] = tk.StringVar()
        numeric_entry(left, fields[key], width=14).grid(row=row, column=1, sticky="ew", padx=6, pady=4)
    for key, value in LATHE_DEFAULTS.items():
        fields[key].set(value)
    fields["max_power"].set(f"{base_power:g}")
    dmax_dmin_warn_row = len(field_rows) + 3
    dmax_warn_var = tk.StringVar()
    ttk.Label(left, textvariable=dmax_warn_var, style="Muted.TLabel", wraplength=380,
              justify="left").grid(row=dmax_dmin_warn_row, column=0, columnspan=2, sticky="w", padx=6, pady=(4, 0))
    ttk.Label(left, textvariable=scale_note_var, style="Muted.TLabel", wraplength=380,
              justify="left").grid(row=dmax_dmin_warn_row + 1, column=0, columnspan=2, sticky="w", padx=6)

    right = ttk.LabelFrame(panel, text="Lathe 결과", padding=10)
    right.grid(row=0, column=1, sticky="nsew")
    right.columnconfigure(1, weight=1)

    insert_var = tk.StringVar()
    ttk.Label(right, textvariable=insert_var, style="Value.TLabel", wraplength=380,
              justify="left").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

    result_vars = {}
    result_rows = [
        ("rpm", "주축 회전수 (min~max)"), ("feed_min", "분당 이송 Vf"),
        ("mrr", "칩 배출량 MRR"), ("force_kg", "주 절삭력 Fc"),
        ("total_vol", "총 제거 체적"), ("passes", "가공 패스 수"),
        ("power_kw", "절삭 동력 Pc"), ("sfm", "SFM"),
        ("total_kwh", "소비 전력"),
    ]
    for idx, (key, label) in enumerate(result_rows):
        ttk.Label(right, text=label, style="Muted.TLabel").grid(row=idx + 1, column=0, sticky="w", padx=(0, 10), pady=3)
        result_vars[key] = tk.StringVar(value="-")
        ttk.Label(right, textvariable=result_vars[key], style="Value.TLabel").grid(
            row=idx + 1, column=1, sticky="e", pady=3)

    load_row = len(result_rows) + 1
    ttk.Label(right, text="설비 부하율", style="Muted.TLabel").grid(row=load_row, column=0, sticky="w", padx=(0, 10), pady=3)
    load_label = ttk.Label(right, text="-")
    load_label.grid(row=load_row, column=1, sticky="e", pady=3)
    ttk.Label(right, text="스핀들 부하율", style="Muted.TLabel").grid(row=load_row + 1, column=0, sticky="w", padx=(0, 10), pady=3)
    spindle_label = ttk.Label(right, text="-")
    spindle_label.grid(row=load_row + 1, column=1, sticky="e", pady=3)

    time_row = load_row + 2
    ttk.Separator(right, orient="horizontal").grid(row=time_row, column=0, columnspan=2, sticky="ew", pady=8)
    ttk.Label(right, text="총 예측 가공 시간(1개 기준)", style="Muted.TLabel").grid(
        row=time_row + 1, column=0, columnspan=2, sticky="w")
    time_var = tk.StringVar(value="-")
    ttk.Label(right, textvariable=time_var, style="Value.TLabel").grid(
        row=time_row + 2, column=0, columnspan=2, sticky="w")

    def find_material_row(name):
        for row in materials:
            if row["name"] == name:
                return row
        return None

    def apply_recommendation():
        row = find_material_row(material_var.get())
        if not row:
            return
        max_power = parse_number(fields["max_power"].get()) or base_power
        rec = mc.apply_lathe_recommendation(row, max_power, base_power, machine_max_rpm)
        fields["v"].set(f"{rec['v']:g}")
        fields["feed"].set(f"{rec['f']:g}")
        fields["ap"].set(f"{rec['ap']:g}")
        fields["g50"].set(f"{rec['g50']:g}")
        insert = row.get("insert_grade")
        if insert:
            insert_var.set(f"추천 인서트 CNMG120408  {insert}  |  {row.get('insert_coat', '')}\n"
                           f"{row.get('insert_iso', '')}  |  {row.get('insert_desc', '')}")
        else:
            insert_var.set("")
        if abs(rec["power_scale"] - 1.0) > 0.02:
            scale_note_var.set(f"동력 스케일 x{rec['power_scale']:.2f} 적용 -> "
                               f"Ap {rec['ap']:g}mm, F {rec['f']:g}mm/rev")
        else:
            scale_note_var.set("")
        recompute()

    material_combo.bind("<<ComboboxSelected>>", lambda event: apply_recommendation())

    def recompute(*_args):
        d_max = parse_number(fields["d_max"].get()) or 0.0
        d_min = parse_number(fields["d_min"].get()) or 0.0
        v = parse_number(fields["v"].get()) or 0.0
        g50 = parse_number(fields["g50"].get()) or 0.0
        feed = parse_number(fields["feed"].get()) or 0.0
        ap = parse_number(fields["ap"].get()) or 0.0
        length = parse_number(fields["length"].get()) or 0.0
        max_power = parse_number(fields["max_power"].get()) or 0.0
        row = find_material_row(material_var.get())
        kc = row["kc"] if row else 0.0

        result = mc.calc_lathe(kc, d_max, d_min, v, g50, feed, ap, length, max_power, base_power)
        dmax_warn_var.set("D_max가 D_min보다 작습니다 -- 두 값을 확인해 주세요."
                          if result["dmax_lt_dmin"] else "")
        result_vars["rpm"].set(f"{round(result['min_rpm'])} ~ {round(result['max_rpm'])} RPM")
        result_vars["feed_min"].set(f"{round(result['feed_min'])} mm/min")
        result_vars["mrr"].set(f"{result['mrr']:.1f} cm³/min")
        result_vars["force_kg"].set(f"{round(result['force_kg'])} kgf")
        result_vars["total_vol"].set(f"{result['total_vol']:.1f} cm³")
        result_vars["passes"].set(f"{result['passes']} 회" + ("  [단면 특수공정]" if result["face_only"] else ""))
        result_vars["power_kw"].set(f"{result['power_kw']:.2f} kW")
        result_vars["sfm"].set(f"{result['sfm']} ft/min")
        result_vars["total_kwh"].set(f"{result['total_kwh']:.3f} kWh")

        load_status = _status_for_percent(result["load_rate"])
        load_label.configure(text=f"{result['load_rate']:.1f} %", style=f"Load{load_status}.TLabel")
        spindle_status = _status_for_percent(result["spindle_load"])
        spindle_label.configure(text=f"{result['spindle_load']:.1f} %", style=f"Load{spindle_status}.TLabel")

        text = mc.seconds_to_text(result["total_sec"])
        hours = mc.seconds_to_hours(result["total_sec"])
        time_var.set(f"{text}  ({hours:g} h)")

    for var in fields.values():
        var.trace_add("write", recompute)

    def apply_item(item):
        note_var.set("")
        if item is None:
            return
        shape, dims = parse_size(item.get("size", ""))
        if shape == "rod":
            if "d" in dims:
                fields["d_max"].set(dims["d"])
            if "l" in dims:
                fields["length"].set(dims["l"])
        row = settings_store.resolve_machining_material(item.get("material", ""), materials)
        note_var.set(_card_note_text(item, row["name"] if row else None, "Lathe"))
        if row:
            material_var.set(row["name"])
            apply_recommendation()
        else:
            recompute()

    recompute()
    return panel, apply_item


# ---------- Mill 패널 ----------

def _build_mill_panel(app, parent):
    panel = ttk.Frame(parent)
    panel.columnconfigure(0, weight=1, minsize=460)
    panel.columnconfigure(1, weight=1, minsize=420)

    left = ttk.LabelFrame(panel, text="Mill 입력", padding=10)
    left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
    left.columnconfigure(1, weight=1)

    materials = app.settings.get("mill_materials", [])
    machine = app.settings.get("mill_machine", settings_store.DEFAULT_MILL_MACHINE)
    base_power = machine.get("power", settings_store.DEFAULT_MILL_MACHINE["power"])
    machine_max_rpm = machine.get("max_rpm", settings_store.DEFAULT_MILL_MACHINE["max_rpm"])
    machine_name = machine.get("name", "") or "(미지정)"

    ttk.Label(left, text=f"장비: {machine_name} ({base_power:g}kW / {machine_max_rpm:g}RPM)",
              style="Muted.TLabel").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 2))
    ttk.Label(left, text="재질값은 잠정치입니다. 설정 > 가공 조건에서 실측치로 고칠 수 있습니다.",
              style="Muted.TLabel", wraplength=380, justify="left").grid(
        row=1, column=0, columnspan=2, sticky="w", pady=(0, 8))

    material_var = tk.StringVar()
    note_var = tk.StringVar()
    ttk.Label(left, text="재질").grid(row=2, column=0, sticky="e", padx=6, pady=4)
    material_combo = ttk.Combobox(left, textvariable=material_var, state="readonly",
                                  values=[row["name"] for row in materials], width=28)
    material_combo.grid(row=2, column=1, sticky="ew", padx=6, pady=4)
    ttk.Label(left, textvariable=note_var, style="Muted.TLabel", wraplength=380,
              justify="left").grid(row=3, column=0, columnspan=2, sticky="w", padx=6)

    tool_fields = {}
    tool_rows = [
        ("tool_d", "공구경 D (mm)"), ("flutes", "날수 Z"), ("vc", "절삭 속도 Vc (m/min)"),
        ("fz", "날당 이송 fz (mm/날)"), ("ap", "축방향 절입 Ap (mm)"), ("ae", "반경방향 절입 Ae (mm)"),
        ("max_rpm", "최고 RPM"), ("max_power", "설비 허용 동력 (kW)"),
    ]
    for idx, (key, label) in enumerate(tool_rows):
        row = idx + 4
        ttk.Label(left, text=label).grid(row=row, column=0, sticky="e", padx=6, pady=4)
        tool_fields[key] = tk.StringVar()
        numeric_entry(left, tool_fields[key], width=14).grid(row=row, column=1, sticky="ew", padx=6, pady=4)
    tool_fields["tool_d"].set("10")
    tool_fields["flutes"].set("4")
    tool_fields["max_rpm"].set(f"{machine_max_rpm:g}")
    tool_fields["max_power"].set(f"{base_power:g}")

    shape_row = len(tool_rows) + 4
    shape_var = tk.StringVar(value=SHAPE_BLOCK)
    ttk.Label(left, text="형상 선택").grid(row=shape_row, column=0, sticky="e", padx=6, pady=(10, 4))
    shape_frame = ttk.Frame(left)
    shape_frame.grid(row=shape_row, column=1, sticky="w", pady=(10, 4))
    ttk.Radiobutton(shape_frame, text="블록 (T x W x L)", value=SHAPE_BLOCK, variable=shape_var).pack(side=tk.LEFT, padx=(0, 8))
    ttk.Radiobutton(shape_frame, text="로드/원봉 (D x L)", value=SHAPE_ROD, variable=shape_var).pack(side=tk.LEFT)

    dims_frame = ttk.Frame(left)
    dims_frame.grid(row=shape_row + 1, column=0, columnspan=2, sticky="ew", padx=6, pady=4)

    dims_vars = {"stock": {}, "target": {}}

    def render_dims(*_args):
        for widget in dims_frame.winfo_children():
            widget.destroy()
        dims_vars["stock"].clear()
        dims_vars["target"].clear()
        shape = shape_var.get()
        if shape == SHAPE_BLOCK:
            keys, labels = ["t", "w", "l"], ["T (두께)", "W (폭)", "L (길이)"]
        else:
            keys, labels = ["d", "l"], ["D (외경/Ø)", "L (길이)"]
        ttk.Label(dims_frame, text="소재", style="Muted.TLabel").grid(row=0, column=0, sticky="w", pady=(4, 2))
        for col, (key, label) in enumerate(zip(keys, labels)):
            ttk.Label(dims_frame, text=label).grid(row=0, column=col * 2 + 1, padx=3)
            var = tk.StringVar()
            dims_vars["stock"][key] = var
            numeric_entry(dims_frame, var, width=8).grid(row=0, column=col * 2 + 2, padx=3)
            var.trace_add("write", recompute)
        target_keys = keys if shape == SHAPE_BLOCK else ["d"]
        target_labels = labels if shape == SHAPE_BLOCK else ["D (목표 외경/Ø)"]
        ttk.Label(dims_frame, text="목표", style="Muted.TLabel").grid(row=1, column=0, sticky="w", pady=(4, 2))
        for col, (key, label) in enumerate(zip(target_keys, target_labels)):
            ttk.Label(dims_frame, text=label).grid(row=1, column=col * 2 + 1, padx=3)
            var = tk.StringVar()
            dims_vars["target"][key] = var
            numeric_entry(dims_frame, var, width=8).grid(row=1, column=col * 2 + 2, padx=3)
            var.trace_add("write", recompute)
        if shape == SHAPE_ROD:
            ttk.Label(dims_frame, text="로드는 목표 지름만 받습니다(길이는 소재와 같다고 봅니다).",
                      style="Muted.TLabel", wraplength=380, justify="left").grid(
                row=2, column=0, columnspan=7, sticky="w", pady=(4, 0))

    right = ttk.LabelFrame(panel, text="Mill 결과", padding=10)
    right.grid(row=0, column=1, sticky="nsew")
    right.columnconfigure(1, weight=1)

    result_vars = {}
    result_rows = [
        ("rpm", "주축 회전수 n"), ("feed_min", "분당 이송 Vf"),
        ("mrr", "칩 배출량 Q"), ("power_kw", "절삭 동력 Pc"), ("volume", "제거 체적"),
    ]
    for idx, (key, label) in enumerate(result_rows):
        ttk.Label(right, text=label, style="Muted.TLabel").grid(row=idx, column=0, sticky="w", padx=(0, 10), pady=3)
        result_vars[key] = tk.StringVar(value="-")
        ttk.Label(right, textvariable=result_vars[key], style="Value.TLabel").grid(
            row=idx, column=1, sticky="e", pady=3)

    load_row = len(result_rows)
    ttk.Label(right, text="설비 부하율", style="Muted.TLabel").grid(row=load_row, column=0, sticky="w", padx=(0, 10), pady=3)
    load_label = ttk.Label(right, text="-")
    load_label.grid(row=load_row, column=1, sticky="e", pady=3)
    ttk.Label(right, text="스핀들 부하율", style="Muted.TLabel").grid(row=load_row + 1, column=0, sticky="w", padx=(0, 10), pady=3)
    spindle_label = ttk.Label(right, text="-")
    spindle_label.grid(row=load_row + 1, column=1, sticky="e", pady=3)

    time_row = load_row + 2
    ttk.Separator(right, orient="horizontal").grid(row=time_row, column=0, columnspan=2, sticky="ew", pady=8)
    ttk.Label(right, text="총 예측 가공 시간(1개 기준)", style="Muted.TLabel").grid(
        row=time_row + 1, column=0, columnspan=2, sticky="w")
    time_var = tk.StringVar(value="-")
    ttk.Label(right, textvariable=time_var, style="Value.TLabel").grid(
        row=time_row + 2, column=0, columnspan=2, sticky="w")

    def find_material_row(name):
        for row in materials:
            if row["name"] == name:
                return row
        return None

    def apply_material_fill():
        row = find_material_row(material_var.get())
        if not row:
            return
        tool_fields["vc"].set(f"{row['vc']:g}")
        tool_fields["fz"].set(f"{row['fz']:g}")
        tool_fields["ap"].set(f"{row['ap']:g}")
        tool_fields["ae"].set(f"{row['ae']:g}")
        recompute()

    material_combo.bind("<<ComboboxSelected>>", lambda event: apply_material_fill())

    def dim_value(store, key):
        return parse_number(store.get(key, tk.StringVar()).get()) or 0.0

    def recompute(*_args):
        tool_d = parse_number(tool_fields["tool_d"].get()) or 0.0
        flutes = parse_number(tool_fields["flutes"].get()) or 0.0
        vc = parse_number(tool_fields["vc"].get()) or 0.0
        fz = parse_number(tool_fields["fz"].get()) or 0.0
        ap = parse_number(tool_fields["ap"].get()) or 0.0
        ae = parse_number(tool_fields["ae"].get()) or 0.0
        max_rpm = parse_number(tool_fields["max_rpm"].get()) or 0.0
        max_power = parse_number(tool_fields["max_power"].get()) or 0.0
        row = find_material_row(material_var.get())
        kc = row["kc"] if row else 0.0

        shape = "block" if shape_var.get() == SHAPE_BLOCK else "rod"
        stock = {key: dim_value(dims_vars["stock"], key) for key in dims_vars["stock"]}
        target = {key: dim_value(dims_vars["target"], key) for key in dims_vars["target"]}

        result = mc.calc_mill(kc, tool_d, flutes, vc, fz, ap, ae, max_rpm, shape, stock, target,
                              max_power, base_power)
        result_vars["rpm"].set(f"{round(result['rpm'])} RPM")
        result_vars["feed_min"].set(f"{round(result['feed_min'])} mm/min")
        result_vars["mrr"].set(f"{result['mrr']:.2f} cm³/min")
        result_vars["power_kw"].set(f"{result['power_kw']:.3f} kW")
        result_vars["volume"].set(f"{result['volume']:.1f} cm³")

        load_status = _status_for_percent(result["load_rate"])
        load_label.configure(text=f"{result['load_rate']:.1f} %", style=f"Load{load_status}.TLabel")
        spindle_status = _status_for_percent(result["spindle_load"])
        spindle_label.configure(text=f"{result['spindle_load']:.1f} %", style=f"Load{spindle_status}.TLabel")

        text = mc.seconds_to_text(result["total_sec"])
        hours = mc.seconds_to_hours(result["total_sec"])
        time_var.set(f"{text}  ({hours:g} h)")

    shape_var.trace_add("write", render_dims)
    for var in tool_fields.values():
        var.trace_add("write", recompute)
    render_dims()

    def apply_item(item):
        note_var.set("")
        if item is None:
            return
        shape, dims = parse_size(item.get("size", ""))
        if shape in ("block", "rod"):
            shape_var.set(SHAPE_BLOCK if shape == "block" else SHAPE_ROD)
            render_dims()
            for key, value in dims.items():
                if key in dims_vars["stock"]:
                    dims_vars["stock"][key].set(value)
        row = settings_store.resolve_machining_material(item.get("material", ""), materials)
        note_var.set(_card_note_text(item, row["name"] if row else None, "Mill"))
        if row:
            material_var.set(row["name"])
            apply_material_fill()
        else:
            recompute()

    return panel, apply_item


# ---------- 창 ----------

def open_condition_dialog(app, item=None, popup=None):
    """산출기 창을 연다.

    item   카드에서 열었을 때 그 카드(dict). None이면 빈 채로 연다.
    popup  카드 팝업(Toplevel)에서 열었으면 그 팝업 -- grab을 넘겨받았다가 닫을 때
           돌려준다. 현황판에서 열었으면 None -- 이 창은 모달이 되지 않는다.
    """
    _ensure_status_styles(app)
    existing = getattr(app, "condition_window", None)
    if existing is not None and existing.winfo_exists():
        _rehome_grab(existing, popup)
        existing.lift()
        existing.focus_force()
        existing._apply_item(item)
        return

    dialog = tk.Toplevel(app.root)
    app.condition_window = dialog
    dialog.title("가공조건 산출기")
    width = min(1100, max(880, dialog.winfo_screenwidth() - 120))
    height = min(760, max(560, dialog.winfo_screenheight() - 140))
    dialog.geometry(f"{width}x{height}"
                    f"+{max(0, (dialog.winfo_screenwidth() - width) // 2)}"
                    f"+{max(0, (dialog.winfo_screenheight() - height) // 4)}")
    dialog.minsize(820, 560)
    dialog.configure(bg=app.theme.color("bg"))
    dialog.transient(app.root)

    def on_destroy(event):
        if event.widget is not dialog:
            return
        app.condition_window = None
        owner = getattr(dialog, "_owner_popup", None)
        if owner is not None:
            try:
                if owner.winfo_exists():
                    owner.grab_set()
            except tk.TclError:
                pass

    dialog.bind("<Destroy>", on_destroy)

    c = app.theme.colors
    outer = ttk.Frame(dialog, padding=14)
    outer.pack(fill=tk.BOTH, expand=True)

    top = ttk.Frame(outer)
    top.pack(side=tk.TOP, fill=tk.X, pady=(0, 10))
    ttk.Label(top, text="가공 계열", style="Head.TLabel").pack(side=tk.LEFT, padx=(0, 10))
    series_var = tk.StringVar(value=MILL)
    ttk.Radiobutton(top, text="Mill", value=MILL, variable=series_var).pack(side=tk.LEFT, padx=6)
    ttk.Radiobutton(top, text="Lathe", value=LATHE, variable=series_var).pack(side=tk.LEFT, padx=6)

    # 입력 항목이 창 높이보다 길어질 수 있어(Mill의 목표 치수 줄까지 포함하면 특히) 세로
    # 스크롤을 둔다 -- dashboard.py의 row_canvas/row_container와 같은 구조다. 저장 버튼
    # 줄(bottom)은 스크롤 영역보다 먼저 아래에 붙잡아 둬야 창이 작아도 항상 보인다
    # (settings_dialog.py의 같은 이유와 같은 순서).
    bottom = ttk.Frame(outer, padding=(0, 10, 0, 0))
    bottom.pack(side=tk.BOTTOM, fill=tk.X)

    scroll_area = tk.Frame(outer, bg=c["bg"])
    scroll_area.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
    body_canvas = tk.Canvas(scroll_area, bg=c["bg"], highlightthickness=0)
    body_scroll = ttk.Scrollbar(scroll_area, orient=tk.VERTICAL, command=body_canvas.yview)
    body_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    body_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    body_canvas.configure(yscrollcommand=body_scroll.set)

    body = ttk.Frame(body_canvas)
    body_window = body_canvas.create_window((0, 0), window=body, anchor="nw")
    body.columnconfigure(0, weight=1)

    def _sync_scrollregion(_event=None):
        body_canvas.configure(scrollregion=body_canvas.bbox("all"))
        body_canvas.itemconfigure(body_window, width=body_canvas.winfo_width())

    body.bind("<Configure>", _sync_scrollregion)
    body_canvas.bind("<Configure>", _sync_scrollregion)
    body_canvas.bind("<Enter>", lambda e: body_canvas.bind_all(
        "<MouseWheel>", lambda ev: body_canvas.yview_scroll(int(-1 * (ev.delta / 120)), "units")))
    body_canvas.bind("<Leave>", lambda e: body_canvas.unbind_all("<MouseWheel>"))

    mill_panel, mill_apply_item = _build_mill_panel(app, body)
    lathe_panel, lathe_apply_item = _build_lathe_panel(app, body)

    def on_series_change(*_args):
        # Mill/Lathe 두 패널의 세로 길이가 서로 다르다(Mill이 목표 치수 줄까지 있어 더
        # 길다). tkraise()로 앞뒤만 바꾸면 짧은 쪽 아래로 긴 쪽의 나머지가 그대로
        # 비쳐 보인다(실제로 캡처해서 확인한 문제) -- grid_remove()로 아예 빼야 한다.
        if series_var.get() == MILL:
            lathe_panel.grid_remove()
            mill_panel.grid(row=0, column=0, sticky="new")
        else:
            mill_panel.grid_remove()
            lathe_panel.grid(row=0, column=0, sticky="new")
        body_canvas.yview_moveto(0)
        dialog.after_idle(_sync_scrollregion)

    series_var.trace_add("write", on_series_change)
    on_series_change()

    def apply_item(new_item):
        mill_apply_item(new_item)
        lathe_apply_item(new_item)

    dialog._apply_item = apply_item
    apply_item(item)

    ttk.Label(bottom, text="이 창의 계산 결과는 카드에 저장되지 않습니다. 참고용입니다.",
              style="Muted.TLabel").pack(side=tk.LEFT)
    ttk.Button(bottom, text="닫기", command=dialog.destroy).pack(side=tk.RIGHT)
    dialog.bind("<Escape>", lambda event: dialog.destroy())

    _rehome_grab(dialog, popup)
