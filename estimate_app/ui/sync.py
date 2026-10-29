"""실시간 동기화(v1.4.0) — 견적 서버를 쓸 때 여러 PC의 화면을 서로 맞춘다.

요청: "데이터가 바뀌면 다른 PC에도 즉시 반영돼야 한다." 데이터 위치가 서버일 때만 돈다
(폴더 모드에서는 아무것도 하지 않는다).

## 무엇을 맞추나

    설정(단가·소재·회사 정보·열 폭)
        다른 PC가 저장하면 곧바로 다시 읽어 화면(금액 포함)에 반영한다. 설정창이 열려 있으면
        그 창을 닫을 때 반영한다 — 고치는 중인 칸을 밑에서 바꾸지 않기 위해서다.
    지금 화면에 불러온 보관함 견적(app.library_current)
        보내기: 카드를 고칠 때마다(app.save_session을 부르는 모든 곳) 잠깐 기다렸다가 서버에
                자동 저장한다. 연달아 고치면 마지막 것 하나만 올린다(PUSH_DELAY_MS).
        받기:   다른 PC가 같은 견적을 저장하면, 이 PC에 아직 안 올린 변경이 없을 때만
                자동으로 다시 불러온다. 이 PC에도 변경이 있으면 알림 줄에서 고르게 한다
                ([서버 내용 불러오기] / [내 내용으로 덮어쓰기]) — 어느 쪽도 말없이 지우지 않는다.
    보관함 창의 목록
        열려 있으면 다른 PC의 저장·삭제를 바로 목록에 반영한다.

보관함에 한 번도 저장하지 않은 카드(library_current 없음)는 맞추지 않는다. 그건 아직 '이 PC의
작업'이다 — [견적 저장]으로 이름을 붙이는 순간부터 공유된다.

## 어떻게 아나 — 롱폴링

감시 스레드가 서버의 `/changes?since=<token>&wait=25`를 걸어 두면, 서버는 무언가 저장되는
순간 응답한다. 응답이 오면 '무엇이' 바뀌었는지는 설정 mtime과 내 견적의 mtime으로 따로
확인한다. 연결이 끊기면 2·5·10초 간격으로 다시 붙고, 붙는 순간 놓친 변경을 한꺼번에 맞춘다
(요청 D). 서버가 1.0.0이라 /changes가 없으면 알림만 한 번 띄우고 멈춘다.

## 화면에 보이는 것 (v1.5.0)

모든 상태는 화면 맨 아래 고정 높이 줄(dashboard의 동기화 줄)에 나온다. 줄이 새로 생기지 않아
표가 움직이지 않는다. 평소 상태(set_sync_status)는 이렇게 바뀐다.

    ● 변경사항 있음 — 자동 저장 대기: 품번 TS-1039 외 2건 수정      고치는 순간(노랑)
    서버에 저장 중…                                                보내는 동안
    ✓ 서버에 저장됨 14:03:21 — 품번 TS-1039 외 2건 수정             성공(초록, 다음 변경까지 유지)

'무엇이 바뀌었나'는 마지막으로 서버와 맞춘 시점의 카드 지문(self.baseline)과 지금 카드를 비교해
만든다. 다른 PC의 변경을 반영했을 때도 같은 방식으로 바뀐 품번을 알려 준다. 알림(show_notice)은
이 상태 위에 잠깐 덮어 쓰며, 사라지면 상태가 다시 보인다.

## 스레드

네트워크는 전부 백그라운드에서 하고, 화면은 Tk 스레드에서만 만진다. 둘 사이는 큐 하나
(events)로만 오간다. 서버에 쓰고 읽는 일(저장·불러오기·확인)은 작업 스레드 하나가 차례로
처리한다 — 내 자동 저장과 '남이 바꿨나' 확인이 엇갈려, 내 저장을 남의 변경으로 착각하지 않게
하기 위해서다(결과도 같은 순서로 화면에 도착한다).
"""

import json
import queue
import threading
import time
from copy import deepcopy
from datetime import datetime

from tkinter import messagebox

from ..core import datastore, editlock, library, remote, settings as settings_store
from ..core.model import has_item_data

WAIT_SECONDS = 25
PUSH_DELAY_MS = 800
POLL_MS = 150
RETRY_SECONDS = (2, 5, 10)
INFO_HIDE_MS = 8000


def _stamp(mtime):
    try:
        return datetime.fromtimestamp(int(mtime)).strftime("%H:%M:%S")
    except (TypeError, ValueError, OSError):
        return ""


class SyncManager:
    def __init__(self, app):
        self.app = app
        self.events = queue.Queue()
        self.tasks = queue.Queue()
        self.generation = 0
        self.stop_event = None
        self.polling = False
        self._reset_flags()

    def _reset_flags(self):
        self.connected = None          # None: 아직 모름 / True / False
        self.push_after_id = None
        self.push_running = False
        self.push_again = False
        self.conflict = False          # 내 변경과 남의 변경이 엇갈려 사용자 선택을 기다리는 중
        self.baseline = {}             # 서버와 마지막으로 맞춘 카드 지문 {no: (지문, 표시 이름)}
        self.pushing_summary = ""
        self.pending_settings = False  # 설정창이 닫히면 다시 읽을 것

    # ---------- 변경 내용 요약 (v1.5.0) ----------

    @staticmethod
    def _make_baseline(items):
        """저장 대상 카드의 {no: (내용 지문, 표시 이름)}. 화면용 배지(NEW 등)는 지문에서 뺀다."""
        out = {}
        for item in items:
            if not has_item_data(item):
                continue
            clean = {k: v for k, v in item.items() if k not in library._VOLATILE_KEYS}
            fingerprint = json.dumps(clean, ensure_ascii=False, sort_keys=True, default=str)
            if str(item.get("part_no") or "").strip():
                label = f"품번 {str(item['part_no']).strip()}"
            elif str(item.get("part_name") or "").strip():
                label = f"품명 {str(item['part_name']).strip()}"
            else:
                label = f"NO.{item.get('no')}"
            out[item["no"]] = (fingerprint, label)
        return out

    @staticmethod
    def _describe(old, new):
        """old/new 지문 표를 비교해 '품번 TS-1039 외 2건 수정' 같은 문장을 만든다. 같으면 ''."""
        modified = [no for no in new if no in old and new[no][0] != old[no][0]]
        added = [no for no in new if no not in old]
        removed = [no for no in old if no not in new]
        groups = [(kind, nos, new if kind != "삭제" else old)
                  for kind, nos in (("수정", modified), ("추가", added), ("삭제", removed)) if nos]
        if not groups:
            return ""
        if len(groups) == 1:
            kind, nos, source = groups[0]
            extra = f" 외 {len(nos) - 1}건" if len(nos) > 1 else ""
            return f"{source[nos[0]][1]}{extra} {kind}"
        return " · ".join(f"{kind} {len(nos)}건" for kind, nos, _ in groups)

    def reset_baseline(self):
        """화면이 보관함 견적을 새로 불러왔거나 저장했을 때(set_library_current) 기준점을 다시 잡는다."""
        if self.app.library_current:
            self.baseline = self._make_baseline(self.app.data)
        else:
            self.baseline = {}
        self.app.set_sync_status(None)

    def _pending_summary(self):
        if not self.baseline:
            return ""
        return self._describe(self.baseline, self._make_baseline(self.app.data))

    # ---------- 시작 / 멈춤 ----------

    def is_active(self):
        return self.stop_event is not None and not self.stop_event.is_set()

    def restart(self):
        """데이터 위치가 바뀌었을 때(설정 > 데이터 위치). 옛 스레드는 버리고 새로 시작한다."""
        if self.stop_event is not None:
            self.stop_event.set()
        if self.push_after_id is not None:
            try:
                self.app.root.after_cancel(self.push_after_id)
            except Exception:
                pass
        self._reset_flags()
        editlock.reset()   # 다른 서버(또는 로컬)로 옮기면 이전 서버의 편집 권한을 들고 가지 않는다
        self.stop_event = None
        self.app.hide_notice()
        self.app.update_edit_ui()
        self.start()

    def start(self):
        if self.is_active() or not datastore.location_is_server():
            return
        self.generation += 1
        stop = threading.Event()
        self.stop_event = stop
        base = datastore.load_location()["path"]
        gen = self.generation
        threading.Thread(target=self._watch_loop, args=(gen, stop, base),
                         daemon=True, name="estimate-watch").start()
        threading.Thread(target=self._task_loop, args=(gen, stop),
                         daemon=True, name="estimate-sync").start()
        if not self.polling:
            self.polling = True
            self.app.root.after(POLL_MS, self._poll)

    # ---------- 백그라운드 ----------

    def _watch_loop(self, gen, stop, base):
        token = ""
        failures = 0
        while not stop.is_set():
            started = time.monotonic()
            # 처음이거나 막 끊겼다 다시 묻는 참이면 기다리지 않고 바로 답을 받는다 — 서버 값이 그대로면
            # 서버가 25초를 꽉 채워 붙잡아서 '다시 연결됨'이 그만큼 늦게 뜬다.
            wait = WAIT_SECONDS if token and not failures else 0
            body, error = remote.wait_changes(base, token, wait)
            if stop.is_set():
                return
            if error == remote.REASON_MISSING:
                self.events.put((gen, "unsupported", None))
                return
            if error:
                failures += 1
                self.events.put((gen, "disconnected", error))
                stop.wait(RETRY_SECONDS[min(failures, len(RETRY_SECONDS)) - 1])
                continue
            if failures or not token:
                self.events.put((gen, "connected", body))
            elif body["token"] != token:
                self.events.put((gen, "changed", body))
            elif time.monotonic() - started < 1.0:
                # 서버가 기다려 주지 않았다(동시 대기 한도). 잠깐 쉬었다 묻는다 — 폴링으로 내려앉는다.
                stop.wait(3)
            failures = 0
            token = body["token"]

    def _task_loop(self, gen, stop):
        while not stop.is_set():
            try:
                kind, func = self.tasks.get(timeout=0.5)
            except queue.Empty:
                continue
            try:
                result = func()
            except Exception as exc:  # 동기화 실패가 프로그램을 멈추면 안 된다
                result = exc
            self.events.put((gen, kind, result))

    def _submit(self, kind, func):
        if self.is_active():
            self.tasks.put((kind, func))

    # ---------- 화면 쪽(Tk 스레드) ----------

    def _poll(self):
        try:
            while True:
                gen, kind, data = self.events.get_nowait()
                if gen != self.generation or not self.is_active():
                    continue
                handler = getattr(self, f"_on_{kind}", None)
                if handler is not None:
                    try:
                        handler(data)
                    except Exception as exc:
                        print(f"[sync] {kind} handler failed: {exc}", flush=True)
        except queue.Empty:
            pass
        if editlock.consume_revoked_event():
            self.app.update_edit_ui()
            self.app.show_notice("🔒 편집 암호가 바뀌어 읽기 전용으로 돌아갔습니다. 새 암호를 입력해 주세요.",
                                 "warn", auto_hide=True)
        if self.pending_settings and self.app.settings_window is None:
            self.pending_settings = False
            self._reload_settings("remote")
        try:
            self.app.root.after(POLL_MS, self._poll)
        except Exception:
            self.polling = False

    def _set_connected(self, ok, reason=None):
        datastore.set_server_reachable(ok, reason)
        self.app.data_state = datastore.get_state()
        self.app.update_summary_text()

    def _on_unsupported(self, _data):
        self.app.show_notice(
            "견적 서버가 1.0.0이라 실시간 동기화를 쓸 수 없습니다. NAS의 서버를 1.1.0 이상으로 업데이트하세요.",
            "warn")

    def _on_disconnected(self, reason):
        if self.connected is False:
            return
        self.connected = False
        self._set_connected(False, reason)
        if reason == remote.REASON_FORBIDDEN:
            text = "● 견적 서버가 접속을 거부했습니다(사내망/VPN 확인). 연결되면 자동으로 다시 붙습니다."
        else:
            text = "● 서버 연결 끊김 — 자동으로 다시 연결하는 중. 고친 내용은 이 PC에 보관했다가 연결되면 올립니다."
        self.app.show_notice(text, "danger")

    def _check_edit_state(self, body):
        """서버가 알려 준 편집 암호 상태를 반영한다(다른 PC가 암호를 켜고 끄고 바꾸는 것도 곧바로 반영)."""
        if not isinstance(body, dict) or "protected" not in body:
            return
        before = (editlock.is_protected(), editlock.can_edit())
        outcome = editlock.apply_server_state(body.get("protected"), body.get("edit_rev"))
        if outcome == "revoked":
            self.app.show_notice("🔒 편집 암호가 바뀌어 읽기 전용으로 돌아갔습니다. 새 암호를 입력해 주세요.",
                                 "warn", auto_hide=True)
        if before != (editlock.is_protected(), editlock.can_edit()):
            self.app.update_edit_ui()

    def _on_connected(self, body):
        self._check_edit_state(body)
        was_down = self.connected is False
        first = self.connected is None
        self.connected = True
        self._set_connected(True)
        if was_down:
            self.app.show_notice("견적 서버에 다시 연결됐습니다.", "success", auto_hide=True)
        # 처음 붙었을 때·다시 붙었을 때 모두, 그사이 놓친 변경을 한꺼번에 맞춘다.
        load_error = settings_store.get_load_error() or self.app.settings_load_error
        if load_error and not self.app.settings_loading:
            self._reload_settings("recovered")
        else:
            self._check_settings(body)
        self._check_library()
        if not first or self.app.library_dirty():
            self.schedule_push()
        self._refresh_library_window()

    def _on_changed(self, body):
        self._check_edit_state(body)
        self._check_settings(body)
        self._check_library()
        self._refresh_library_window()

    # ---------- 설정 ----------

    def _check_settings(self, body):
        server_mtime = body.get("settings_mtime") or 0
        known = settings_store.get_loaded_mtime()
        if known is None or server_mtime == (known or 0) or self.app.settings_loading:
            return
        if self.app.settings_window is not None:
            # 설정창에서 고치는 중이다. 밑에서 값을 바꾸지 않고, 닫히면 반영한다.
            self.pending_settings = True
            self.app.show_notice("다른 PC에서 설정을 바꿨습니다. 설정창을 닫으면 반영합니다.", "warn")
            return
        self._reload_settings("remote")

    def _reload_settings(self, why):
        def work():
            loaded = settings_store.load()
            return loaded, settings_store.get_load_error(), why
        self._submit("settings_loaded", work)

    def _on_settings_loaded(self, result):
        if isinstance(result, Exception):
            return
        loaded, error, why = result
        if error:
            return
        if self.app.settings_window is not None:
            self.pending_settings = True
            return
        self.app.settings_load_error = None
        self.app.col_widths = dict(loaded.get("col_widths", {}))
        self.app.col_width_overridden = set(self.app.col_widths.keys())
        self.app.apply_settings(loaded)
        if why == "recovered":
            self.app.show_notice("서버 설정을 다시 읽어 반영했습니다. 이제 설정을 저장할 수 있습니다.",
                                 "success", auto_hide=True)
        else:
            self.app.show_notice("다른 PC에서 바꾼 설정(단가·소재 등)을 반영했습니다. 금액도 다시 계산했습니다.",
                                 "success", auto_hide=True)

    # ---------- 보관함 견적: 받기 ----------

    def _current_server_entry(self):
        current = self.app.library_current
        if not current or not library.is_server_path(current.get("path")):
            return None
        return dict(current)

    def _check_library(self):
        current = self._current_server_entry()
        if current is None:
            return
        path = current["path"]
        self._submit("library_checked", lambda: (path, library.peek_mtime(path)))

    def _on_library_checked(self, result):
        if isinstance(result, Exception):
            return
        path, (mtime, error) = result
        current = self._current_server_entry()
        if current is None or current["path"] != path:
            return
        if error == remote.REASON_MISSING:
            self.app.set_library_current(None)
            self.app.save_session()
            self.app.show_notice(
                f"'{current['title']}'이 다른 PC에서 삭제됐습니다. 카드는 그대로 두고 자동 저장을 멈췄습니다."
                f" 계속하려면 [견적 저장]으로 다시 저장하세요.", "warn")
            return
        if error or mtime is None or mtime == current.get("mtime"):
            return
        if self.app.library_dirty() or self.app.open_popups:
            self._enter_conflict(current, mtime)
            return
        self._load_remote(path)

    def _load_remote(self, path):
        self._submit("library_loaded", lambda: (path, library.load_entry(path)))

    def _on_library_loaded(self, result):
        if isinstance(result, Exception):
            return
        path, (payload, error) = result
        current = self._current_server_entry()
        if error or current is None or current["path"] != path:
            return
        if payload.get("mtime") == current.get("mtime") and not self.app.library_dirty():
            return  # 변경 알림이 겹쳐 같은 버전을 두 번 받았다. 이미 반영했으니 알림도 다시 띄우지 않는다.
        # 바뀐 품번은 화면을 갈아 끼우기 전의 카드와 비교해야 알 수 있다.
        summary = self._describe(self._make_baseline(self.app.data), self._make_baseline(payload["items"]))
        if not self.app.apply_library_entry(payload, path, quiet=True):
            self._enter_conflict(current, payload["mtime"])
            return
        self.conflict = False
        who = payload.get("saved_by") or "다른 PC"
        detail = f" — {summary}" if summary else ""
        self.app.show_notice(
            f"{who}가 '{payload['title']}'을 수정해 반영했습니다 ({_stamp(payload['mtime'])}){detail}",
            "success", auto_hide=True)

    def _enter_conflict(self, current, server_mtime):
        self.conflict = True
        title = current["title"]
        if self.app.open_popups and not self.app.library_dirty():
            text = (f"다른 PC가 '{title}'을 수정했습니다({_stamp(server_mtime)}). 입력창이 열려 있어"
                    f" 반영하지 않았습니다. 닫은 뒤 [서버 내용 불러오기]를 누르세요.")
        else:
            text = (f"다른 PC가 '{title}'을 수정했고({_stamp(server_mtime)}) 이 PC에도 안 올린 변경이 있습니다."
                    f" 어느 쪽을 남길지 고르세요.")
        self.app.show_notice(text, "warn", actions=[
            ("서버 내용 불러오기", self.take_server),
            ("내 내용으로 덮어쓰기", self.keep_mine),
        ])

    def take_server(self):
        current = self._current_server_entry()
        if current is None:
            return
        if self.app.open_popups:
            messagebox.showwarning("불러올 수 없음", "항목 입력창을 모두 닫은 뒤 다시 눌러 주세요.",
                                   parent=self.app.root)
            return
        if self.app.library_dirty() and not messagebox.askyesno(
                "서버 내용 불러오기",
                f"이 PC에서 고친 내용을 버리고 서버의 '{current['title']}'으로 바꿉니다. 계속할까요?",
                default="no", parent=self.app.root):
            return
        self.app.hide_notice()
        self._load_remote(current["path"])

    def keep_mine(self):
        current = self._current_server_entry()
        if current is None:
            return
        if not messagebox.askyesno(
                "내 내용으로 덮어쓰기",
                f"다른 PC가 저장한 '{current['title']}'을 이 PC의 내용으로 덮어씁니다."
                f" 다른 PC의 변경은 사라집니다. 계속할까요?",
                default="no", parent=self.app.root):
            return
        self.app.hide_notice()
        path = current["path"]

        def work():
            mtime, error = library.peek_mtime(path)
            if error and error != remote.REASON_MISSING:
                return None, error
            return mtime, None
        self._submit("overwrite_base", work)

    def _on_overwrite_base(self, result):
        if isinstance(result, Exception):
            return
        mtime, error = result
        if error:
            self.app.show_notice(f"서버의 지금 상태를 읽지 못했습니다. ({datastore.describe()})", "danger")
            return
        current = self._current_server_entry()
        if current is None:
            return
        # 서버의 지금 값을 기준으로 다시 보낸다. 그사이 또 누가 저장했으면 다시 충돌로 돌아온다.
        self.app.library_current["mtime"] = mtime
        self.conflict = False
        self.schedule_push(force=True)

    # ---------- 보관함 견적: 보내기 ----------

    def schedule_push(self, force=False):
        """카드가 바뀌었다(app.save_session에서 부른다). 잠깐 모았다가 서버에 올린다."""
        if not self.is_active() or self.conflict or self._current_server_entry() is None:
            return
        if not self.app.can_edit():
            return   # v1.7.0: 읽기 전용 PC는 자동 저장을 올리지 않는다
        if not force and not self.app.library_dirty():
            return
        if self.push_after_id is not None:
            try:
                self.app.root.after_cancel(self.push_after_id)
            except Exception:
                pass
        summary = self._pending_summary()
        self.app.set_sync_status("● 변경사항 있음 — 자동 저장 대기" + (f": {summary}" if summary else ""), "warn")
        self.push_after_id = self.app.root.after(PUSH_DELAY_MS, lambda: self._push(force))

    def _push(self, force=False):
        self.push_after_id = None
        current = self._current_server_entry()
        if current is None or self.conflict or self.connected is False:
            return
        if not force and not self.app.library_dirty():
            return
        if self.push_running:
            self.push_again = True
            return
        items = deepcopy(self.app.data)
        signature = library.content_signature(items)
        self.pushing_summary = self._pending_summary()
        self.app.set_sync_status("서버에 저장 중…", "info")
        self.push_running = True

        def work():
            result = library.save_entry(current["title"], items, path=current["path"],
                                        base_mtime=current.get("mtime"))
            return current, signature, result, library.get_last_error(), items
        self._submit("pushed", work)

    def _on_pushed(self, data):
        self.push_running = False
        if isinstance(data, Exception):
            return
        sent, signature, result, error, items = data
        current = self._current_server_entry()
        if current is None or current["path"] != sent["path"]:
            return
        if result is not None:
            self.app.library_current.update({"mtime": result["mtime"], "sig": signature})
            self.baseline = self._make_baseline(items)
            self.app.save_session(sync=False)
            detail = f" — {self.pushing_summary}" if self.pushing_summary else ""
            self.app.set_sync_status(f"✓ 서버에 저장됨 {datetime.now():%H:%M:%S}{detail}", "success")
            if self.push_again or self.app.library_dirty():
                self.push_again = False
                self.schedule_push()
            return
        self.push_again = False
        if error == remote.REASON_LOCKED:
            self.app.update_edit_ui()
            self.app.set_sync_status("🔒 읽기 전용 — 편집 암호를 입력해야 서버에 저장됩니다", "warn")
            return
        if error == remote.REASON_CONFLICT:
            def work():
                return library.peek_mtime(sent["path"])
            self._submit("conflict_detected", work)
            return
        # 못 닿은 경우: 연결 감시가 '끊김'을 띄우고 다시 붙을 때 schedule_push로 올린다. 서버가
        # 살아 있는데 저장만 실패했을 때(서버 오류)는 감시가 모르므로 여기서 직접 다시 시도한다.
        self.app.set_sync_status("● 서버에 저장하지 못했습니다 — 5초 뒤 다시 시도합니다", "danger")
        self.app.root.after(5000, self.schedule_push)

    def _on_conflict_detected(self, result):
        current = self._current_server_entry()
        if current is None or isinstance(result, Exception):
            return
        mtime, error = result
        if error == remote.REASON_MISSING:
            self._on_library_checked((current["path"], (None, remote.REASON_MISSING)))
            return
        self._enter_conflict(current, mtime)

    # ---------- 보관함 창 ----------

    def _refresh_library_window(self):
        window = getattr(self.app, "library_window", None)
        refresh = getattr(window, "sync_refresh", None) if window is not None else None
        if refresh is not None:
            try:
                if window.winfo_exists():
                    refresh()
            except Exception:
                pass
