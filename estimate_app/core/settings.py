"""설정창에서 고친 값을 담아 두는 저장소(v0.0.9 신설).

저장 위치는 기본이 `%LOCALAPPDATA%\\MachineEstimate\\settings.json` 이다.
설치 폴더({app})는 Program Files라 일반 사용자 권한으로 쓸 수 없어서, 사용자가 화면에서
고치는 값은 전부 여기로 보낸다.

v0.1.4부터는 사용자가 설정창에서 데이터 폴더를 공유 폴더로 바꿀 수 있다
(`core/datastore.py`). 여러 PC가 같은 단가·소재 기준을 보게 하려는 것이다.
그래서 이 파일이 **네트워크 너머에 있을 수 있고**, 아래 두 가지가 v0.1.4에서 추가됐다.

    1. 읽기 실패를 구분한다. '파일 없음'(처음 쓰는 정상 상태)과 '경로에 못 닿음'은
       전혀 다르다. 못 닿았는데 기본값으로 시작했다가 사용자가 뭔가 저장하면,
       공유 settings.json이 모두에게 기본값으로 덮어써진다. 그래서 못 닿은 뒤에는
       save()가 아예 거부한다(`get_load_error()`로 이유를 알려 준다).
    2. 저장은 임시 파일 + 이름 바꿔치기로 한다(datastore.write_json_atomic).
       쓰는 도중 연결이 끊겨도 잘린 파일이 남지 않는다.

이 파일이 없거나 망가져도 프로그램이 뜨지 않는 일이 없도록, 코드 안의 기본값 위에
파일 내용을 덮어쓰는 방식으로 읽는다(config.py와 같은 규칙).

담는 값
    rates             공정별 단가. v0.0.9부터 여기가 단가의 유일한 주인이다.
                      (카드 팝업에서는 고칠 수 없는 고정값으로 보여 준다 — 요청 6-2)
    materials         Material 선택 목록. 카드에서 콤보박스로 고른다.
    company           견적을 내는 우리 회사 정보. 기계 시트 푸터에 들어간다.
    client            견적을 받는 상대 업체 정보. 견적서 시트 왼쪽 위에 들어간다.
    supplier          견적서 시트 오른쪽 위(대표자/사업자번호/주소/전화/담당자).
    densities         v0.1.0 신설. 소재 비중(g/cm³) 목록 — 카드에서 무게를 계산할 때 쓴다
                      (요청 4). 설정창에서 추가·수정·삭제한다.
    col_widths        v0.1.0 신설. 현황판 표의 열 폭(요청 3-3). 사용자가 헤더 구분선을
                      끌어 조절한 값을 기억해 다음에 켤 때도 그대로 연다.
    lathe_machine     v0.1.1 신설. 가공조건 산출기(Lathe) 장비 스펙 — 정격 동력·최고
                      회전수·이름. 04.hta의 PUMA 2600Y(22kW/3500RPM)가 기본값이다.
    mill_machine      v0.1.1 신설. 가공조건 산출기(Mill) 장비 스펙. 01.hta에는 계산식이
                      없어 참고할 값이 없다 — 잠정 기본값(15kW/12000RPM)이다.
    lathe_materials   v0.1.1 신설. Lathe 재질별 kc·권장 절삭조건·추천 인서트 9행.
                      04.hta의 값을 그대로 옮겼다.
    mill_materials    v0.1.1 신설. Mill 재질별 kc·권장 절삭조건 9행. 참고할 원본이 없어
                      잠정치를 넣었다(plan.md 2026-08-09 v0.1.1 "확인이 필요한 것" 참고).

client / supplier 값은 라벨을 뺀 알맹이만 담는다. 예를 들어 `client.dept`에 `구매팀`만
넣어 두면 저장할 때 코드가 `  부   서 : 구매팀` 형태로 조립한다 — 사용자가 매번
`부   서 :` 같은 양식 문구까지 다시 적지 않아도 되게 하기 위해서다.
"""

from . import datastore
from .config import DEFAULT_RATES

SETTINGS_FILE = "settings.json"

# 마지막 load()가 '경로에 못 닿아' 기본값을 돌려줬는가. 여기 값이 남아 있는 동안은
# save()가 거부한다 — 읽지 못한 값을 되쓰면 공유 파일이 기본값으로 날아간다.
_load_error = None

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

# 소재 비중(g/cm³) 기본값(요청 4-2). 목록의 소재 이름이 `AL6061P-T62, T651` /
# `AL6061P-T651` / `AL6061-T651` / `AL6061-T6`처럼 같은 재질을 여러 표기로 담고 있어,
# 이름 전체를 열쇠로 쓰지 않고 재질 키워드로 찾는다(resolve_density 참고). 통용되는
# 물성값이지만 실제 견적 금액에 들어가는 값이라 사용자 확인을 받고 넣었다(2026-08-09).
DEFAULT_DENSITIES = [
    {"name": "SM45C", "density": 7.85},
    {"name": "SCM440", "density": 7.85},
    {"name": "STD61", "density": 7.85},
    {"name": "SS275", "density": 7.85},
    {"name": "A516", "density": 7.85},
    {"name": "STS304", "density": 7.93},
    {"name": "STS630", "density": 7.78},
    {"name": "AL6061", "density": 2.70},
    {"name": "AL7075", "density": 2.81},
    {"name": "AL2024", "density": 2.78},
    {"name": "Ti-6AL-4V", "density": 4.43},
    {"name": "PEEK", "density": 1.30},
]

# 현황판 표의 기본 열 폭(px). theme.json의 layout 값과 같은 순서다(요청 3-3).
# 사용자가 헤더 구분선을 끌어 고치면 여기 대신 settings.json에 저장된 값이 쓰인다.
DEFAULT_COL_WIDTHS = {}

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
DEFAULT_HEADERS = {
    "model": "기종",
    "part_no": "품번",
    "part_name": "품명",
    "comment": "Coment",
    "possible": "가능여부",
    "qty": "Qty",
    "material": "Material",
    "size": "Size",
    "heat": "열처리",
}

# v0.1.1: 가공조건 산출기(Mill/Lathe) 기본값. `core/machining.py`가 계산만 하고,
# 어떤 장비·재질을 쓰는지는 여기(설정)가 정한다 -- v0.1.0의 densities와 같은 자리다.

# Lathe 장비 스펙. 04.hta에 적힌 PUMA 2600Y(DN솔루션) 그대로다.
DEFAULT_LATHE_MACHINE = {"name": "PUMA 2600Y", "power": 22.0, "max_rpm": 3500.0}
# Mill 장비 스펙. 01.hta에는 계산식 자체가 없어 참고할 장비 정보도 없다 -- 잠정값이다.
DEFAULT_MILL_MACHINE = {"name": "", "power": 15.0, "max_rpm": 12000.0}

# Lathe 재질표. kc(비절삭저항)·권장 절삭조건(v/f/ap/max_rpm)·추천 인서트(대구텍
# CNMG120408)까지 04.hta의 9개 <option>과 recommendations/insertGrades를 그대로 옮겼다.
# `keywords`는 04.hta에는 없던 값이다 -- 카드의 Material 문자열(예: "KS D 3752, SM45C")과
# 매칭하기 위해 새로 붙였다. densities처럼 화학 기호 위주로 짧게 잡았다(resolve_machining_material
# 참고). 못 찾으면 사용자가 직접 고른다 -- 추측해서 고르지 않는다.
DEFAULT_LATHE_MATERIALS = [
    {"name": "알루미늄 (Al)", "keywords": ["AL6061", "AL7075", "AL2024", "알루미늄"],
     "kc": 700, "v": 350, "f": 0.30, "ap": 3.0, "max_rpm": 3500,
     "insert_grade": "TH10", "insert_coat": "비코팅 초경 (Uncoated Carbide)",
     "insert_iso": "ISO N · K10", "insert_desc": "비철금속 전용 · 알루미늄 고속 가공 최적"},
    {"name": "주철 (FC/FCD)", "keywords": ["FC200", "FCD450", "주철"],
     "kc": 1350, "v": 200, "f": 0.28, "ap": 2.8, "max_rpm": 2500,
     "insert_grade": "TT7015", "insert_coat": "CVD 다층 코팅",
     "insert_iso": "ISO K · K10~K25", "insert_desc": "주철 FC/FCD 전용 · 내마모성 우수"},
    {"name": "탄소강/구조용강 (S45C)", "keywords": ["SM45C", "S45C", "SS275"],
     "kc": 1800, "v": 220, "f": 0.28, "ap": 2.8, "max_rpm": 2500,
     "insert_grade": "TT8125", "insert_coat": "CVD TiCN/Al₂O₃/TiN",
     "insert_iso": "ISO P · P15~P30", "insert_desc": "탄소강/구조용강 황삭~중삭 범용"},
    {"name": "티타늄 (Ti6Al4V)", "keywords": ["TI-6AL-4V", "TI6AL4V", "티타늄"],
     "kc": 1950, "v": 70, "f": 0.22, "ap": 1.8, "max_rpm": 1200,
     "insert_grade": "TT9030", "insert_coat": "PVD TiAlN 코팅",
     "insert_iso": "ISO S · S05~S20", "insert_desc": "Ti6Al4V 티타늄 전용 · 내용착성 최우선"},
    {"name": "합금강/금형강 (SCM)", "keywords": ["SCM440", "SCM415", "STD61"],
     "kc": 2200, "v": 170, "f": 0.25, "ap": 2.3, "max_rpm": 2000,
     "insert_grade": "TT5100", "insert_coat": "CVD TiCN/Al₂O₃",
     "insert_iso": "ISO P · P20~P35", "insert_desc": "합금강/금형강 황삭 전용 · 고인성"},
    {"name": "스테인리스강 (SUS304)", "keywords": ["STS304", "SUS304", "STS630"],
     "kc": 2400, "v": 130, "f": 0.23, "ap": 1.6, "max_rpm": 1500,
     "insert_grade": "TT9215", "insert_coat": "PVD TiAlN 코팅",
     "insert_iso": "ISO M · M05~M20", "insert_desc": "SUS304 스테인리스 중삭~정삭"},
    {"name": "열처리강 (HRC 40~)", "keywords": ["HRC", "열처리강"],
     "kc": 2750, "v": 60, "f": 0.18, "ap": 1.4, "max_rpm": 1000,
     "insert_grade": "TT8125", "insert_coat": "CVD TiCN/Al₂O₃/TiN",
     "insert_iso": "ISO P/H · P15~P30", "insert_desc": "열처리강 HRC40~ · 초경 카바이드 한계 범위"},
    {"name": "인코넬 / 내열합금", "keywords": ["INCONEL", "인코넬"],
     "kc": 3100, "v": 35, "f": 0.12, "ap": 1.2, "max_rpm": 500,
     "insert_grade": "TT7005", "insert_coat": "PVD TiAlN 코팅",
     "insert_iso": "ISO S · S05~S20", "insert_desc": "인코넬/초내열합금 난삭재 전용"},
    {"name": "청동 (Bronze)", "keywords": ["BRONZE", "청동", "BC6"],
     "kc": 780, "v": 200, "f": 0.25, "ap": 3.0, "max_rpm": 3000,
     "insert_grade": "TH10", "insert_coat": "비코팅 초경 (Uncoated Carbide)",
     "insert_iso": "ISO N · K10", "insert_desc": "청동/비철 전용 · 비코팅 K계열 최적"},
]

# Mill 재질표. 참고할 원본(01.hta)에 계산식이 없어 실측치가 아니다 -- 초경 엔드밀
# Ø10 4날 기준으로 잡은 잠정값이며, 화면에도 잠정치라고 적는다(plan.md 2026-08-09
# v0.1.1 "확인이 필요한 것" 1번). kc는 Lathe 표와 같은 값(재질의 비절삭저항은 가공
# 방식과 무관하다)을 쓰고, keywords도 Lathe 표와 같은 값을 쓴다.
DEFAULT_MILL_MATERIALS = [
    {"name": "알루미늄 (Al)", "keywords": ["AL6061", "AL7075", "AL2024", "알루미늄"],
     "kc": 700, "vc": 300, "fz": 0.10, "ap": 5.0, "ae": 5.0},
    {"name": "주철 (FC/FCD)", "keywords": ["FC200", "FCD450", "주철"],
     "kc": 1350, "vc": 150, "fz": 0.10, "ap": 3.0, "ae": 5.0},
    {"name": "탄소강/구조용강 (S45C)", "keywords": ["SM45C", "S45C", "SS275"],
     "kc": 1800, "vc": 120, "fz": 0.08, "ap": 2.0, "ae": 5.0},
    {"name": "티타늄 (Ti6Al4V)", "keywords": ["TI-6AL-4V", "TI6AL4V", "티타늄"],
     "kc": 1950, "vc": 50, "fz": 0.05, "ap": 1.0, "ae": 3.0},
    {"name": "합금강/금형강 (SCM)", "keywords": ["SCM440", "SCM415", "STD61"],
     "kc": 2200, "vc": 100, "fz": 0.07, "ap": 2.0, "ae": 4.0},
    {"name": "스테인리스강 (SUS304)", "keywords": ["STS304", "SUS304", "STS630"],
     "kc": 2400, "vc": 80, "fz": 0.06, "ap": 1.5, "ae": 4.0},
    {"name": "열처리강 (HRC 40~)", "keywords": ["HRC", "열처리강"],
     "kc": 2750, "vc": 45, "fz": 0.04, "ap": 1.0, "ae": 2.0},
    {"name": "인코넬 / 내열합금", "keywords": ["INCONEL", "인코넬"],
     "kc": 3100, "vc": 25, "fz": 0.03, "ap": 0.8, "ae": 2.0},
    {"name": "청동 (Bronze)", "keywords": ["BRONZE", "청동", "BC6"],
     "kc": 780, "vc": 180, "fz": 0.08, "ap": 3.0, "ae": 5.0},
]

LATHE_MATERIAL_NUMERIC_FIELDS = ["kc", "v", "f", "ap", "max_rpm"]
MILL_MATERIAL_NUMERIC_FIELDS = ["kc", "vc", "fz", "ap", "ae"]


def get_settings_path():
    """지금 쓰는 settings.json의 실제 경로. 공유 폴더를 지정했으면 그쪽이다."""
    return datastore.get_data_file(SETTINGS_FILE)


def get_load_error():
    """마지막 load()가 경로에 못 닿았으면 그 이유, 정상이면 None."""
    return _load_error


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


def _clean_densities(values):
    """빈 이름·비중이 숫자가 아닌 항목을 걸러 낸다. 순서(=매칭 우선순위)는 그대로 지킨다."""
    if not isinstance(values, list):
        return [dict(d) for d in DEFAULT_DENSITIES]
    cleaned = []
    for entry in values:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name", "")).strip()
        try:
            density = float(entry.get("density"))
        except (TypeError, ValueError):
            continue
        if name and density > 0:
            cleaned.append({"name": name, "density": density})
    return cleaned


def _clean_machine(value, defaults):
    """가공조건 산출기 장비 스펙(정격 동력·최고 회전수·이름)을 정리한다(v0.1.1)."""
    merged = dict(defaults)
    if isinstance(value, dict):
        name = str(value.get("name", "")).strip()
        if name:
            merged["name"] = name
        for key in ("power", "max_rpm"):
            try:
                number = float(value.get(key))
                if number > 0:
                    merged[key] = number
            except (TypeError, ValueError):
                pass
    return merged


def _clean_material_rows(values, defaults, numeric_fields):
    """가공조건 재질표(Lathe/Mill 공용) 행을 정리한다(v0.1.1).

    이름·필수 숫자 항목이 없으면 그 행을 통째로 버린다. densities와 같은 규칙으로,
    사용자가 행을 다 지워 빈 목록으로 저장했으면 그대로 존중한다(기본값으로 되돌리지
    않는다) -- 저장된 값이 아예 없을 때(키 자체가 없는 옛 settings.json)만 기본값을 쓴다.
    """
    if not isinstance(values, list):
        return [dict(row) for row in defaults]
    cleaned = []
    for entry in values:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name", "")).strip()
        if not name:
            continue
        row = {"name": name}
        ok = True
        for field in numeric_fields:
            try:
                row[field] = float(entry.get(field))
            except (TypeError, ValueError):
                ok = False
                break
        if not ok:
            continue
        keywords = entry.get("keywords", [])
        row["keywords"] = [str(k).strip() for k in keywords if str(k).strip()] \
            if isinstance(keywords, list) else []
        for extra in ("insert_grade", "insert_coat", "insert_iso", "insert_desc"):
            if extra in entry:
                row[extra] = str(entry.get(extra, "")).strip()
        cleaned.append(row)
    return cleaned


def resolve_machining_material(material_text, materials):
    """소재 문자열에 맞는 가공조건 재질 행을 찾는다(v0.1.1). 없으면 None -- 추측해서
    고르지 않는다.

    densities(resolve_density)는 이름 자체를 키워드로 쓰지만, 여기 name은
    "탄소강/구조용강 (S45C)"처럼 사람이 읽는 설명이라 그대로는 카드의 Material
    문자열(예: "KS D 3752, SM45C")과 거의 안 겹친다. 그래서 별도 keywords(화학
    기호 등)로 찾는다. 가장 긴 키워드가 이긴다(density의 "더 구체적인 쪽이 이긴다"
    규칙과 같다).
    """
    text = str(material_text or "").strip().upper()
    if not text:
        return None
    best, best_len = None, 0
    for row in materials:
        for keyword in row.get("keywords", []):
            keyword = str(keyword).strip().upper()
            if keyword and keyword in text and len(keyword) > best_len:
                best, best_len = row, len(keyword)
    return best


def resolve_density(material_text, densities):
    """소재 문자열에 맞는 비중(g/cm³)을 찾는다. 없으면 None(요청 4-4).

    먼저 이름이 정확히 같은 항목을 찾고, 없으면 소재 문자열에 이름이 포함되는 항목 중
    가장 긴 이름을 고른다 -- `AL6061`(키워드)과 `AL6061P-T651`(특정 표기 덮어쓰기)이
    둘 다 목록에 있을 때, 더 구체적인 쪽이 이기게 하기 위해서다.
    """
    text = str(material_text or "").strip()
    if not text or not densities:
        return None
    upper = text.upper()
    for entry in densities:
        if str(entry.get("name", "")).strip().upper() == upper:
            return entry["density"]
    candidates = [entry for entry in densities
                 if str(entry.get("name", "")).strip()
                 and str(entry["name"]).strip().upper() in upper]
    if not candidates:
        return None
    candidates.sort(key=lambda entry: -len(str(entry["name"])))
    return candidates[0]["density"]


def load():
    """저장된 설정을 읽어 온다. 파일이 없거나 깨졌으면 기본값 그대로 돌려준다.

    v0.1.4: '파일이 없다'와 '경로에 못 닿는다'를 구분한다. 뒤쪽이면 `_load_error`를 세워
    두고, 그 뒤로는 save()가 거부한다(위 파일 첫머리 설명 참고).
    """
    global _load_error
    _load_error = None
    payload = {}

    state = datastore.get_state()
    if not state["ok"]:
        # 폴더 자체에 못 닿는다. 파일을 열어 보려 하면 SMB 대기 시간만 더 쓴다.
        _load_error = state["reason"]
    else:
        loaded, error = datastore.read_json(get_settings_path())
        if error in (datastore.REASON_UNREACHABLE, "broken"):
            # 깨진 파일도 여기 넣는다 — 내용이 무엇이었는지 모르는 채 덮어쓰면
            # 공유 폴더에서는 남의 설정을 통째로 날리는 것과 같다.
            _load_error = error
        elif isinstance(loaded, dict):
            payload = loaded

    rates = _merged(DEFAULT_RATES, payload.get("rates"))
    for key, value in rates.items():
        # 단가를 문자열로 적어 두는 실수를 대비해 숫자로 바꿔 둔다.
        try:
            rates[key] = float(value)
        except (TypeError, ValueError):
            rates[key] = float(DEFAULT_RATES[key])

    col_widths = payload.get("col_widths")
    return {
        "rates": rates,
        "materials": _clean_materials(payload.get("materials", DEFAULT_MATERIALS)),
        "densities": _clean_densities(payload.get("densities", DEFAULT_DENSITIES)),
        "company": _merged(DEFAULT_COMPANY, payload.get("company")),
        "client": _merged(DEFAULT_CLIENT, payload.get("client")),
        "supplier": _merged(DEFAULT_SUPPLIER, payload.get("supplier")),
        "col_widths": dict(col_widths) if isinstance(col_widths, dict) else {},
        "lathe_machine": _clean_machine(payload.get("lathe_machine"), DEFAULT_LATHE_MACHINE),
        "mill_machine": _clean_machine(payload.get("mill_machine"), DEFAULT_MILL_MACHINE),
        "lathe_materials": _clean_material_rows(
            payload.get("lathe_materials", DEFAULT_LATHE_MATERIALS),
            DEFAULT_LATHE_MATERIALS, LATHE_MATERIAL_NUMERIC_FIELDS),
        "mill_materials": _clean_material_rows(
            payload.get("mill_materials", DEFAULT_MILL_MATERIALS),
            DEFAULT_MILL_MATERIALS, MILL_MATERIAL_NUMERIC_FIELDS),
        "headers": _merged(DEFAULT_HEADERS, payload.get("headers")),
    }


def save(data, force=False):
    """설정을 파일로 남긴다. 저장에 실패하면 False.

    마지막 읽기가 실패한 상태(`_load_error`)에서는 저장하지 않는다 — 지금 손에 든 값은
    사용자가 고친 설정이 아니라 코드 안의 기본값이고, 그걸 공유 폴더에 쓰면 모두의 단가가
    한 번에 날아간다. `force=True`는 데이터 폴더를 옮기면서 설정을 이관할 때만 쓴다
    (그때는 원본이 무엇인지 알고 옮기는 것이므로 덮어써도 된다).
    """
    if _load_error and not force:
        return False

    col_widths = data.get("col_widths")
    payload = {
        "rates": {key: float(value) for key, value in data["rates"].items()},
        "materials": _clean_materials(data.get("materials")),
        "densities": _clean_densities(data.get("densities")),
        "company": _merged(DEFAULT_COMPANY, data.get("company")),
        "client": _merged(DEFAULT_CLIENT, data.get("client")),
        "supplier": _merged(DEFAULT_SUPPLIER, data.get("supplier")),
        "col_widths": dict(col_widths) if isinstance(col_widths, dict) else {},
        "lathe_machine": _clean_machine(data.get("lathe_machine"), DEFAULT_LATHE_MACHINE),
        "mill_machine": _clean_machine(data.get("mill_machine"), DEFAULT_MILL_MACHINE),
        "lathe_materials": _clean_material_rows(
            data.get("lathe_materials"), DEFAULT_LATHE_MATERIALS, LATHE_MATERIAL_NUMERIC_FIELDS),
        "mill_materials": _clean_material_rows(
            data.get("mill_materials"), DEFAULT_MILL_MATERIALS, MILL_MATERIAL_NUMERIC_FIELDS),
        "headers": _merged(DEFAULT_HEADERS, data.get("headers")),
    }
    # 임시 파일에 다 쓴 뒤 바꿔치기한다(네트워크 폴더에서 잘린 파일이 남지 않게).
    return datastore.write_json_atomic(get_settings_path(), payload)


def relocate(new_path, enabled=True):
    """데이터 폴더를 옮긴다(v0.1.4). 결과를 dict로 돌려준다.

        ok      성공 여부
        reason  실패 이유(datastore의 REASON_* / "broken" / "location_write_failed")
        action  "adopted"  옮긴 곳에 이미 settings.json이 있어 그 값을 쓰기로 했다
                "copied"   비어 있어서 지금 쓰던 설정을 복사해 갔다
                "fresh"    비어 있지만 지금 값이 못 미더워 복사하지 않았다(아래 설명)
        settings 옮긴 뒤 실제로 쓰게 된 설정값

    어느 쪽 값이 이겼는지 반드시 화면에 알려야 한다. 말없이 기본값으로 시작하면
    사용자에게는 "내 단가가 다 초기화됐다"로 보인다.

    'fresh'는 옮기기 직전의 읽기가 실패했던 경우다. 그때 손에 든 값은 사용자가 고친
    설정이 아니라 코드 안의 기본값이라, 그걸 새 폴더에 복사하면 기본값을 진짜 설정인
    것처럼 굳혀 버린다. 복사하지 않고 새 폴더에서 처음부터 시작한다.
    """
    previous = datastore.load_location()
    current_values = load()
    had_load_error = get_load_error()

    if enabled:
        reason = datastore.probe(new_path)
        if reason != datastore.REASON_OK:
            return {"ok": False, "reason": reason}

    if not datastore.save_location(new_path if enabled else "", enabled):
        return {"ok": False, "reason": "location_write_failed"}
    datastore.get_state(recheck=True)

    target, error = datastore.read_json(get_settings_path())
    if error in (datastore.REASON_UNREACHABLE, "broken"):
        # 옮긴 곳의 파일이 수상하다. 원래 위치로 되돌려 놓고 알린다 — 이 상태로 두면
        # 사용자는 설정을 못 고치는 창을 보게 된다.
        datastore.save_location(previous["path"], previous["enabled"])
        datastore.get_state(recheck=True)
        load()
        return {"ok": False, "reason": error}

    if isinstance(target, dict):
        action = "adopted"
    elif had_load_error:
        action = "fresh"
    else:
        save(current_values, force=True)
        action = "copied"

    return {"ok": True, "reason": None, "action": action, "settings": load()}


def writer_line(company):
    """기계 시트 푸터에 들어갈 `직위 이름` 한 줄. 한쪽이 비어도 공백이 남지 않게 만든다."""
    parts = [str(company.get("writer_title", "")).strip(),
             str(company.get("writer_name", "")).strip()]
    return " ".join(part for part in parts if part)
