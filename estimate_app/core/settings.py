"""설정창에서 고친 값을 담아 두는 저장소(v0.0.9 신설).

저장 위치는 `%LOCALAPPDATA%\\MachineEstimate\\settings.json` 이다.
설치 폴더({app})는 Program Files라 일반 사용자 권한으로 쓸 수 없어서, 사용자가 화면에서
고치는 값은 전부 여기로 보낸다(세션 파일과 같은 자리).

이 파일이 없거나 망가져도 프로그램이 뜨지 않는 일이 없도록, 코드 안의 기본값 위에
파일 내용을 덮어쓰는 방식으로 읽는다(config.py와 같은 규칙).

담는 값
    rates             공정별 단가. v0.0.9부터 여기가 단가의 유일한 주인이다.
                      (카드 팝업에서는 고칠 수 없는 고정값으로 보여 준다 — 요청 6-2)
    materials         Material 선택 목록. 카드에서 콤보박스로 고른다.
    company           견적을 내는 우리 회사 정보. 기계 시트 푸터에 들어간다.
    client            견적을 받는 상대 업체 정보. 견적서 시트 왼쪽 위에 들어간다.
    supplier          견적서 시트 오른쪽 위(대표자/사업자번호/주소/전화/담당자).

client / supplier 값은 라벨을 뺀 알맹이만 담는다. 예를 들어 `client.dept`에 `구매팀`만
넣어 두면 저장할 때 코드가 `  부   서 : 구매팀` 형태로 조립한다 — 사용자가 매번
`부   서 :` 같은 양식 문구까지 다시 적지 않아도 되게 하기 위해서다.
"""

import json
import os

from . import paths
from .config import DEFAULT_RATES

SETTINGS_FILE = "settings.json"

# 회사명/작성자 기본값은 요청서(v0.0.9.md 3-5)의 표기를 그대로 쓴다.
DEFAULT_COMPANY = {
    "name": "(주)텍스타",
    "writer_title": "생산부장",
    "writer_name": "황성문",
}

# 견적서 왼쪽 위(견적을 받는 업체). 값은 양식의 기존 문구에서 라벨을 뺀 것이다.
DEFAULT_CLIENT = {
    "name": "회사명㈜",
    "manager": "대상업체 담당자 직위",
    "dept": "구매팀",
    "project": "사업명",
}

# 견적서 오른쪽 위(견적을 내는 우리 쪽 연락처). 양식에 이미 적혀 있던 값을 기본값으로 둔다.
DEFAULT_SUPPLIER = {
    "ceo": "김종호 대표이사",
    "biz_no": "000-00-00000",
    "address": "경남 진주시 뿌리산단로 15번길24",
    "phone": "055-761-3767",
    "contact": "김병환 이사",
}

# 기존 견적 파일 18개의 Material 열을 실제로 읽어 많이 쓰인 순서로 추린 목록이다.
# 설정창에서 추가·삭제할 수 있다.
DEFAULT_MATERIALS = [
    "KS D 3752, SM45C",
    "AL6061P-T62, T651",
    "AL6061P-T651",
    "AL6061-T651",
    "AL6061-T6",
    "AL7075-T651",
    "AL7075-T6",
    "AL2024-T3",
    "ASTM A516 Grade 70",
    "KS D 3706의 STS630",
    "STS630",
    "STS304",
    "KS D 3867, SCM440",
    "KS D 3503의 SS275",
    "STD61",
    "Ti-6AL-4V SAE-AMS4911",
    "PEEK",
]


def get_settings_path():
    return paths.get_user_file(SETTINGS_FILE)


def _merged(defaults, override):
    merged = dict(defaults)
    if isinstance(override, dict):
        for key, value in override.items():
            if key in merged:
                merged[key] = value
    return merged


def _clean_materials(values):
    """빈 값과 중복을 걸러 낸다. 사용자가 적은 순서는 그대로 지킨다."""
    if not isinstance(values, list):
        return list(DEFAULT_MATERIALS)
    cleaned = []
    for value in values:
        text = str(value).strip()
        if text and text not in cleaned:
            cleaned.append(text)
    return cleaned


def load():
    """저장된 설정을 읽어 온다. 파일이 없거나 깨졌으면 기본값 그대로 돌려준다."""
    payload = {}
    try:
        with open(get_settings_path(), "r", encoding="utf-8") as handle:
            loaded = json.load(handle)
        if isinstance(loaded, dict):
            payload = loaded
    except (OSError, ValueError):
        payload = {}

    rates = _merged(DEFAULT_RATES, payload.get("rates"))
    for key, value in rates.items():
        # 단가를 문자열로 적어 두는 실수를 대비해 숫자로 바꿔 둔다.
        try:
            rates[key] = float(value)
        except (TypeError, ValueError):
            rates[key] = float(DEFAULT_RATES[key])

    return {
        "rates": rates,
        "materials": _clean_materials(payload.get("materials", DEFAULT_MATERIALS)),
        "company": _merged(DEFAULT_COMPANY, payload.get("company")),
        "client": _merged(DEFAULT_CLIENT, payload.get("client")),
        "supplier": _merged(DEFAULT_SUPPLIER, payload.get("supplier")),
    }


def save(data):
    """설정을 파일로 남긴다. 저장에 실패하면 False."""
    payload = {
        "rates": {key: float(value) for key, value in data["rates"].items()},
        "materials": _clean_materials(data.get("materials")),
        "company": _merged(DEFAULT_COMPANY, data.get("company")),
        "client": _merged(DEFAULT_CLIENT, data.get("client")),
        "supplier": _merged(DEFAULT_SUPPLIER, data.get("supplier")),
    }
    path = get_settings_path()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        return True
    except OSError:
        return False


def writer_line(company):
    """기계 시트 푸터에 들어갈 `직위 이름` 한 줄. 한쪽이 비어도 공백이 남지 않게 만든다."""
    parts = [str(company.get("writer_title", "")).strip(),
             str(company.get("writer_name", "")).strip()]
    return " ".join(part for part in parts if part)
