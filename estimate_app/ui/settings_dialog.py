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

    # ---------- 4) 회사 / 견적서 양식 ----------
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
        payload = {
            "rates": rates,
            "materials": list(material_list.get(0, tk.END)),
            "densities": densities,
            "company": {key: company_vars[key].get().strip() for key, _, _ in COMPANY_FIELDS},
            "client": {key: client_vars[key].get().strip() for key, _, _ in CLIENT_FIELDS},
            "supplier": {key: supplier_vars[key].get().strip() for key, _, _ in SUPPLIER_FIELDS},
            # 이 창에서는 열 폭을 다루지 않으니 지금 값을 그대로 넘긴다(요청 3-3, table.py에서 고침).
            "col_widths": current.get("col_widths", {}),
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
