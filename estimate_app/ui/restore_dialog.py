"""백업에서 복원 창 (v1.8.0).

서버의 백업 목록(자동·수동·복원 직전 상태)을 보여 주고, 고른 시점으로 서버 데이터를 되돌린다.
복원은 서버가 한다 — 되돌리기 직전 상태를 `before_restore_…` 파일로 먼저 남기므로, 잘못 되돌렸다면
같은 창의 목록에서 그 파일을 골라 다시 복원하면 된다. 편집 암호는 지금 것이 유지된다.
"""

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from ..core import datastore, remote

_KIND = {"manual": "수동", "auto": "자동", "restore": "복원 직전"}


def _size_text(size):
    return f"{max(1, int(size or 0) // 1024):,}KB"


def open_restore_dialog(app):
    """[백업에서 복원] 단추."""
    if not datastore.location_is_server():
        messagebox.showinfo("서버 연결 필요", "백업 복원은 견적 서버에 연결했을 때 쓸 수 있습니다."
                            "\n\n[설정 > 데이터 위치]에서 서버 주소를 지정해 주세요.", parent=app.root)
        return
    if not app.require_edit("백업에서 복원"):
        return
    existing = getattr(app, "restore_window", None)
    if existing is not None and existing.winfo_exists():
        existing.lift()
        return

    base = datastore.get_data_dir()
    app.root.configure(cursor="watch")
    app.root.update_idletasks()
    try:
        entries, error = remote.list_backups(base)
    finally:
        app.root.configure(cursor="")
    if error == remote.REASON_MISSING:
        messagebox.showwarning("서버 버전이 낮습니다", "서버를 1.3.0 이상으로 올려야 백업 복원을 쓸 수 있습니다.",
                               parent=app.root)
        return
    if error:
        messagebox.showerror("백업 복원", "서버에서 백업 목록을 가져오지 못했습니다.", parent=app.root)
        return
    if not entries:
        messagebox.showinfo("백업 복원", "서버에 백업이 없습니다. 먼저 [데이터 백업]을 눌러 만들어 주세요.",
                            parent=app.root)
        return

    dialog = tk.Toplevel(app.root)
    app.restore_window = dialog
    dialog.title("백업에서 복원")
    dialog.transient(app.root)
    dialog.geometry("640x420")
    dialog.minsize(520, 300)
    dialog.configure(bg=app.theme.color("bg"))
    frame = ttk.Frame(dialog, padding=14)
    frame.pack(fill=tk.BOTH, expand=True)

    ttk.Label(frame, text="되돌릴 시점을 고르세요. 서버의 모든 견적과 설정이 그 시점으로 돌아갑니다.\n"
                          "되돌리기 직전 상태는 '복원 직전'으로 자동 보관되어 언제든 다시 복원할 수 있습니다.",
              style="Muted.TLabel", justify="left", wraplength=600).pack(anchor="w", pady=(0, 8))

    status = tk.StringVar(value="")
    buttons = ttk.Frame(frame)
    buttons.pack(side=tk.BOTTOM, fill=tk.X, pady=(8, 0))
    ttk.Label(frame, textvariable=status, style="Muted.TLabel").pack(side=tk.BOTTOM, anchor="w", pady=(8, 0))
    restore_btn = ttk.Button(buttons, text="선택한 시점으로 복원")
    restore_btn.pack(side=tk.LEFT)
    ttk.Button(buttons, text="닫기", command=dialog.destroy).pack(side=tk.RIGHT)

    holder = ttk.Frame(frame)
    holder.pack(fill=tk.BOTH, expand=True)
    columns = ("time", "kind", "count", "size")
    tree = ttk.Treeview(holder, columns=columns, show="headings", selectmode="browse", height=6)
    for key, text, width, anchor in (("time", "백업 시각", 190, "w"), ("kind", "구분", 90, "center"),
                                     ("count", "견적 수", 80, "e"), ("size", "크기", 90, "e")):
        tree.heading(key, text=text)
        tree.column(key, width=width, anchor=anchor)
    scroll = ttk.Scrollbar(holder, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scroll.set)
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scroll.pack(side=tk.RIGHT, fill=tk.Y)

    by_id = {}
    for entry in entries:
        count = entry.get("estimates")
        iid = tree.insert("", "end", values=(entry.get("created_at", ""), _KIND.get(entry.get("kind"), ""),
                                             "-" if count is None else count, _size_text(entry.get("size"))))
        by_id[iid] = entry
    first = tree.get_children()
    if first:
        tree.selection_set(first[0])

    def chosen():
        selection = tree.selection()
        return by_id.get(selection[0]) if selection else None

    def do_restore():
        entry = chosen()
        if entry is None:
            return
        if not app.require_edit("백업에서 복원", parent=dialog):
            return
        count = entry.get("estimates")
        text = (f"{entry.get('created_at', '')} 시점({_KIND.get(entry.get('kind'), '')} 백업"
                f"{'' if count is None else f', 견적 {count}개'})으로 서버 데이터를 되돌립니다."
                f"\n\n그 이후에 저장한 내용은 이 백업에 없으면 사라집니다(복원 직전 상태는 자동 보관됩니다).")
        if app.library_dirty():
            text += "\n\n이 PC에 아직 서버에 올리지 못한 변경이 있습니다. 복원 후 서버 내용으로 바뀝니다."
        if not messagebox.askyesno("백업에서 복원", text + "\n\n복원할까요?", default="no", parent=dialog):
            return
        restore_btn.state(["disabled"])
        status.set("복원 중… 잠시만 기다려 주세요.")
        box = []

        def work():
            box.append(remote.restore_backup(base, entry["name"]))

        threading.Thread(target=work, daemon=True, name="estimate-restore").start()
        dialog.after(150, lambda: finish(box, entry))

    def finish(box, entry):
        if not dialog.winfo_exists():
            return
        if not box:
            dialog.after(150, lambda: finish(box, entry))
            return
        info, error = box[0]
        if error is None:
            dialog.destroy()
            app.show_notice(f"✓ 복원 완료 — {entry.get('created_at', '')} 시점으로 되돌렸습니다. "
                            f"(직전 상태: {info.get('safety', '')})", "success", auto_hide=True)
            return
        restore_btn.state(["!disabled"])
        status.set("")
        if error == remote.REASON_LOCKED:
            messagebox.showwarning("백업 복원", "편집 권한이 풀렸습니다. 편집 암호를 다시 입력해 주세요.", parent=dialog)
        elif error == remote.REASON_UNREACHABLE:
            messagebox.showerror("백업 복원", "견적 서버에 연결하지 못했습니다. 복원이 끝났는지 확인하려면 목록을 다시 열어 주세요.",
                                 parent=dialog)
        else:
            detail = (info or {}).get("msg") if isinstance(info, dict) else ""
            messagebox.showerror("백업 복원", detail or "서버가 복원하지 못했습니다.", parent=dialog)

    restore_btn.configure(command=do_restore)
    tree.bind("<Double-1>", lambda _e: do_restore())
