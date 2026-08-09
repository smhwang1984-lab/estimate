"""작업 중이던 카드 목록을 JSON으로 저장해 두었다가 다음 실행 때 되살린다.

엑셀 양식은 입력/출력용으로만 쓰고, 화면 상태는 이 JSON에 따로 저장한다.
저장 위치는 %LOCALAPPDATA%\\MachineEstimate\\session_state.json 이라
설치 폴더 권한과 무관하게 항상 쓸 수 있다.

v0.1.4에서 데이터 폴더를 공유 폴더로 옮길 수 있게 됐지만, **이 파일은 로컬에 그대로 둔다.**
자동 저장이기 때문이다 — 종료할 때 쓰고 시작할 때 읽으므로, 두 사람이 같이 켜 두면
나중에 끈 쪽이 앞사람 작업을 말없이 덮어쓴다(자동이라 물어볼 자리조차 없다).
여러 PC가 견적을 주고받는 일은 `core/library.py`(견적 보관함)가 맡는다.
"""

import json
from datetime import datetime

from . import datastore, paths
from .model import create_blank_item, has_item_data

SESSION_FILE = "session_state.json"


def get_session_path():
    return paths.get_user_file(SESSION_FILE)


def save(items, selected_nos, search_text):
    # v0.0.9: 단가(rates)는 여기에 담지 않는다. 설정창(core/settings.py)이 단가의 유일한
    # 주인인데, 세션에도 담아 두면 프로그램을 켤 때 옛 세션 값이 새 설정을 덮어써 버린다.
    payload = {
        "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "selected_nos": sorted(selected_nos),
        "search": search_text,
        "items": [item for item in items if has_item_data(item)],
    }
    # v0.1.4: 로컬이지만 여기도 임시 파일 + 바꿔치기로 쓴다. 저장은 프로그램을 끄는
    # 순간에 일어나므로, 쓰는 도중에 전원이 끊기면 예전 방식으로는 세션이 통째로
    # 잘린 채 남는다(그러면 다음 실행에서 작업 목록이 사라진 것으로 보인다).
    return datastore.write_json_atomic(get_session_path(), payload)


def load():
    """저장된 세션을 읽어 dict로 돌려준다. 없거나 깨졌으면 None."""
    try:
        with open(get_session_path(), "r", encoding="utf-8") as state_file:
            payload = json.load(state_file)
    except (OSError, ValueError):
        return None
    items = []
    for raw_item in payload.get("items", []):
        item = create_blank_item(raw_item.get("no", 0))
        item.update(raw_item)
        items.append(item)
    return {
        "items": items,
        "selected_nos": set(payload.get("selected_nos", [])),
        "search": payload.get("search", ""),
        "saved_at": payload.get("saved_at"),
    }
