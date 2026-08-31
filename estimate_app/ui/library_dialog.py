"""견적 보관함 창 — 카드 목록을 이름 붙여 저장하고 다시 불러온다(v0.1.4 신설).

데이터 폴더를 공유 폴더로 잡아 두면(설정 > 데이터 위치) 이 목록을 여러 PC가 같이 본다.
저장·불러오기 두 버튼이 같은 창을 열고, 어느 쪽으로 열렸는지에 따라 포커스만 다르다
(같은 목록을 보면서 저장할지 불러올지 정하는 편이 실제 사용에 맞다).

주의: 불러오기는 현재 카드 목록을 **통째로 바꾼다**. 지금 작업 중인 내용이 있으면 반드시
먼저 묻는다 — 삭제와 달리 Ctrl+Z로 되돌릴 수 없기 때문이다.
"""

import queue
import threading
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

from ..core import datastore, library

_MODE_TITLE = {"save": "견적 저장", "load": "견적 불러오기"}


def _format_entry(entry):
    if entry.get("broken"):
        return f"{entry['title']}   (파일을 읽을 수 없음)"
    saved_at = entry["saved_at"] or "-"
    who = f"   {entry['saved_by']}" if entry["saved_by"] else ""
    return f"{entry['title']}   |   {entry['count']}건   |   {saved_at}{who}"


def open_library_dialog(app, mode="load"):
    """보관함 창을 연다. 이미 열려 있으면 그 창을 앞으로 올린다."""
    existing = getattr(app, "library_window", None)
    if existing is not None and existing.winfo_exists():
        existing.lift()
        existing.focus_force()
        return

    dialog = tk.Toplevel(app.root)
    app.library_window = dialog
    dialog.title(_MODE_TITLE.get(mode, "견적 보관함"))
    width, height = 820, 560
    dialog.geometry(f"{width}x{height}"
                    f"+{max(0, (dialog.winfo_screenwidth() - width) // 2)}"
                    f"+{max(0, (dialog.winfo_screenheight() - height) // 4)}")
    dialog.minsize(680, 460)
    dialog.configure(bg=app.theme.color("bg"))
    dialog.transient(app.root)
    dialog.grab_set()
    dialog.bind("<Destroy>",
                lambda event: setattr(app, "library_window", None) if event.widget is dialog else None)

    outer = ttk.Frame(dialog, padding=14)
    outer.pack(fill=tk.BOTH, expand=True)

    location_var = tk.StringVar()
    ttk.Label(outer, textvariable=location_var, style="Muted.TLabel",
              wraplength=760, justify="left").pack(anchor="w", pady=(0, 10))

    # 저장 줄을 먼저 아래에 붙잡아 둔다(설정창과 같은 이유 — 목록이 공간을 다 가져가면
    # 창이 조금만 작아도 버튼 줄이 화면 밖으로 밀린다).
    bottom = ttk.Frame(outer, padding=(0, 12, 0, 0))
    bottom.pack(side=tk.BOTTOM, fill=tk.X)

    list_row = ttk.Frame(outer)
    list_row.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
    scrollbar = ttk.Scrollbar(list_row, orient=tk.VERTICAL)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    entry_list = tk.Listbox(list_row, activestyle="none",
                            bg=app.theme.color("card_alt"), fg=app.theme.color("text"),
                            highlightthickness=1, highlightbackground=app.theme.color("line"),
                            selectbackground=app.theme.color("accent"),
                            selectforeground=app.theme.color("bg"))
    entry_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    entry_list.configure(yscrollcommand=scrollbar.set)
    scrollbar.configure(command=entry_list.yview)

    name_var = tk.StringVar()
    entries = []
    scan_queue = queue.Queue()
    refresh_token = {"value": 0}

    def selected_entry():
        # 목록이 비었거나 못 읽었을 때는 안내 문구 한 줄을 대신 넣어 둔다. 그 줄도 클릭이
        # 되므로 `entries`와 번호가 어긋난다 -- 길이를 반드시 같이 본다(안 그러면 보관함이
        # 빈 첫 실행에서 그 줄을 클릭하는 순간 IndexError가 난다).
        indexes = entry_list.curselection()
        if not indexes or indexes[0] >= len(entries):
            return None
        return entries[indexes[0]]

    def _apply_entry_list(found, error, state, directory, select_title):
        entries.clear()
        entry_list.delete(0, tk.END)
        location_var.set(f"보관 위치: {directory}\n상태: {datastore.describe(state)}")
        if error:
            entry_list.insert(tk.END, "  보관함을 읽을 수 없습니다 — 데이터 위치 설정을 확인하세요.")
            return
        entries.extend(found)
        for entry in entries:
            entry_list.insert(tk.END, _format_entry(entry))
        if not entries:
            entry_list.insert(tk.END, "  저장된 견적이 없습니다.")
            return
        target = select_title or (app.library_current or {}).get("title")
        if target:
            for index, entry in enumerate(entries):
                if entry["title"] == target:
                    entry_list.selection_set(index)
                    entry_list.see(index)
                    break

    def _poll_refresh(token):
        try:
            result = scan_queue.get_nowait()
        except queue.Empty:
            if refresh_token["value"] == token and dialog.winfo_exists():
                dialog.after(80, lambda: _poll_refresh(token))
            return
        if result[0] != refresh_token["value"] or not dialog.winfo_exists():
            return
        _token, found, error, state, directory, select_title = result
        _apply_entry_list(found, error, state, directory, select_title)

    def refresh_list(select_title=None):
        refresh_token["value"] += 1
        token = refresh_token["value"]
        entries.clear()
        entry_list.delete(0, tk.END)
        entry_list.insert(tk.END, "  보관함을 불러오는 중입니다...")
        location_var.set("보관 위치를 확인하는 중입니다...")

        def worker():
            try:
                state = datastore.get_state()
                directory = datastore.get_library_dir()
                found, error = library.list_entries()
            except OSError:
                state = {"dir": "", "shared": True, "ok": False,
                         "reason": datastore.REASON_UNREACHABLE}
                directory = ""
                found, error = [], datastore.REASON_UNREACHABLE
            scan_queue.put((token, found, error, state, directory, select_title))

        threading.Thread(target=worker, daemon=True).start()
        dialog.after(80, lambda: _poll_refresh(token))

    def on_select(_event=None):
        entry = selected_entry()
        if entry:
            name_var.set(entry["title"])

    def do_load(_event=None):
        entry = selected_entry()
        if entry is None:
            messagebox.showinfo("선택 없음", "불러올 견적을 목록에서 고르세요.", parent=dialog)
            return
        if entry.get("broken"):
            messagebox.showerror("불러오기 오류",
                                 f"'{entry['title']}' 파일을 읽을 수 없습니다.\n{entry['path']}",
                                 parent=dialog)
            return
        # 불러오기는 현재 목록을 통째로 바꾼다. Ctrl+Z로 되돌릴 수 없으므로 반드시 묻는다.
        if app.data and not messagebox.askyesno(
                "불러오기 확인",
                f"현재 카드 {len(app.data)}건을 '{entry['title']}' ({entry['count']}건)으로"
                f" 바꿉니다.\n\n지금 목록은 저장하지 않으면 사라집니다. 계속할까요?",
                default="no", parent=dialog):
            return
        payload, error = library.load_entry(entry["path"])
        if error:
            messagebox.showerror("불러오기 오류",
                                 f"'{entry['title']}'을 읽지 못했습니다.\n{entry['path']}",
                                 parent=dialog)
            return
        if not app.apply_library_entry(payload, entry["path"]):
            return  # 입력창이 열려 있어 거절됐다(안내는 app이 이미 띄웠다)
        messagebox.showinfo("불러오기 완료",
                            f"'{payload['title']}' {len(payload['items'])}건을 불러왔습니다.",
                            parent=dialog)
        dialog.destroy()

    def do_save():
        title = library.sanitize_title(name_var.get())
        if not title:
            messagebox.showinfo("이름 필요", "저장할 이름을 적어 주세요.", parent=dialog)
            return
        if title != name_var.get().strip():
            if not messagebox.askyesno(
                    "이름 확인",
                    f"파일 이름에 쓸 수 없는 문자가 있어 다음 이름으로 저장합니다.\n\n{title}\n\n계속할까요?",
                    parent=dialog):
                return
        items = [item for item in app.data]
        if not items:
            messagebox.showinfo("저장할 항목 없음", "저장할 카드가 없습니다.", parent=dialog)
            return

        path = library.entry_path(title)
        existing_mtime = library.get_mtime(path)
        if existing_mtime is not None:
            # 내가 불러온 뒤 다른 사람이 같은 파일을 고쳐 놨는지 본다. 잠금을 걸지 않는
            # 대신(library.py 첫머리 참고) 덮어쓰기 직전에 확인해서 알린다.
            if library.is_changed_by_other(app.library_current, path, existing_mtime):
                stamp = datetime.fromtimestamp(existing_mtime).strftime("%Y-%m-%d %H:%M:%S")
                if not messagebox.askyesno(
                        "다른 사람이 고쳤습니다",
                        f"'{title}'은 불러온 뒤에 다른 곳에서 저장됐습니다 (마지막 저장 {stamp}).\n\n"
                        f"지금 저장하면 그 내용이 사라집니다. 덮어쓸까요?",
                        default="no", parent=dialog):
                    return
            elif not messagebox.askyesno(
                    "덮어쓰기 확인",
                    f"'{title}'이 이미 있습니다. 덮어쓸까요?", parent=dialog):
                return

        result = library.save_entry(title, items)
        if result is None:
            messagebox.showerror(
                "저장 오류",
                f"견적을 저장하지 못했습니다.\n{path}\n\n"
                f"데이터 위치 설정과 폴더 권한을 확인해 주세요.", parent=dialog)
            return
        app.library_current = {"title": title, "path": result["path"], "mtime": result["mtime"]}
        # 세션에도 바로 남긴다 -- 저장 직후 프로그램을 끄면 이 참조가 사라져, 다음에 켰을 때
        # 덮어쓰기 충돌 판정의 기준점을 잃는다.
        app.save_session()
        messagebox.showinfo("저장 완료",
                            f"'{title}' {result['count']}건을 저장했습니다.\n\n{result['path']}",
                            parent=dialog)
        refresh_list(select_title=title)

    def do_delete():
        entry = selected_entry()
        if entry is None:
            messagebox.showinfo("선택 없음", "지울 견적을 목록에서 고르세요.", parent=dialog)
            return
        if not messagebox.askyesno(
                "삭제 확인",
                f"보관함에서 '{entry['title']}'을 지울까요?\n\n"
                f"공유 폴더의 파일이 지워지며 되돌릴 수 없습니다.",
                default="no", parent=dialog):
            return
        if not library.delete_entry(entry["path"]):
            messagebox.showerror("삭제 오류", f"파일을 지우지 못했습니다.\n{entry['path']}", parent=dialog)
            return
        if (app.library_current or {}).get("path") == entry["path"]:
            app.library_current = None
        refresh_list()

    entry_list.bind("<<ListboxSelect>>", on_select)
    entry_list.bind("<Double-Button-1>", do_load)

    # 버튼을 한 줄에 다 넣었더니 창을 최소 폭으로 줄였을 때 오른쪽 버튼 둘이 0px로
    # 눌려 사라졌다(직접 캡처해서 확인). 목록 조작과 저장을 두 줄로 나눈다.
    action_row = ttk.Frame(bottom)
    action_row.pack(fill=tk.X)
    ttk.Button(action_row, text="불러오기", command=do_load).pack(side=tk.LEFT)
    ttk.Button(action_row, text="새로고침", command=lambda: refresh_list()).pack(side=tk.LEFT, padx=8)
    # 삭제는 공유 폴더의 파일을 지우는 동작이라 되돌릴 수 없다 -- 오클릭을 막으려고 떼어 둔다.
    ttk.Button(action_row, text="삭제", command=do_delete).pack(side=tk.LEFT, padx=(24, 0))
    ttk.Button(action_row, text="닫기", command=dialog.destroy).pack(side=tk.RIGHT)

    save_row = ttk.Frame(bottom)
    save_row.pack(fill=tk.X, pady=(10, 0))
    ttk.Label(save_row, text="이름").pack(side=tk.LEFT, padx=(0, 8))
    ttk.Button(save_row, text="현재 카드 목록 저장",
               command=do_save).pack(side=tk.RIGHT, padx=(8, 0))
    name_entry = ttk.Entry(save_row, textvariable=name_var)
    name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

    ttk.Label(bottom,
              text="불러오면 현재 카드 목록이 통째로 바뀝니다. 작업 중인 내용은 먼저 저장하세요.",
              style="Muted.TLabel").pack(anchor="w", pady=(10, 0))

    refresh_list()
    # 저장으로 열었으면 이름 칸에, 불러오기로 열었으면 목록에 포커스를 준다.
    if mode == "save":
        default_title = (app.library_current or {}).get("title") \
            or f"견적_{datetime.now():%Y-%m-%d}"
        name_var.set(default_title)
        name_entry.focus_set()
        name_entry.selection_range(0, tk.END)
    else:
        entry_list.focus_set()

    dialog.bind("<Escape>", lambda event: dialog.destroy())
    app.root.wait_window(dialog)
