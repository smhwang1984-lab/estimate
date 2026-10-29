"""편집 암호 입력·설정 창 (v1.7.0).

- unlock(): 읽기 전용 PC가 암호를 입력해 편집 권한을 얻는다(프로그램을 끌 때까지 유지).
- open_password_settings(): 암호를 처음 정하거나 바꾸거나 해제한다([설정 > 데이터 위치]에서 연다).
암호 원문은 서버로 보내는 순간에만 쓰고 어디에도 저장하지 않는다.
"""

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from ..core import datastore, editlock, remote

_ERRORS = {
    remote.REASON_BAD_PASSWORD: "암호가 맞지 않습니다.",
    remote.REASON_THROTTLED: "암호를 여러 번 틀려 잠시 막혔습니다. 5분 뒤 다시 시도해 주세요.",
    remote.REASON_UNREACHABLE: "견적 서버에 연결하지 못했습니다.",
    remote.REASON_MISSING: "서버 버전이 낮아 편집 암호를 쓸 수 없습니다. 서버를 1.2.0 이상으로 올려 주세요.",
    remote.REASON_FORBIDDEN: "견적 서버가 접속을 거부했습니다(사내망/VPN 확인).",
}


def _error_text(error):
    return _ERRORS.get(error, "서버가 요청을 처리하지 못했습니다.")


def _busy(widget, func):
    widget.configure(cursor="watch")
    widget.update_idletasks()
    try:
        return func()
    finally:
        widget.configure(cursor="")


def unlock(app, parent=None):
    """암호를 물어 편집 권한을 얻는다. 얻었으면 True."""
    parent = parent or app.root
    if not datastore.location_is_server():
        return True
    password = simpledialog.askstring(
        "편집 암호", "수정·입력하려면 편집 암호를 입력하세요.\n(이 프로그램을 끌 때까지 유지됩니다)",
        show="*", parent=parent)
    if password is None:
        return False
    base = datastore.get_data_dir()
    token, error = _busy(parent, lambda: remote.login(base, password))
    if error:
        messagebox.showerror("편집 암호", _error_text(error), parent=parent)
        return False
    if not token:
        editlock.apply_server_state(False, "")
        app.update_edit_ui()
        messagebox.showinfo("편집 암호", "서버에 편집 암호가 설정되어 있지 않아 누구나 편집할 수 있습니다.", parent=parent)
        return True
    editlock.apply_server_state(True, editlock.rev_of(token))
    editlock.set_token(token)
    app.update_edit_ui()
    app.show_notice("🔓 편집 권한을 얻었습니다. 프로그램을 끌 때까지 유지됩니다.", "success", auto_hide=True)
    app.sync.schedule_push()   # 읽기 전용일 때 밀려 있던 자동 저장이 있으면 올린다
    return True


def open_password_settings(app, parent):
    """편집 암호를 정하거나 바꾸거나 해제하는 창."""
    if not datastore.location_is_server():
        messagebox.showinfo("편집 암호", "편집 암호는 견적 서버를 쓸 때만 설정할 수 있습니다.", parent=parent)
        return
    protected = editlock.is_protected()
    dialog = tk.Toplevel(parent)
    dialog.title("편집 암호 변경" if protected else "편집 암호 설정")
    dialog.transient(parent)
    dialog.resizable(False, False)
    dialog.configure(bg=app.theme.color("bg"))
    frame = ttk.Frame(dialog, padding=18)
    frame.pack(fill=tk.BOTH, expand=True)

    intro = ("암호를 아는 PC에서만 수정·입력이 가능하고, 나머지 PC는 읽기 전용(엑셀 출력은 가능)입니다.\n"
             "암호는 서버에 해시로만 저장되며, 잊으면 NAS에서 초기화해야 합니다.")
    ttk.Label(frame, text=intro, style="Muted.TLabel", justify="left", wraplength=420).grid(
        row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))

    current_var, new_var, again_var = tk.StringVar(), tk.StringVar(), tk.StringVar()
    rows = []
    if protected:
        rows.append(("현재 암호", current_var))
    rows += [("새 암호 (4자 이상)", new_var), ("새 암호 확인", again_var)]
    first = None
    for index, (label, var) in enumerate(rows, start=1):
        ttk.Label(frame, text=label).grid(row=index, column=0, sticky="w", pady=4, padx=(0, 12))
        entry = ttk.Entry(frame, textvariable=var, show="*", width=26)
        entry.grid(row=index, column=1, sticky="w", pady=4)
        first = first or entry

    def finish(token, message):
        editlock.apply_server_state(bool(token), editlock.rev_of(token))
        editlock.set_token(token)
        app.update_edit_ui()
        dialog.destroy()
        messagebox.showinfo("편집 암호", message, parent=parent)

    def submit(new_password):
        base = datastore.get_data_dir()
        token, error = _busy(dialog, lambda: remote.change_password(base, current_var.get(), new_password))
        if error:
            text = "현재 암호가 맞지 않습니다." if error == remote.REASON_BAD_PASSWORD else _error_text(error)
            messagebox.showerror("편집 암호", text, parent=dialog)
            return
        if new_password:
            finish(token, "편집 암호를 저장했습니다. 이 PC는 지금 편집할 수 있고, 다른 PC는 읽기 전용이 됩니다.")
        else:
            finish("", "편집 암호를 해제했습니다. 모든 PC가 다시 편집할 수 있습니다.")

    def save():
        new_password = new_var.get()
        if len(new_password) < 4:
            messagebox.showerror("편집 암호", "새 암호는 4자 이상이어야 합니다.", parent=dialog)
            return
        if new_password != again_var.get():
            messagebox.showerror("편집 암호", "새 암호와 확인이 서로 다릅니다.", parent=dialog)
            return
        submit(new_password)

    def clear():
        if not messagebox.askyesno("암호 해제", "편집 암호를 없애면 사내망의 모든 PC가 수정할 수 있게 됩니다.\n해제할까요?",
                                   default="no", parent=dialog):
            return
        submit("")

    buttons = ttk.Frame(frame)
    buttons.grid(row=len(rows) + 1, column=0, columnspan=2, sticky="e", pady=(14, 0))
    if protected:
        ttk.Button(buttons, text="암호 해제", command=clear).pack(side=tk.LEFT, padx=(0, 8))
    ttk.Button(buttons, text="취소", command=dialog.destroy).pack(side=tk.RIGHT, padx=(8, 0))
    ttk.Button(buttons, text="저장", command=save).pack(side=tk.RIGHT)

    dialog.update_idletasks()
    x = parent.winfo_rootx() + max(0, (parent.winfo_width() - dialog.winfo_width()) // 2)
    y = parent.winfo_rooty() + max(0, (parent.winfo_height() - dialog.winfo_height()) // 3)
    dialog.geometry(f"+{x}+{y}")
    dialog.bind("<Escape>", lambda event: dialog.destroy())
    dialog.bind("<Return>", lambda event: save())
    dialog.grab_set()
    if first is not None:
        first.focus_set()
