# Estimate(견적) 인수인계서

이 문서 하나만 읽고도 다른 에이전트(Codex 등)나 사람이 곧바로 작업을 이어받을 수 있도록
정리한 것이다. 마지막 갱신은 **v0.1.3 (2026-08-09)** 기준이다.

> **읽는 순서**
> 1. 이 문서 전체 (10분)
> 2. `.agents/AGENTS.md` — 이 프로젝트의 에이전트 지침(계획 먼저, 승인 후 구현)
> 3. `plan.md`의 마지막 두 항목 — 최근 버전에서 무엇을 왜 바꿨는지
> 4. 손댈 모듈의 파일 첫머리 docstring — 그 파일의 설계 의도와 과거 실패 사례가 적혀 있다
>
> 에이전트 지침 파일은 저장소 루트가 아니라 **`.agents/AGENTS.md`** 에 있다. 루트의
> `AGENTS.md`만 자동으로 읽는 도구를 쓴다면 그 경로를 직접 열어 볼 것.

---

## 1. 이 프로그램이 하는 일

기계 가공 견적을 카드 단위로 입력해서, 회사 표준 엑셀 양식(`견적용.xlsx`)으로 뽑아내는
Windows 데스크톱 프로그램이다. 실무 사용자는 생산부장 1명 수준의 소규모다.

```
[기존 견적 xlsx 업로드]  ─┐
                          ├─→ [카드 목록(현황판)] ─→ [카드 입력창] ─→ [엑셀 견적 파일 다운로드]
[새 항목 직접 입력]      ─┘            ↑
                                  [설정창] 단가·소재 목록·회사 정보
```

- 금액 = Σ(공정별 시간 × 공정별 단가) × 수량, 최종금액은 1,000원 단위 내림
- 작업 중 상태는 JSON 세션으로 저장돼 다음 실행 때 복원된다
- 네트워크 기능은 **없다** (업데이트는 `{설치폴더}\update`에 설치 파일을 두면 감지)

---

## 2. 현재 상태

| 항목 | 값 |
|---|---|
| 버전 | v0.1.3 |
| 브랜치 | `worktree-v0.0.9` — v0.0.9~v0.1.3이 함께 커밋돼 있다 — **`Estimate` 브랜치에 미병합** |
| 원격 | **없음** (로컬 전용 저장소) |
| 주 개발 브랜치 | `Estimate` (기본 브랜치는 `main`이지만 실제 작업은 `Estimate`에서 해 왔다) |
| 설치 파일 | `installer\Output\MachineEstimate_Setup_v0.1.3.exe` (9,633,408바이트). 워크트리 밖 배포 폴더 `C:\Users\SumH\orca\workspaces\Estimate\Estimate\installer\Output\`에도 복사해 뒀다 |
| Python | 3.14 / openpyxl 3.1.5 / PyInstaller 6.21 |
| 빌드 형태 | onedir (`dist\Estimate\Estimate.exe` + `_internal\`) |
| 설치 경로 | `C:\Program Files (x86)\Estimate` |

**병합은 아직 하지 않았다.** 사용자가 v0.1.3을 실사용으로 확인한 뒤 `Estimate` 브랜치로
합치는 것이 남은 절차다 — v0.0.9~v0.1.2도 아직 병합 전이라 이번에 같이 합치게 된다.

---

## 3. 저장소 지도

### 살아 있는 코드

```
main.py                     진입점(PyInstaller가 이 파일을 묶는다)
estimate_app/
  __init__.py               APP_VERSION / APP_TITLE  ← 버전을 올리는 곳 ①
  main.py                   Tk 루트 생성
  core/                     화면과 무관한 로직
    paths.py                경로 계산(설치본/소스 실행/사용자 폴더)
    config.py               theme.json·rates.json 읽기, 공정 키 정의(MACHINE_KEYS)
    settings.py             ★ v0.0.9 신설. 설정창 값의 저장소
    model.py                카드 한 건의 자료 구조, 정렬·검색·HRC 조립
    pricing.py              금액 계산(화면과 엑셀이 같은 규칙을 쓰도록 여기만 본다)
    excel_io.py             ★ 가장 복잡. 견적 양식 읽기/쓰기
    session.py              작업 중 카드 목록 JSON 저장/복원
    updater.py              update 폴더의 새 설치 파일 감지
    machining.py            ★ v0.1.1 신설. 가공조건 산출기(Mill/Lathe) 계산만 담당(화면 무관)
  ui/
    theme.py                theme.json을 ttk 스타일로 적용
    widgets.py              직접 그린 체크박스 + 숫자 전용 입력칸(numeric_entry, v0.1.1부터 popup·condition_dialog 공유)
    table.py                현황판 표(열 정의, 행 슬롯 재사용, 클릭 규칙)
    dashboard.py            메인 화면 + 전체 흐름을 쥐고 있는 EstimateApp
    popup.py                카드 입력창
    settings_dialog.py      ★ v0.0.9 신설. 설정창(v0.1.1부터 "가공 조건" 탭 포함)
    condition_dialog.py     ★ v0.1.1 신설. 가공조건 산출기 창(카드 데이터는 읽기만, 절대 안 고침)
  assets/
    theme.json              색·글꼴·열 폭 (재빌드 없이 수정 가능)
    rates.json              단가·공정 표시 이름의 기본값
    estimate.ico            아이콘 (16/32/48 DIB + 256 PNG)
견적_산정/양식/견적용.xlsx   ★ 견적 양식 원본. 이 파일 구조가 곧 도메인 규칙이다
Machine_Estimate.spec       PyInstaller 설정(EXCLUDES 주의, 6절 참고)
installer/Setup.iss         Inno Setup 스크립트  ← 버전을 올리는 곳 ②
build.bat                   빌드 + 설치 파일 생성 (CP949로 저장돼 있음, 인코딩 바꾸지 말 것)
run.bat                     소스 그대로 실행(개발용)
```

### 문서

| 파일 | 성격 |
|---|---|
| `plan.md` | **작업 기록의 정본.** v0.0.9부터 계획과 결과를 여기 통합한다 |
| `ver_plan.md` | v0.0.8까지의 전체 작업 기록(110KB). 과거 판단 근거를 찾을 때만 본다 |
| `v0.0.7.md` / `v0.0.8.md` / `v0.0.9.md` | 사용자가 준 원본 요청서 |
| `v0.0.7_plan.md` / `v0.0.8_plan.md` | 과거 방식(버전별 개별 계획서). **더 만들지 않는다** |
| `.agents/AGENTS.md` | 작업 원칙 |

### 레거시 — 참고만, 수정하지 말 것

`Estimate.py`, `machine_estimate_app.py`, `*.hta`, `exe_release/`는 v0.0.4 이전의 옛 구현이다.
지금 프로그램과 무관하며 어떤 코드도 이들을 import 하지 않는다. 과거 동작을 확인할 때만 읽는다.

---

## 4. 반드시 알아야 할 도메인 지식 — 견적 양식 구조

`견적_산정\양식\견적용.xlsx`에는 시트가 셋 있다: **견적서**, **기계**, Sheet1(빈 시트).

### 기계 시트 (데이터 원본)

| 위치 | 내용 |
|---|---|
| 5행 | 공정별 단가 (L~U열) |
| 6행 | 헤더 — `NO 기종 품번 품명 Coment 가능여부 Qty Material Size(I:K 병합) 5축NC 4축 3축NC NC선반 범용 사상 CMM 연삭or와이어 치구 프로그램 SUM 단가 최종단가` |
| 7행~ | 데이터 행 (양식 기본 7칸) |
| 합계행 | 단가(W)열에 `합계`, 최종단가(X)열에 `=SUM(...)`. **행 번호 고정이 아니다** |
| 합계행 +3 / +4 / +5 (Q열) | 회사명 / 발행 날짜(yyyy-mm-dd) / 직위+작성자 |

### 견적서 시트 (출력용, 기계 시트를 참조)

| 위치 | 내용 |
|---|---|
| B4 / B5 / B6 / B8 | 받는 업체 — `○○ 귀중` / `담당자 :` / `부   서 :` / `사업명 :` |
| B7 | 날짜. `=기계!Q##` 참조 (## = 기계 시트 푸터 날짜 행) |
| F5~F9 | 우리 쪽 — 대표자 / 사업자등록번호 / 주소 / 전화번호 / 담당자 |
| 14행 | 항목 헤더 |
| 15행~ | 항목. B=No, C:D=품번, E:F=품명, G:H=견적단가 (전부 `=기계!...` 참조) |
| 합계행 | B열에 `' 합 계 '` (공백 포함), G열에 `=SUM(...)` |

### 이 구조를 다룰 때의 규칙

1. **열 위치를 코드에 박지 말 것.** `excel_io.resolve_columns(ws)`가 6행 헤더 문구를 읽어
   실제 배치를 판단한다. 사용자가 예전 배치의 양식(기종 열이 없거나 치구/프로그램이 한 칸에
   합쳐진 구버전)을 업로드해도 엉뚱한 열에 값이 들어가지 않게 하기 위해서다.
2. **푸터·합계행은 상대 위치로 찾을 것.** 데이터 행이 늘면 합계행과 푸터가 함께 밀린다
   (7건 Q17~19 → 20건 Q30~32 → 45건 Q55~57). 절대 행 번호를 쓰면 20건만 넘어도 깨진다.
3. **견적서 날짜 참조도 매번 다시 쓸 것.** 양식에 박힌 `=기계!Q18`을 그대로 두면 푸터가
   밀렸을 때 빈 칸을 가리킨다. `write_estimate_header()`가 실제 푸터 행으로 다시 쓴다.

---

## 5. 절대 하면 안 되는 것 (전부 실제로 당한 것들)

| # | 함정 | 이유 / 대응 |
|---|---|---|
| 1 | `ws.cell(row, col, value=None)`으로 값 지우기 | openpyxl은 이걸 "value 인자를 안 준 것"으로 취급해 **기존 값이 그대로 남는다**. 반드시 `ws.cell(...).value = None` |
| 2 | `openpyxl.insert_rows()`로 행 추가 | 병합 범위가 따라오지 않아 8건째부터 푸터가 밀리고 견적서가 `#REF!`가 된다. `excel_io.shift_block_down()`을 쓸 것 |
| 3 | 세션(`session.py`)에 단가 담기 | 설정창이 단가의 주인이다. 세션에도 담으면 프로그램을 켤 때 옛 세션이 새 설정을 덮어쓴다 (v0.0.9에서 제거함) |
| 4 | 설치 폴더(`{app}`)에 사용자 데이터 쓰기 | Program Files라 일반 권한으로 못 쓴다. 쓰기는 전부 `%LOCALAPPDATA%\MachineEstimate` |
| 5 | Canvas 텍스트 y 좌표를 픽셀로 하드코딩 | 배율 150%/200% 화면에서 글꼴만 커져 줄이 겹친다. `tkfont.Font(font=...).metrics("linespace")`로 재서 쌓을 것 |
| 6 | 표 행 위젯을 destroy 후 재생성 | 33행 기준 3.9초 걸리고 깜빡인다. `table.py`의 슬롯 풀을 재사용하며, 콜백은 `slot["no"]`를 **호출 시점에** 읽어야 한다 |
| 7 | 위젯 생성 시점의 상태를 클로저에 담기 | 슬롯을 재사용하므로 그 값은 곧 낡는다. v0.0.9 이전 체크박스가 이 때문에 해제되지 않았다 |
| 8 | 화면 순번(`display_no`)과 내부 번호(`item["no"]`)를 섞기 | 내부 번호는 선택·팝업·슬롯 매핑의 키다. 화면 순번은 정렬·검색에 따라 바뀐다. `app.get_display_no()`는 목록에 없으면 `None`을 준다 |
| 9 | 버전을 한 곳만 올리기 | `estimate_app/__init__.py`와 `installer/Setup.iss` **둘 다**. 설치 파일명의 버전이 `updater`의 비교 기준이다 |
| 10 | `Machine_Estimate.spec`의 EXCLUDES에서 `_ssl`/`ssl`/`_hashlib` 유지한 채 네트워크 기능 추가 | 통신할 때만 오류가 난다. 기능을 붙이면 제외를 되돌릴 것 |
| 11 | `build.bat`을 UTF-8로 다시 저장 | cmd.exe가 CP949로 읽어 깨진다. CP949 유지 |
| 12 | Inno `[Tasks]`의 `desktopicon`에 `unchecked` 되살리기 | `[InstallDelete]`는 작업 선택과 무관하게 도므로, 체크 안 하면 기존 바로가기만 지워지고 새로 안 만들어져 아이콘이 사라진다 |
| 13 | Tk의 `widget.grid_bbox(column=idx)`를 `row` 없이 부르기 | `row`를 같이 안 주면 그 열 하나가 아니라 **그리드 전체의 bbox**를 돌려준다(문서에 명시 안 됨, v0.1.0에서 직접 겪음 — 현황판 헤더 구분선 9개가 전부 같은 자리에 겹쳐 소재 헤더 글자를 가렸다). 반드시 `grid_bbox(row=0, column=idx)`처럼 둘 다 줄 것 |

---

## 6. 개발·빌드·배포 절차

### 소스 실행

```bat
run.bat
```
또는 `python main.py` (openpyxl 필요).

### 빌드

```bat
build.bat            REM exe만  → dist\Estimate\
build.bat setup      REM 설치 파일까지 → installer\Output\
```

`build.bat`이 인코딩 문제로 dist를 갱신하지 않는 일이 과거에 있었다. 그럴 땐 직접 부른다:

```powershell
python -m PyInstaller --noconfirm Machine_Estimate.spec
& "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe" "installer\Setup.iss"
```

### 배포

설치 파일은 `installer\Output\`에 생기며 `.gitignore`로 커밋되지 않는다.
**워크트리에서 빌드했다면 워크트리 삭제 시 함께 사라지므로**, 사용자의 배포 폴더로
복사해 둘 것. 배포 폴더는 여기다 — 경로를 줄여 적지 말 것:

```
C:\Users\SumH\orca\workspaces\Estimate\Estimate\installer\Output\
```

`C:\Users\SumH\Codex\Estimate\installer\Output\`도 존재하지만 **거기가 아니다**
(v0.0.1·v0.0.2만 남아 있는 옛 폴더다). v0.1.3에서 실제로 이 둘을 헷갈려 사용자가
설치 파일을 못 찾는 일이 있었다. v0.1.0~v0.1.3은 모두 위의 orca 경로에 있다.

### 사용자 데이터 위치

```
%LOCALAPPDATA%\MachineEstimate\
  settings.json        설정창 값(단가·소재 목록·회사·견적서 상단)
  session_state.json   작업 중 카드 목록
  update_state.txt     이미 처리한 업데이트 파일 기록
```
`theme.json` / `rates.json`을 이 폴더에 같은 이름으로 두면 번들 것보다 **우선** 적용된다
(`paths.get_asset_path`). 색이나 열 폭 실험에 유용하다.

---

## 7. 검증 방법

GUI 프로그램이라 자동 테스트가 없다. 대신 아래 세 가지를 매번 돌린다.

### (1) 문법

```powershell
python -m compileall -q estimate_app main.py
```

### (2) 엑셀 출력 — 헤드리스로 실제 파일을 만들어 셀을 읽는다

가장 중요한 검증이다. **3 / 7 / 20 / 45건**을 반드시 함께 확인한다
(7건 = 양식 기본 칸 수, 그 위는 행 확장 경로, 45건은 견적서 칸까지 넘는 경로).

```python
import sys; sys.path.insert(0, ".")
import openpyxl
from estimate_app.core import excel_io, settings as st
from estimate_app.core.model import create_blank_item

cfg = st.load()
items = []
for i in range(1, 21):
    it = create_blank_item(i)
    it["part_no"], it["part_name"] = f"PN-{i}", f"품명{i}"
    it["m_5axis"] = 40.0 + i          # 금액을 크게 만들어 열 폭도 함께 본다
    items.append(it)

excel_io.export_items(items, cfg["rates"], "out.xlsx", cfg)

wb = openpyxl.load_workbook("out.xlsx")
gi, es = wb["기계"], wb["견적서"]
# 확인할 것: 합계행 위치, 푸터 3줄(합계행+3/+4/+5의 Q열), 견적서 B4~B8·F5~F9,
#            B7의 =기계!Q## 참조가 실제 푸터 행을 가리키는지, W/X 열 폭, 항목 참조 수
```

`openpyxl`로는 화면 렌더링을 볼 수 없다. `####` 같은 표시 문제는 열 폭 숫자까지만
확인할 수 있고, 실제 모양은 엑셀로 열어 봐야 한다.

### (3) 화면 — 창을 직접 캡처

백그라운드 세션에서는 화면 전체 캡처가 엉뚱한 창을 잡는다. 창 핸들을 직접 그리게 한다.

```python
# 사용자 실제 설정/세션을 건드리지 않도록 저장 폴더부터 임시로 돌린다
from estimate_app.core import paths
paths.get_user_dir = lambda: r"C:\temp\est_profile"

# 이후 tkinter로 EstimateApp을 띄우고, ctypes로 PrintWindow(hwnd, hdc, 2) 캡처
# (GetAncestor(root.winfo_id(), GA_ROOT)로 최상위 핸들을 얻는다)
```

주의: `LOCALAPPDATA` 환경변수 자체를 바꾸는 방법은 쓰지 말 것 — Windows의 Python
install manager가 그 경로에 파이썬을 새로 설치해 버려 openpyxl이 사라진다(실제로 겪음).

---

## 8. 작업 규약

`.agents/AGENTS.md`의 원칙에 더해, 이 프로젝트에서 굳어진 관례다.

1. **계획을 먼저 쓰고 승인을 받는다.** 코드·버전·빌드·배포를 건드리기 전에 계획을 `plan.md`에
   적고 사용자 승인을 기다린다.
2. **기록은 `plan.md` 하나에 통합한다.** v0.0.9부터 버전별 개별 계획서(`v0.0.X_plan.md`)를
   만들지 않는다. `## YYYY-MM-DD <제목>` 아래
   `### 요청 내용 / 확인한 현재 구조 / 수정 계획 / 반영 내용 / 검증 결과 / 미실행 항목`
   순서를 따른다.
   `plan.md`는 **BOM 있는 UTF-8 + CRLF**다. 전체 재작성 말고 append 할 것.
3. **추측을 사실처럼 적지 않는다.** "확인한 현재 구조"에는 실제로 재현해 본 것만 적고,
   못 해 본 것은 "미실행 항목"에 그대로 남긴다. 이 프로젝트의 기록은 그 원칙으로 유지돼 왔다.
4. **주석은 "무엇"이 아니라 "왜"를 적는다.** 특히 과거에 실패한 방법과 그 이유를 남긴다
   (`excel_io.py`, `table.py` 첫머리가 좋은 예다).
5. 버전을 올릴 땐 `estimate_app/__init__.py`와 `installer/Setup.iss` 양쪽 모두.

---

## 9. 남은 일 / 알려진 미해결

### 곧 해야 할 것

- [ ] **v0.1.3(과 아직 안 합친 v0.0.9~v0.1.2) 실사용 확인 후 `Estimate` 브랜치로 병합.**
      현재 `worktree-v0.0.9`에만 있다.
- [ ] **다중 업로드를 실제 기계 시트로 확인.** 검증에 쓴 xlsx는 프로그램이 스스로 만든
      출력물이다. 사용자의 실제 파일 여러 개를 한 번에 올려 보는 것은 못 해 봤다.
- [ ] **"선택 삭제 옆의 삭제"의 해석 확인.** v0.1.3에서 버튼 옆에 있던 "삭제 취소"를
      없앴다. 사용자가 뜻한 것이 우클릭 메뉴의 "삭제"였다면
      `dashboard.open_row_context_menu()`의 `add_separator()`와 `label="삭제"` 두 줄을
      지우면 된다.
- [ ] **바탕화면 아이콘이 실제로 바뀌는지 확인.** exe·바로가기·아이콘 파일 쪽은 다 손봤지만
      관리자 권한 실제 설치는 해 보지 못했다. 옛 아이콘이 남아 있으면 셸 캐시가 원인이며
      `ie4uinit.exe -show`로 갱신된다.
- [ ] **견적서 출력을 실제 엑셀로 눈으로 확인.** v0.1.0에서 숨은 항목 행을 펼치고
      수식을 값으로 바꿨다(`plan.md`의 v0.1.0 항목 참고). openpyxl로 속성(hidden,
      행 높이, 수식 유무)까지만 확인했고, 엑셀이 실제로 그리는 모양은 못 봤다.

### 알려진 불일치·개선 여지 (급하지 않음)

- `excel_io._openpyxl()`은 openpyxl을 늦게 불러오려고 만든 함수인데, 같은 파일 맨 위에
  `from openpyxl.styles import Alignment`가 남아 있고 `dashboard.py`가 `excel_io`를 모듈
  수준에서 import 한다. **결과적으로 시작할 때 openpyxl이 로드된다** — 주석이 말하는
  "지연 로드"는 지금 사실이 아니다. 시작 속도를 더 줄이려면 여기가 첫 후보다.
- 표 행 하나에 위젯이 16개 남짓 붙는다. 슬롯 재사용으로 성능 목표는 이미 달성했지만,
  수백 건을 다루게 되면 다시 볼 지점이다.
- 다크 팔레트가 `theme.json`의 `presets.dark`에 남아 있다. 화면 내 전환 버튼은 없고,
  값을 `colors`로 옮겨 쓰면 재빌드 없이 되돌릴 수 있다.
- 아이콘에 96/128px 항목이 없다. 고배율 화면 바탕화면에서는 48px을 늘려 쓰거나 256px을
  줄여 쓴다. 선명도를 더 올리려면 그 두 크기를 DIB로 추가하면 된다.

---

## 10. 버전 요약 (무엇이 언제 들어왔는지)

| 버전 | 핵심 |
|---|---|
| ~v0.0.2 | 단일 파일 앱(`machine_estimate_app.py`), 카드형 현황판, 선택 다운로드 |
| v0.0.3~4 | 실행 파일명 `Estimate.exe`로 변경, JSON 세션 저장, TSERP UI |
| v0.0.5 | onefile → **onedir** 배포(시작 속도), 설치 파일 용량 33MB → 9.5MB |
| v0.0.7 | 열 위치를 헤더 문구로 판단(`resolve_columns`), 다건 출력 안정화 |
| v0.0.8 | 표 갱신 구조 재작성(슬롯 재사용), 밝은 그라데이션 테마, PDF 출력, 아이콘 |
| v0.0.9 | 설정창 신설, No/Comment 열, 탐색기식 선택·더블클릭, 여러 줄 Comment, 열처리 HRC, 견적서 상단·푸터 자동 기재, `####` 해소, **PDF·날짜별 누적 저장 제거** |
| **v0.1.0** | 견적서 숨은 항목 행 해제, Comment 행 높이 자동 계산, **엑셀 출력 수식 전부 값으로 전환**, 시간·HRC·Qty 숫자 전용 입력, 소재 비중 설정 + Size 치수 기반 무게 계산·표시, 현황판 헤더 열 구분선·드래그 리사이즈(폭 저장), 소재 칸 실측 폭 기반 말줄임 |
| **v0.1.1** | 가공조건 산출기(Mill/Lathe) 신설 -- 카드에서 선택한 소재·Size를 읽어 채우는 보조 계산 창(현황판 보조 기능 / 카드 팝업 Size 섹션에서 연다). Lathe는 `04.CSS_조건 산출기.hta`를 그대로 이식, Mill은 새로 설계(재질값은 잠정치). **카드 데이터는 절대 고치지 않는다** -- 계산 결과를 카드로 되돌리는 기능 없음(사용자 결정). 설정창에 "가공 조건" 탭 추가 |

| **v0.1.2** | 카드 삭제 신설 — 보조 기능 줄의 "선택 삭제"와 행 우클릭 메뉴("입력창 열기" / "삭제"). 입력창이 열려 있는 카드는 지우지 않는다(부분 삭제도 안 한다). 되돌리기는 메모리에 단일 단계만 기억한다(세션 파일에 안 남으므로 프로그램을 끄면 사라진다) |
| **v0.1.3** | "삭제 취소" **버튼** 제거(되돌리기 기능·Ctrl+Z는 그대로), 기계 시트 **다중 파일 업로드**(전부 읽은 뒤 한꺼번에 붙인다 — 실패한 파일이 있어도 나머지는 살리고 부분 반영을 만들지 않는다), **품번 중복 행 색 표시**(선택 > 중복 > 줄무늬 순, 요약줄에 중복 건수) |

v0.0.9에서 **없어진 기능**을 특히 기억할 것 — PDF 출력, 날짜별 누적 저장, 신규 입력
다운로드는 사용자가 직접 빼 달라고 한 것이다. 되살리지 말 것.

v0.1.0에서 **엑셀 출력에 수식이 없어졌다**는 것도 기억할 것 — 기계 시트 5행 단가나
시간을 엑셀에서 직접 고쳐도 더 이상 자동으로 재계산되지 않는다(모든 계산은
`core/pricing.calc_row()`로 프로그램이 미리 해서 값으로 적는다). 되돌리려면 `plan.md`의
v0.1.0 항목 "C. 수식 제거"를 참고할 것.

v0.1.1의 **가공조건 산출기는 카드를 읽기만 한다**는 것도 기억할 것 — 계산 결과를
공정 시간칸에 자동으로 채워 넣지 않는다. 사용자가 "결과는 카드로 되돌릴 필요 없음"이라고
명시적으로 정한 것이니, 나중에 "계산 결과 적용" 버튼 같은 걸 되살리려면 먼저 사용자에게
확인부터 할 것. 밀링 재질별 절삭조건(`core/settings.DEFAULT_MILL_MATERIALS`)과 밀링 장비
스펙(`DEFAULT_MILL_MACHINE`)은 참고할 원본이 없어 잠정값이다 — 설정창 "가공 조건 > Mill"
탭에서 실측치로 고쳐 쓸 수 있게만 만들어 뒀다.
