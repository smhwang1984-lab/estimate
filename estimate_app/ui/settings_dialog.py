"""설정창(v0.0.9 신설, 요청 6번).

여기서 고친 값은 저장하는 순간 전체에 적용된다.

    공정 단가      카드 팝업에서는 고칠 수 없는 고정값으로 쓰인다(요청 6-2).
    Material       카드 입력창의 선택 목록. 여기서 추가·삭제한다(요청 6-3).
    회사 / 양식    기계 시트 푸터의 회사명·작성자와, 견적서 시트 맨 위 문구(요청 6-4, 7-1).
    소재 비중      v0.1.0 신설. 카드에서 무게를 계산할 때 쓰는 소재별 비중(요청 4-2).

값은 `%LOCALAPPDATA%\\MachineEstimate\\settings.json`에 저장한다(core/settings.py).
"""

import tkinter as tk
from tkinter import messagebox, ttk

from ..core import config, settings as settings_store
from ..core.model import parse_number

# (설정 키, 화면 라벨, 도움말). 견적서 상단은 라벨 문구를 코드가 붙이므로 알맹이만 입력받는다.
CLIENT_FIELDS = [
    ("name", "받는 회사명", "'○○ 귀중'"),
    ("manager", "담당자", "'담당자 : ○○'"),
    ("dept", "부서", "'부   서 : ○○'"),
    ("project", "사업명", "'사업명 : ○○'"),
]
SUPPLIER_FIELDS = [
    ("ceo", "대표자", "'대표자 : ○○    (인)'"),
    ("biz_no", "사업자등록번호", ""),
    ("address", "주소", ""),
    ("phone", "전화번호", ""),
    ("contact", "담당자", "우리 쪽 담당자"),
]
COMPANY_FIELDS = [
    ("name", "회사명", "예: (주)텍스타"),
    ("writer_title", "직위", "예: 생산부장"),
    ("writer_name", "작성자", "예: 황성문"),
]


def _labeled_entries(parent, fields, values, width=34):
    """(키 -> StringVar) 사전을 만들면서 라벨 + 입력칸을 세로로 쌓는다."""
    variables = {}
    for row, (key, label, hint) in enumerate(fields):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="e", padx=(6, 8), pady=5)
        variables[key] = tk.StringVar(value=str(values.get(key, "")))
        ttk.Entry(parent, textvariable=variables[key], width=width).grid(
            row=row, column=1, sticky="ew", padx=6, pady=5)
        if hint:
            ttk.Label(parent, text=hint, style="Muted.TLabel").grid(
                row=row, column=2, sticky="w", padx=6, pady=5)
    parent.columnconfigure(1, weight=1)
    return variables


def _build_machining_material_table(parent, dialog, numeric_fields, numeric_labels, rows, has_insert):
    """가공조건 재질표(Lathe/Mill 공용) 편집기(v0.1.1). 소재 비중 탭과 같은 트리뷰 +
    추가/수정 폼 구조를 재질표에 맞게 넓힌 것이다.

    반환: get_rows() -- 저장 시점에 트리뷰 내용을 core/settings.py가 기대하는 dict 목록으로
    바꿔 주는 함수. 인서트 상세(coat/iso/desc)는 트리뷰 칸에는 안 보이지만 `extra_by_name`에
    같이 지켜지며 get_rows()가 합쳐 돌려준다.
    """
    extra_by_name = {row["name"]: {k: row.get(k, "") for k in
                                   ("insert_coat", "insert_iso", "insert_desc")}
                     for row in rows} if has_insert else {}

    list_row = ttk.Frame(parent)
    list_row.pack(fill=tk.BOTH, expand=True)
    scrollbar = ttk.Scrollbar(list_row, orient=tk.VERTICAL)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    columns = ["name", "keywords"] + numeric_fields + (["insert_grade"] if has_insert else [])
    tree = ttk.Treeview(list_row, columns=columns, show="headings", selectmode="browse",
                        yscrollcommand=scrollbar.set, height=9)
    headers = {"name": "이름", "keywords": "키워드(콤마로 구분)", "insert_grade": "추천 인서트"}
    headers.update(numeric_labels)
    widths = {"name": 190, "keywords": 190, "insert_grade": 90}
    for field in numeric_fields:
        widths.setdefault(field, 70)
    for col in columns:
        tree.heading(col, text=headers.get(col, col))
        tree.column(col, width=widths.get(col, 70), anchor="w" if col in ("name", "keywords") else "e")
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.configure(command=tree.yview)

    def row_values(row):
        values = [row["name"], ",".join(row.get("keywords", []))]
        values += [row.get(field, 0) for field in numeric_fields]
        if has_insert:
            values.append(row.get("insert_grade", ""))
        return values

    for row in rows:
        tree.insert("", tk.END, iid=row["name"], values=row_values(row))

    edit_box = ttk.Frame(parent, padding=(0, 8, 0, 0))
    edit_box.pack(fill=tk.X)
    edit_vars = {"name": tk.StringVar(), "keywords": tk.StringVar()}
    for field in numeric_fields:
        edit_vars[field] = tk.StringVar()
    if has_insert:
        for field in ("insert_grade", "insert_coat", "insert_iso", "insert_desc"):
            edit_vars[field] = tk.StringVar()

    line1 = ttk.Frame(edit_box)
    line1.pack(fill=tk.X)
    ttk.Label(line1, text="이름").pack(side=tk.LEFT)
    ttk.Entry(line1, textvariable=edit_vars["name"], width=20).pack(side=tk.LEFT, padx=(4, 12))
    ttk.Label(line1, text="키워드").pack(side=tk.LEFT)
    ttk.Entry(line1, textvariable=edit_vars["keywords"], width=20).pack(side=tk.LEFT, padx=(4, 12))
    for field in numeric_fields:
        ttk.Label(line1, text=numeric_labels.get(field, field)).pack(side=tk.LEFT)
        ttk.Entry(line1, textvariable=edit_vars[field], width=8).pack(side=tk.LEFT, padx=(4, 12))

    if has_insert:
        line2 = ttk.Frame(edit_box, padding=(0, 6, 0, 0))
        line2.pack(fill=tk.X)
        insert_fields = [("insert_grade", "인서트 등급", 12), ("insert_coat", "코팅", 22),
                         ("insert_iso", "ISO", 14), ("insert_desc", "설명", 26)]
        for field, label, width in insert_fields:
            ttk.Label(line2, text=label).pack(side=tk.LEFT)
            ttk.Entry(line2, textvariable=edit_vars[field], width=width).pack(side=tk.LEFT, padx=(4, 12))

    def load_selected():
        selected = tree.selection()
        if not selected:
            messagebox.showinfo("선택 없음", "수정할 재질을 목록에서 고르세요.", parent=dialog)
            return
        iid = selected[0]
        values = tree.item(iid, "values")
        for offset, col in enumerate(columns):
            if col in ("name", "keywords") or col in numeric_fields:
                edit_vars[col].set(values[offset])
        if has_insert:
            for field in ("insert_coat", "insert_iso", "insert_desc"):
                edit_vars[field].set(extra_by_name.get(iid, {}).get(field, ""))

    def add_or_update():
        name = edit_vars["name"].get().strip()
        if not name:
            messagebox.showinfo("이름 없음", "재질 이름을 입력하세요.", parent=dialog)
            return
        numbers = {}
        for field in numeric_fields:
            value = parse_number(edit_vars[field].get())
            if value is None:
                messagebox.showerror("입력 오류",
                                     f"'{numeric_labels.get(field, field)}' 값이 숫자가 아닙니다.",
                                     parent=dialog)
                return
            numbers[field] = value
        keywords = edit_vars["keywords"].get().strip()
        values = [name, keywords] + [numbers[field] for field in numeric_fields]
        if has_insert:
            values.append(edit_vars["insert_grade"].get().strip())
            extra_by_name[name] = {field: edit_vars[field].get().strip()
                                   for field in ("insert_coat", "insert_iso", "insert_desc")}
        if tree.exists(name):
            tree.item(name, values=values)
        else:
            tree.insert("", tk.END, iid=name, values=values)

    def remove_selected():
        selected = tree.selection()
        if not selected:
            messagebox.showinfo("선택 없음", "지울 재질을 목록에서 고르세요.", parent=dialog)
            return
        for iid in selected:
            tree.delete(iid)
            extra_by_name.pop(iid, None)

    button_row = ttk.Frame(edit_box, padding=(0, 6, 0, 0))
    button_row.pack(fill=tk.X)
    ttk.Button(button_row, text="선택 항목 불러오기", command=load_selected).pack(side=tk.LEFT, padx=3)
    ttk.Button(button_row, text="추가/수정", command=add_or_update).pack(side=tk.LEFT, padx=3)
    ttk.Button(button_row, text="선택 삭제", command=remove_selected).pack(side=tk.LEFT, padx=3)

    def get_rows():
        result_rows = []
        for iid in tree.get_children():
            values = tree.item(iid, "values")
            row = {"name": str(values[0]),
                  "keywords": [k.strip() for k in str(values[1]).split(",") if k.strip()]}
            for offset, field in enumerate(numeric_fields, start=2):
                row[field] = float(values[offset])
            if has_insert:
                row["insert_grade"] = str(values[-1])
                row.update(extra_by_name.get(iid, {}))
            result_rows.append(row)
        return result_rows

    return get_rows


def _build_machine_spec_row(parent, machine_current):
    """가공조건 산출기 장비 스펙(이름·정격 동력·최고 회전수) 한 줄. 변수 사전을 돌려준다."""
    box = ttk.Frame(parent)
    box.pack(fill=tk.X, pady=(0, 8))
    variables = {"name": tk.StringVar(value=str(machine_current.get("name", ""))),
                "power": tk.StringVar(value=str(machine_current.get("power", ""))),
                "max_rpm": tk.StringVar(value=str(machine_current.get("max_rpm", "")))}
    ttk.Label(box, text="장비 이름").pack(side=tk.LEFT)
    ttk.Entry(box, textvariable=variables["name"], width=18).pack(side=tk.LEFT, padx=(4, 14))
    ttk.Label(box, text="정격 동력(kW)").pack(side=tk.LEFT)
    ttk.Entry(box, textvariable=variables["power"], width=8).pack(side=tk.LEFT, padx=(4, 14))
    ttk.Label(box, text="최고 회전수(RPM)").pack(side=tk.LEFT)
    ttk.Entry(box, textvariable=variables["max_rpm"], width=8).pack(side=tk.LEFT, padx=(4, 0))
    return variables


def open_settings_dialog(app):
    """설정창을 연다. 저장하면 True를 돌려주고 app에 값을 반영한다."""
    existing = getattr(app, "settings_window", None)
    if existing is not None and existing.winfo_exists():
        existing.lift()
        existing.focus_force()
        return False

    current = app.settings
    dialog = tk.Toplevel(app.root)
    app.settings_window = dialog
    dialog.title("설정")
    width = min(1180, max(860, dialog.winfo_screenwidth() - 120))
    height = min(940, max(620, dialog.winfo_screenheight() - 140))
    dialog.geometry(f"{width}x{height}"
                    f"+{max(0, (dialog.winfo_screenwidth() - width) // 2)}"
                    f"+{max(0, (dialog.winfo_screenheight() - height) // 4)}")
    dialog.minsize(720, 520)
    dialog.configure(bg=app.theme.color("bg"))
    dialog.transient(app.root)
    dialog.grab_set()
    dialog.bind("<Destroy>",
                lambda event: setattr(app, "settings_window", None) if event.widget is dialog else None)

    outer = ttk.Frame(dialog, padding=14)
    outer.pack(fill=tk.BOTH, expand=True)
    # 저장/취소 줄을 먼저 아래에 붙잡아 둔다. 탭을 먼저 pack하면 탭이 공간을 다 가져가
    # 창이 조금만 작아도 버튼 줄이 화면 밖으로 밀려난다.
    buttons = ttk.Frame(outer, padding=(0, 14, 0, 0))
    buttons.pack(side=tk.BOTTOM, fill=tk.X)
    notebook = ttk.Notebook(outer)
    notebook.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    # ---------- 1) 공정 단가 ----------
    rate_tab = ttk.Frame(notebook, padding=14)
    notebook.add(rate_tab, text="공정 단가")
    ttk.Label(rate_tab,
              text="여기서 정한 단가가 모든 카드에 그대로 쓰입니다. 카드 입력창에서는 고칠 수 없습니다.",
              style="Muted.TLabel", wraplength=760, justify="left").grid(
        row=0, column=0, columnspan=4, sticky="w", pady=(0, 10))
    rate_vars = {}
    machine_fields = config.get_machine_fields()
    for idx, (key, label) in enumerate(machine_fields):
        row, col = idx % 5 + 1, idx // 5 * 2
        ttk.Label(rate_tab, text=label).grid(row=row, column=col, sticky="e", padx=(12, 8), pady=7)
        rate_vars[key] = tk.StringVar(value=str(int(current["rates"][key])))
        ttk.Entry(rate_tab, textvariable=rate_vars[key], width=14).grid(
            row=row, column=col + 1, sticky="w", padx=6, pady=7)
    ttk.Label(rate_tab, text="단위는 원(₩)이며 시간당 단가입니다.", style="Muted.TLabel").grid(
        row=6, column=0, columnspan=4, sticky="w", pady=(12, 0))

    # ---------- 2) Material 목록 ----------
    material_tab = ttk.Frame(notebook, padding=14)
    notebook.add(material_tab, text="Material 목록")
    ttk.Label(material_tab,
              text="카드 입력창의 Material 선택 목록입니다. 목록에 없는 소재는 카드에서 직접 적어도 됩니다.",
              style="Muted.TLabel").pack(anchor="w", pady=(0, 10))
    list_row = ttk.Frame(material_tab)
    list_row.pack(fill=tk.BOTH, expand=True)
    scrollbar = ttk.Scrollbar(list_row, orient=tk.VERTICAL)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    material_list = tk.Listbox(list_row, selectmode=tk.EXTENDED, activestyle="none",
                              bg=app.theme.color("card_alt"), fg=app.theme.color("text"),
                              highlightthickness=1, highlightbackground=app.theme.color("line"),
                              selectbackground=app.theme.color("accent"),
                              selectforeground=app.theme.color("bg"))
    material_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    material_list.configure(yscrollcommand=scrollbar.set)
    scrollbar.configure(command=material_list.yview)
    for name in current["materials"]:
        material_list.insert(tk.END, name)

    add_row = ttk.Frame(material_tab, padding=(0, 10, 0, 0))
    add_row.pack(fill=tk.X)
    new_material_var = tk.StringVar()

    def add_material():
        text = new_material_var.get().strip()
        if not text:
            return
        if text in material_list.get(0, tk.END):
            messagebox.showinfo("이미 있는 소재", f"'{text}'는 이미 목록에 있습니다.", parent=dialog)
            return
        material_list.insert(tk.END, text)
        material_list.see(tk.END)
        new_material_var.set("")

    def remove_material():
        selected = list(material_list.curselection())
        if not selected:
            messagebox.showinfo("선택 없음", "지울 소재를 목록에서 고르세요.", parent=dialog)
            return
        for index in reversed(selected):
            material_list.delete(index)

    material_entry = ttk.Entry(add_row, textvariable=new_material_var, width=42)
    material_entry.pack(side=tk.LEFT, padx=(0, 8))
    # 입력칸에서 Enter를 누르면 바로 추가된다. bind_all이 아니라 이 입력칸에만 건다
    # (전역으로 걸면 다른 탭의 입력칸에서 Enter를 눌러도 소재가 추가된다).
    material_entry.bind("<Return>", lambda event: add_material())
    ttk.Button(add_row, text="추가", command=add_material).pack(side=tk.LEFT, padx=3)
    ttk.Button(add_row, text="선택 삭제", command=remove_material).pack(side=tk.LEFT, padx=3)
    ttk.Label(add_row, text="여러 개를 골라 한 번에 지울 수 있습니다.",
              style="Muted.TLabel").pack(side=tk.LEFT, padx=(12, 0))

    # ---------- 3) 소재 비중 ----------
    density_tab = ttk.Frame(notebook, padding=14)
    notebook.add(density_tab, text="소재 비중")
    ttk.Label(density_tab,
              text="카드에서 Size 치수로 무게를 계산할 때 쓰는 소재별 비중(g/cm³)입니다. "
                   "소재 이름에 이 키워드가 들어 있으면 매칭됩니다(예: 'AL6061'은 목록의 "
                   "'AL6061-T6', 'AL6061P-T651'도 함께 찾습니다). 정확히 같은 이름을 등록하면 "
                   "그 소재에만 다른 값을 줄 수 있습니다.",
              style="Muted.TLabel", wraplength=760, justify="left").pack(anchor="w", pady=(0, 10))

    density_list_row = ttk.Frame(density_tab)
    density_list_row.pack(fill=tk.BOTH, expand=True)
    density_scroll = ttk.Scrollbar(density_list_row, orient=tk.VERTICAL)
    density_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    density_tree = ttk.Treeview(density_list_row, columns=("name", "density"), show="headings",
                                selectmode="extended", yscrollcommand=density_scroll.set)
    density_tree.heading("name", text="소재 이름 / 키워드")
    density_tree.heading("density", text="비중 (g/cm³)")
    density_tree.column("name", width=420, anchor="w")
    density_tree.column("density", width=140, anchor="e")
    density_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    density_scroll.configure(command=density_tree.yview)
    for entry in current["densities"]:
        density_tree.insert("", tk.END, values=(entry["name"], entry["density"]))

    density_add_row = ttk.Frame(density_tab, padding=(0, 10, 0, 0))
    density_add_row.pack(fill=tk.X)
    new_density_name_var = tk.StringVar()
    new_density_value_var = tk.StringVar()

    def add_density():
        name = new_density_name_var.get().strip()
        value = parse_number(new_density_value_var.get())
        if not name:
            messagebox.showinfo("이름 없음", "소재 이름(키워드)을 입력하세요.", parent=dialog)
            return
        if value is None or value <= 0:
            messagebox.showerror("입력 오류", "비중은 0보다 큰 숫자로 입력해 주세요.", parent=dialog)
            return
        # 같은 이름이 이미 있으면 값만 갱신한다(중복으로 쌓이지 않게).
        for iid in density_tree.get_children():
            if density_tree.item(iid, "values")[0] == name:
                density_tree.item(iid, values=(name, value))
                break
        else:
            density_tree.insert("", tk.END, values=(name, value))
        new_density_name_var.set("")
        new_density_value_var.set("")
        density_name_entry.focus_set()

    def remove_density():
        selected = density_tree.selection()
        if not selected:
            messagebox.showinfo("선택 없음", "지울 항목을 목록에서 고르세요.", parent=dialog)
            return
        for iid in selected:
            density_tree.delete(iid)

    ttk.Label(density_add_row, text="이름/키워드").pack(side=tk.LEFT)
    density_name_entry = ttk.Entry(density_add_row, textvariable=new_density_name_var, width=22)
    density_name_entry.pack(side=tk.LEFT, padx=(6, 12))
    ttk.Label(density_add_row, text="비중").pack(side=tk.LEFT)
    density_value_entry = ttk.Entry(density_add_row, textvariable=new_density_value_var, width=8)
    density_value_entry.pack(side=tk.LEFT, padx=(6, 12))
    density_name_entry.bind("<Return>", lambda event: density_value_entry.focus_set())
    density_value_entry.bind("<Return>", lambda event: add_density())
    ttk.Button(density_add_row, text="추가/수정", command=add_density).pack(side=tk.LEFT, padx=3)
    ttk.Button(density_add_row, text="선택 삭제", command=remove_density).pack(side=tk.LEFT, padx=3)

    # ---------- 4) 가공 조건 (v0.1.1) ----------
    machining_tab = ttk.Frame(notebook, padding=14)
    notebook.add(machining_tab, text="가공 조건")
    ttk.Label(machining_tab,
              text="가공조건 산출기(Mill/Lathe 보조 계산 도구, 보조 기능 줄에서 엽니다)가 쓰는 "
                   "장비·재질 값입니다. Lathe 재질표는 04.CSS_조건 산출기.hta의 실측치이고, "
                   "Mill 재질표는 잠정치입니다 — 실제 값으로 고쳐 쓰세요. 키워드는 카드의 "
                   "Material 문자열과 매칭할 때 씁니다(예: 'S45C'가 있으면 'KS D 3752, SM45C'는 "
                   "'S45C'로는 못 찾고 'SM45C'로 찾습니다 — 실제 표기에 맞는 키워드를 넣어 주세요).",
              style="Muted.TLabel", wraplength=760, justify="left").pack(anchor="w", pady=(0, 10))

    machining_notebook = ttk.Notebook(machining_tab)
    machining_notebook.pack(fill=tk.BOTH, expand=True)

    lathe_sub = ttk.Frame(machining_notebook, padding=10)
    machining_notebook.add(lathe_sub, text="Lathe")
    ttk.Label(lathe_sub, text="장비 스펙", style="Head.TLabel").pack(anchor="w")
    lathe_machine_vars = _build_machine_spec_row(lathe_sub, current["lathe_machine"])
    ttk.Label(lathe_sub, text="재질표", style="Head.TLabel").pack(anchor="w", pady=(4, 4))
    get_lathe_materials = _build_machining_material_table(
        lathe_sub, dialog, settings_store.LATHE_MATERIAL_NUMERIC_FIELDS,
        {"kc": "kc", "v": "V(m/min)", "f": "F(mm/rev)", "ap": "Ap(mm)", "max_rpm": "최고RPM"},
        current["lathe_materials"], has_insert=True)

    mill_sub = ttk.Frame(machining_notebook, padding=10)
    machining_notebook.add(mill_sub, text="Mill")
    ttk.Label(mill_sub, text="장비 스펙", style="Head.TLabel").pack(anchor="w")
    mill_machine_vars = _build_machine_spec_row(mill_sub, current["mill_machine"])
    ttk.Label(mill_sub, text="재질표 (잠정치)", style="Head.TLabel").pack(anchor="w", pady=(4, 4))
    get_mill_materials = _build_machining_material_table(
        mill_sub, dialog, settings_store.MILL_MATERIAL_NUMERIC_FIELDS,
        {"kc": "kc", "vc": "Vc(m/min)", "fz": "fz(mm/날)", "ap": "Ap(mm)", "ae": "Ae(mm)"},
        current["mill_materials"], has_insert=False)

    # ---------- 5) 회사 / 견적서 양식 ----------
    form_tab = ttk.Frame(notebook, padding=14)
    notebook.add(form_tab, text="회사 / 견적서 양식")
    # 세 묶음을 세로로 쌓으면 마지막 묶음이 창 밖으로 밀려나므로 좌우로 나눠 놓는다.
    form_tab.columnconfigure(0, weight=1)
    form_tab.columnconfigure(1, weight=1)
    form_tab.rowconfigure(0, weight=1)
    left_col = ttk.Frame(form_tab)
    left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
    right_col = ttk.Frame(form_tab)
    right_col.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

    company_box = ttk.LabelFrame(left_col, text="우리 회사 (기계 시트 하단)", padding=10)
    company_box.pack(fill=tk.X)
    company_vars = _labeled_entries(company_box, COMPANY_FIELDS, current["company"], width=26)

    client_box = ttk.LabelFrame(left_col, text="견적서 왼쪽 위 (받는 업체)", padding=10)
    client_box.pack(fill=tk.X, pady=(12, 0))
    client_vars = _labeled_entries(client_box, CLIENT_FIELDS, current["client"], width=26)

    supplier_box = ttk.LabelFrame(right_col, text="견적서 오른쪽 위 (우리 쪽 연락처)", padding=10)
    supplier_box.pack(fill=tk.X)
    supplier_vars = _labeled_entries(supplier_box, SUPPLIER_FIELDS, current["supplier"], width=26)

    ttk.Label(right_col,
              text="견적 날짜는 저장하는 날짜(yyyy-mm-dd)로 자동으로 들어갑니다.",
              style="Muted.TLabel", wraplength=380, justify="left").pack(anchor="w", pady=(12, 0))

    # ---------- 저장 / 취소 ----------
    result = {"saved": False}

    def _read_machine_vars(vars_dict, label):
        name = vars_dict["name"].get().strip()
        power = parse_number(vars_dict["power"].get())
        max_rpm = parse_number(vars_dict["max_rpm"].get())
        if power is None or power <= 0:
            messagebox.showerror("입력 오류", f"{label} 정격 동력은 0보다 큰 숫자로 입력해 주세요.",
                                 parent=dialog)
            return None
        if max_rpm is None or max_rpm <= 0:
            messagebox.showerror("입력 오류", f"{label} 최고 회전수는 0보다 큰 숫자로 입력해 주세요.",
                                 parent=dialog)
            return None
        return {"name": name, "power": power, "max_rpm": max_rpm}

    def save_and_close():
        rates = {}
        for key, label in machine_fields:
            value = parse_number(rate_vars[key].get())
            if value is None or value < 0:
                messagebox.showerror("입력 오류", f"'{label}' 단가는 0 이상의 숫자로 입력해 주세요.",
                                     parent=dialog)
                return
            rates[key] = value
        densities = []
        for iid in density_tree.get_children():
            name, value = density_tree.item(iid, "values")
            densities.append({"name": str(name), "density": float(value)})
        lathe_machine = _read_machine_vars(lathe_machine_vars, "Lathe")
        if lathe_machine is None:
            return
        mill_machine = _read_machine_vars(mill_machine_vars, "Mill")
        if mill_machine is None:
            return
        payload = {
            "rates": rates,
            "materials": list(material_list.get(0, tk.END)),
            "densities": densities,
            "company": {key: company_vars[key].get().strip() for key, _, _ in COMPANY_FIELDS},
            "client": {key: client_vars[key].get().strip() for key, _, _ in CLIENT_FIELDS},
            "supplier": {key: supplier_vars[key].get().strip() for key, _, _ in SUPPLIER_FIELDS},
            # 이 창에서는 열 폭을 다루지 않으니 지금 값을 그대로 넘긴다(요청 3-3, table.py에서 고침).
            "col_widths": current.get("col_widths", {}),
            "lathe_machine": lathe_machine,
            "mill_machine": mill_machine,
            "lathe_materials": get_lathe_materials(),
            "mill_materials": get_mill_materials(),
        }
        if not settings_store.save(payload):
            messagebox.showerror("저장 오류",
                                 f"설정을 저장하지 못했습니다.\n{settings_store.get_settings_path()}",
                                 parent=dialog)
            return
        app.apply_settings(settings_store.load())
        result["saved"] = True
        dialog.destroy()

    ttk.Label(buttons, text=f"저장 위치: {settings_store.get_settings_path()}",
              style="Muted.TLabel", wraplength=520, justify="left").pack(side=tk.LEFT)
    ttk.Button(buttons, text="저장", command=save_and_close).pack(side=tk.RIGHT, padx=4)
    ttk.Button(buttons, text="취소", command=dialog.destroy).pack(side=tk.RIGHT, padx=4)
    dialog.bind("<Escape>", lambda event: dialog.destroy())

    app.root.wait_window(dialog)
    return result["saved"]
