"""설정창(v0.0.9 신설, 요청 6번).

여기서 고친 값은 저장하는 순간 전체에 적용된다.

    공정 단가      카드 팝업에서는 고칠 수 없는 고정값으로 쓰인다(요청 6-2).
    Material       카드 입력창의 선택 목록. 여기서 추가·삭제한다(요청 6-3).
    회사 / 양식    기계 시트 푸터의 회사명·작성자와, 견적서 시트 맨 위 문구(요청 6-4, 7-1).
    소재 비중      v0.1.0 신설. 카드에서 무게를 계산할 때 쓰는 소재별 비중(요청 4-2).
    데이터 위치    v0.1.4 신설. 위 값들과 견적 보관함을 어느 폴더에 둘지(네트워크 공유).

값은 `settings.json`에 저장한다(core/settings.py). 기본 자리는
`%LOCALAPPDATA%\\MachineEstimate`이고, v0.1.4부터 '데이터 위치' 탭에서 공유 폴더로 옮길 수 있다.
"""

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from ..core import config, datastore, settings as settings_store
from ..core.model import parse_number

# 데이터 위치 변경 결과를 사람이 읽는 문장으로. 어느 쪽 설정이 이겼는지 반드시 알린다 --
# 말없이 기본값으로 시작하면 사용자에게는 "내 단가가 초기화됐다"로 보인다.
_LOCATION_ACTION = {
    "adopted": "그 폴더에 이미 있던 설정을 가져왔습니다. 이 PC에서 쓰던 값 대신 공유 폴더의 값이 적용됩니다.",
    "copied": "폴더가 비어 있어 이 PC에서 쓰던 설정을 복사해 넣었습니다.",
    "fresh": "폴더가 비어 있지만, 직전에 설정을 읽지 못한 상태라 복사하지 않았습니다."
             " 기본값으로 시작하니 단가와 소재 목록을 확인해 주세요.",
}
_LOCATION_ERROR = {
    datastore.REASON_MISSING: "그 폴더를 찾을 수 없습니다.",
    datastore.REASON_UNREACHABLE: "그 폴더에 연결하지 못했습니다. 네트워크 연결과 경로를 확인해 주세요.",
    datastore.REASON_READONLY: "그 폴더에 쓸 수 없습니다. 폴더 권한을 확인해 주세요.",
    "broken": "그 폴더의 settings.json을 읽을 수 없습니다. 파일이 깨졌을 수 있습니다.",
    "location_write_failed": "설정 위치를 기록하지 못했습니다.",
}

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


def _build_location_tab(notebook, app, dialog):
    """데이터 위치 탭(v0.1.4). 네트워크 공유 폴더를 고르는 곳이다.

    다른 탭과 달리 아래 '저장' 버튼을 거치지 않는다 -- 폴더를 바꾸면 단가·소재 같은 값의
    출처 자체가 달라지므로, 화면에 떠 있는 옛 값을 그대로 새 폴더에 쓰면 안 되기 때문이다.
    적용하면 설정창을 닫고 새 폴더에서 다시 읽는다.
    """
    tab = ttk.Frame(notebook, padding=14)
    notebook.add(tab, text="데이터 위치")

    ttk.Label(tab, wraplength=760, justify="left", style="Muted.TLabel",
              text="단가·Material 목록·소재 비중·가공 조건·회사 정보와 '견적 보관함'을 어디에 둘지"
                   " 정합니다.\n네트워크 공유 폴더를 지정하면 여러 PC가 같은 기준으로 견적을 내고,"
                   " 저장한 견적을 서로 열어 볼 수 있습니다."
              ).pack(anchor="w", pady=(0, 12))

    ttk.Label(tab, wraplength=760, justify="left",
              text="※ 이 탭은 아래 [저장] 버튼과 상관없이 누르는 즉시 적용됩니다."
              ).pack(anchor="w", pady=(0, 10))

    status_var = tk.StringVar()
    path_var = tk.StringVar()

    box = ttk.LabelFrame(tab, text="현재 위치", padding=12)
    box.pack(fill=tk.X)
    ttk.Label(box, textvariable=status_var, wraplength=720, justify="left").pack(anchor="w")

    pick = ttk.LabelFrame(tab, text="공유 폴더 지정", padding=12)
    pick.pack(fill=tk.X, pady=(14, 0))
    row = ttk.Frame(pick)
    row.pack(fill=tk.X)
    ttk.Entry(row, textvariable=path_var, width=64).pack(side=tk.LEFT, fill=tk.X, expand=True)
    ttk.Button(row, text="찾아보기…",
               command=lambda: _browse_folder(dialog, path_var)).pack(side=tk.LEFT, padx=(8, 0))
    ttk.Label(pick, style="Muted.TLabel", wraplength=720, justify="left",
              text=r"네트워크 경로는 \\서버이름\공유폴더\Estimate 처럼 직접 적어도 됩니다."
                   " 모든 PC가 같은 폴더를 가리켜야 하며, 그 폴더에 읽기·쓰기 권한이 있어야 합니다."
              ).pack(anchor="w", pady=(10, 0))

    def refresh_status():
        state = datastore.get_state(recheck=True)
        location = datastore.load_location()
        lines = [f"폴더: {state['dir']}", f"상태: {datastore.describe(state)}"]
        error = settings_store.get_load_error()
        if error:
            lines.append("설정 파일을 읽지 못해 지금은 기본값이 보입니다."
                         " 이 상태에서는 설정을 저장하지 않습니다(공유 파일이 기본값으로"
                         " 덮어써지는 것을 막기 위해서입니다).")
        status_var.set("\n".join(lines))
        if location["path"] and not path_var.get().strip():
            path_var.set(location["path"])

    def apply_location(path, enabled):
        result = settings_store.relocate(path, enabled)
        if not result["ok"]:
            detail = _LOCATION_ERROR.get(result["reason"], "폴더를 사용할 수 없습니다.")
            # 네트워크 경로는 '폴더가 없다'와 '서버에 못 닿는다'가 겉으로 똑같이 보인다
            # (연결이 끊기면 윈도우도 그냥 '없음'으로 답한다). 확인할 곳을 같이 알려 준다.
            if str(path).startswith("\\\\") and result["reason"] == datastore.REASON_MISSING:
                detail += " 서버 이름·공유 이름이 맞는지, 그 PC에 접근할 수 있는지 확인해 주세요."
            messagebox.showerror("데이터 위치 변경 실패", f"{detail}\n\n{path or ''}", parent=dialog)
            refresh_status()
            return
        app.apply_settings(result["settings"])
        app.library_current = None  # 폴더가 바뀌면 보관함도 다른 곳을 본다
        app.save_session()          # 옛 폴더의 견적을 가리키는 참조가 세션에 남지 않게
        messagebox.showinfo("데이터 위치 변경",
                            f"{_LOCATION_ACTION[result['action']]}\n\n"
                            f"폴더: {datastore.get_data_dir()}\n\n"
                            f"설정창을 닫습니다. 바뀐 값을 보려면 다시 열어 주세요.",
                            parent=dialog)
        dialog.destroy()

    def use_shared():
        path = path_var.get().strip()
        if not path:
            messagebox.showinfo("경로 없음", "사용할 폴더를 고르거나 경로를 적어 주세요.", parent=dialog)
            return
        apply_location(path, True)

    def use_local():
        if not datastore.is_shared():
            messagebox.showinfo("이미 로컬", "이미 이 PC에만 저장하고 있습니다.", parent=dialog)
            return
        if not messagebox.askyesno(
                "로컬로 되돌리기",
                "이 PC의 기본 폴더(%LOCALAPPDATA%\\MachineEstimate)로 되돌립니다.\n\n"
                "공유 폴더의 파일은 지우지 않습니다. 다만 이 PC의 단가·소재 설정은"
                " 공유 폴더로 옮기기 전 값으로 돌아갑니다. 계속할까요?",
                default="no", parent=dialog):
            return
        apply_location("", False)

    buttons = ttk.Frame(tab, padding=(0, 14, 0, 0))
    buttons.pack(fill=tk.X)
    ttk.Button(buttons, text="이 폴더 사용", command=use_shared).pack(side=tk.LEFT)
    ttk.Button(buttons, text="다시 확인", command=refresh_status).pack(side=tk.LEFT, padx=8)
    ttk.Button(buttons, text="이 PC에만 저장(기본값)", command=use_local).pack(side=tk.LEFT)

    ttk.Label(tab, style="Muted.TLabel", wraplength=760, justify="left",
              text="작업 중인 카드 목록(자동 저장)과 업데이트 기록은 공유하지 않고 PC마다 따로 둡니다."
                   " 자동 저장은 물어보지 않고 덮어쓰기 때문에, 두 사람이 같이 켜 두면 나중에 끈"
                   " 쪽이 앞사람 작업을 지워 버립니다. 여러 PC가 견적을 주고받는 일은"
                   " '견적 저장 / 견적 불러오기'(견적 보관함)가 맡습니다."
              ).pack(anchor="w", pady=(16, 0))

    refresh_status()


def _browse_folder(dialog, path_var):
    initial = path_var.get().strip() or None
    chosen = filedialog.askdirectory(parent=dialog, title="데이터를 저장할 폴더 선택",
                                     initialdir=initial, mustexist=True)
    if chosen:
        path_var.set(os.path.normpath(chosen))


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

    # ---------- 4) 화면 열 ----------
    column_tab = ttk.Frame(notebook, padding=14)
    notebook.add(column_tab, text="화면 열")
    ttk.Label(column_tab,
              text="현황판과 출력 양식에 표시할 서술 열 제목을 바꿉니다. No, SUM, 단가, 최종단가는 계산 기준이라 고정입니다.",
              style="Muted.TLabel", wraplength=820, justify="left").pack(anchor="w", pady=(0, 12))

    header_fields = [
        ("model", "기종"), ("part_no", "품번"), ("part_name", "품명"),
        ("comment", "Coment"), ("possible", "가능여부"), ("qty", "Qty"),
        ("material", "Material"), ("heat", "열처리"), ("size", "Size"),
    ]
    header_box = ttk.LabelFrame(column_tab, text="열 제목", padding=10)
    header_box.pack(fill=tk.X)
    header_vars = {}
    for idx, (key, label) in enumerate(header_fields):
        row, col = divmod(idx, 3)
        ttk.Label(header_box, text=label).grid(row=row, column=col * 2, sticky="e", padx=(8, 6), pady=5)
        header_vars[key] = tk.StringVar(value=str(current.get("headers", {}).get(key, label)))
        ttk.Entry(header_box, textvariable=header_vars[key], width=20).grid(
            row=row, column=col * 2 + 1, sticky="ew", padx=(0, 10), pady=5)
    for col in (1, 3, 5):
        header_box.columnconfigure(col, weight=1)

    def reset_headers():
        for key, label in header_fields:
            header_vars[key].set(settings_store.DEFAULT_HEADERS[key])

    def reset_widths():
        app.reset_column_widths()
        messagebox.showinfo("열 폭 초기화", "대시보드 열 폭을 기본값으로 되돌렸습니다.", parent=dialog)

    reset_row = ttk.Frame(column_tab, padding=(0, 12, 0, 0))
    reset_row.pack(fill=tk.X)
    ttk.Button(reset_row, text="열 제목 기본값", command=reset_headers).pack(side=tk.LEFT, padx=(0, 6))
    ttk.Button(reset_row, text="열 폭 기본값", command=reset_widths).pack(side=tk.LEFT, padx=6)
    ttk.Button(reset_row, text="열 제목·폭 모두 기본값", command=lambda: (reset_headers(), reset_widths())).pack(side=tk.LEFT, padx=6)
    ttk.Label(column_tab,
              text=f"열 폭이 망가져 설정 버튼을 누르기 어렵다면 {settings_store.get_settings_path()} 파일을 삭제하면 기본값으로 복구됩니다.",
              style="Muted.TLabel", wraplength=820, justify="left").pack(anchor="w", pady=(12, 0))
    # ---------- 6) 데이터 위치 (v0.1.4) ----------
    # 이 탭만 '저장' 버튼과 무관하게 즉시 적용된다. 폴더를 바꾸는 순간 다른 탭이 들고 있는
    # 값(옛 폴더에서 읽은 단가 등)이 통째로 낡기 때문에, 적용하면 이 창을 닫고 새로 열게 한다.
    _build_location_tab(notebook, app, dialog)

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
        headers = {key: header_vars[key].get().strip() for key, _ in header_fields}
        if any(not value for value in headers.values()):
            messagebox.showerror("입력 오류", "열 제목은 비워 둘 수 없습니다.", parent=dialog)
            return
        if len(set(headers.values())) != len(headers):
            messagebox.showerror("입력 오류", "열 제목은 서로 중복될 수 없습니다.", parent=dialog)
            return
        reserved = {"No", "SUM", "단가", "최종단가"}
        if any(value in reserved for value in headers.values()):
            messagebox.showerror("입력 오류", "No, SUM, 단가, 최종단가는 고정 제목이라 사용할 수 없습니다.", parent=dialog)
            return
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
            "headers": headers,
            # 이 창에서는 열 폭을 다루지 않으니 지금 값을 그대로 넘긴다(요청 3-3, table.py에서 고침).
            "col_widths": current.get("col_widths", {}),
            "lathe_machine": lathe_machine,
            "mill_machine": mill_machine,
            "lathe_materials": get_lathe_materials(),
            "mill_materials": get_mill_materials(),
        }
        if not settings_store.save(payload):
            # v0.1.4: 공유 폴더를 못 읽은 상태에서는 save()가 일부러 거부한다.
            # 그 경우와 진짜 쓰기 실패를 구분해서 알린다.
            error = settings_store.get_load_error()
            detail = ("설정 파일을 읽지 못한 상태라 저장하지 않았습니다.\n"
                      "지금 화면에 보이는 값은 기본값이며, 이대로 저장하면 공유 폴더의 설정이"
                      " 모두 기본값으로 바뀝니다.\n\n'데이터 위치' 탭에서 폴더 상태를 확인해 주세요."
                      if error else "설정을 저장하지 못했습니다. 폴더 권한을 확인해 주세요.")
            messagebox.showerror("저장 오류",
                                 f"{detail}\n\n{settings_store.get_settings_path()}",
                                 parent=dialog)
            return
        app.apply_settings(settings_store.load())
        result["saved"] = True
        dialog.destroy()

    ttk.Label(buttons, text=f"저장 위치: {settings_store.get_settings_path()}",
              style="Muted.TLabel", wraplength=520, justify="left").pack(side=tk.LEFT)
    ttk.Button(buttons, text="저장", command=save_and_close).pack(side=tk.RIGHT, padx=4)
    def current_snapshot():
        return {
            "rates": {key: rate_vars[key].get() for key, _ in machine_fields},
            "materials": list(material_list.get(0, tk.END)),
            "company": {key: company_vars[key].get() for key, _, _ in COMPANY_FIELDS},
            "client": {key: client_vars[key].get() for key, _, _ in CLIENT_FIELDS},
            "supplier": {key: supplier_vars[key].get() for key, _, _ in SUPPLIER_FIELDS},
            "headers": {key: header_vars[key].get() for key, _ in header_fields},
        }

    initial_snapshot = current_snapshot()

    def close_dialog(event=None):
        if current_snapshot() != initial_snapshot and not messagebox.askyesno(
                "설정 확인", "저장하지 않은 변경 사항이 있습니다.\n저장하지 않고 닫으시겠습니까?", parent=dialog):
            return
        dialog.destroy()

    ttk.Button(buttons, text="취소", command=close_dialog).pack(side=tk.RIGHT, padx=4)
    dialog.bind("<Escape>", close_dialog)
    dialog.protocol("WM_DELETE_WINDOW", close_dialog)

    app.root.wait_window(dialog)
    return result["saved"]
