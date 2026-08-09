"""작업 중이던 카드 목록을 JSON으로 저장해 두었다가 다음 실행 때 되살린다.

엑셀 양식은 입력/출력용으로만 쓰고, 화면 상태는 이 JSON에 따로 저장한다.
저장 위치는 %LOCALAPPDATA%\\MachineEstimate\\session_state.json 이라
설치 폴더 권한과 무관하게 항상 쓸 수 있다.
"""

import json
import os
from datetime import datetime

from . import paths
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
    state_path = get_session_path()
    try:
        os.makedirs(os.path.dirname(state_path), exist_ok=True)
        with open(state_path, "w", encoding="utf-8") as state_file:
            json.dump(payload, state_file, ensure_ascii=False, indent=2)
        return True
    except OSError:
        return False


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
