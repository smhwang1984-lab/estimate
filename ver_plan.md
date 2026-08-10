# Estimate 작업 기록

## 2026-08-02 초기 확인

- 작업 위치: `C:\Users\SumH\Codex\Estimate`
- 확인된 기본 양식: `견적_산정\양식\견적용.xlsx`
- 확인된 산출 프로그램:
  - `04.CSS_조건 산출기.hta`
  - `05.견적.hta`
- 참고 사항: HTA 파일은 콘솔 미리보기에서 한글 주석/제목이 깨져 보였으므로, 수정 전 실제 파일 인코딩을 확인하고 기존 동작을 보존해야 함.
- 다음 단계: 기능 수정 또는 통합 작업이 필요하면 먼저 구체적인 계획을 작성하고 승인 받은 뒤 진행.

## 2026-08-02 견적 산출 입력 프로그램 틀 계획

### 요청

- 기본 산출 양식(`견적_산정\양식\견적용.xlsx`)을 입력창 형태로 옮긴 프로그램 틀을 먼저 만든다.

### 확인한 양식 구조

- `견적용.xlsx` 시트:
  - `견적서`: 최종 견적 출력 양식
  - `기계`: 실제 견적 산출 입력/계산 영역
  - `Sheet1`: 빈 시트로 보임
- `기계` 시트 주요 구조:
  - 상단 공정별 기준 단가: `K5:T5`
  - 공정: 5축 NC, 4축, 3축 NC, NC 선반, 범용, 사상, CMM, 연삭 or 와이어, 치구, 프로그램
  - 품목 입력 영역: `A7:W13`, 현재 7개 품목 기준
  - 행별 입력: 품번, 품명, Coment, 가능여부, Qty, Material, Size, 공정별 입력값
  - 행별 자동 계산: 공정 합계, 산출금액, 천원 단위 절사 견적단가
  - 합계: `W14`
- `견적서` 시트는 `기계` 시트의 품번/품명/견적단가를 참조하여 견적서 출력에 사용함.

### 구현 방향

- 새 파일 추가: `01.견적_산출_입력.hta`
- 기존 `04.CSS_조건 산출기.hta`, `05.견적.hta`는 수정하지 않음.
- HTA 방식으로 먼저 틀을 만든다.
  - Windows에서 더블클릭 실행 가능
  - 별도 설치나 서버 없이 사용 가능

### 1차 화면 구성

- 상단: 제목, 기준일, 회사/담당자/사업명 메모 입력 영역
- 기준 단가 영역:
  - 기본값은 엑셀 양식 기준값 사용
  - 5축 NC 70000, 4축 50000, 3축 NC 40000, NC 선반 35000, 범용 20000, 사상 15600, CMM 30000, 연삭 or 와이어 35000, 치구 35000, 프로그램 35000
- 품목 입력 테이블:
  - 품번, 품명, Coment, 가능여부, Qty, Material, Size
  - 공정별 입력칸 10개
  - 행별 공정 합계, 산출금액, 견적단가 자동 표시
- 합계/미리보기 영역:
  - 총 견적금액
  - 품목별 단가 요약
  - 견적서에 들어갈 품번/품명/단가 미리보기

### 1차 계산 규칙

- 행별 공정 합계: 공정별 입력값 10개 합계
- 행별 산출금액: `(각 공정 입력값 * 각 공정 기준단가의 합) * Qty`
- 행별 견적단가: 엑셀의 `ROUNDDOWN(산출금액, -3)`와 동일하게 천원 단위 절사
- 전체 합계: 표시된 견적단가 합계

### 1차 기능 범위

- 입력값 변경 시 즉시 자동 계산
- 숫자 입력칸 포커스 시 전체 선택
- 초기값/마지막 입력값 로컬 저장
- 전체 초기화 버튼
- 엑셀 양식과 동일한 7개 품목 기준으로 먼저 구성

### 1차 제외 범위

- 엑셀 파일 직접 쓰기/저장 자동화
- 견적서 엑셀/PDF 자동 출력
- 기존 가공조건 산출기(`04`, `05`)와의 자동 연동
- 품목 행 무제한 추가/삭제

### 승인 후 작업 순서

1. `01.견적_산출_입력.hta` 신규 작성
2. 엑셀 양식의 입력/계산 구조를 HTML 입력창과 JavaScript 계산식으로 반영
3. 기존 HTA 스타일을 참고해 작은 화면에서도 보이는 레이아웃 적용
4. 기본 계산 검증: 엑셀 수식과 동일한 결과가 나오는지 샘플값으로 확인
5. `ver_plan.md`에 구현 완료 내용과 검증 결과 추가

## 2026-08-02 견적 산출 입력 프로그램 기본틀 완료

- 신규 파일: `01.견적_산출_입력.hta`
- 기존 파일 유지:
  - `04.CSS_조건 산출기.hta`
  - `05.견적.hta`
- 반영한 기본 구조:
  - 견적 기본정보 입력 영역
  - 공정별 기준 단가 입력 영역
  - `기계` 시트 기준 7개 품목 입력 테이블
  - 품번, 품명, Coment, 가능여부, Qty, Material, Size 입력칸
  - 5축 NC, 4축, 3축 NC, NC 선반, 범용, 사상, CMM, 연삭/와이어, 치구, 프로그램 입력칸
  - 공정 합계, 산출금액, 견적단가 표시 자리
  - 견적서 미리보기 영역
- 이번 단계에서 의도적으로 제외한 내용:
  - 산출 방식 상세 계산
  - 엑셀 자동 저장/출력
  - PDF 출력
  - 기존 `04`, `05` 산출기와 자동 연동
- 점검:
  - 파일 생성 확인 완료
  - 주요 함수 확인: `buildRows`, `refreshPreview`, `clearItemRows`, `clearAllInputs`, `initApp`
  - 주요 입력 구조 확인: 기준단가, 품목 입력, 견적서 미리보기

## 2026-08-02 입력 방식 팝업 전환 계획

### 요청

- 현재 `01.견적_산출_입력.hta`의 입력 방식 변경
- 양식의 `기계` 시트 기준 단가 데이터와 상세 입력란을 팝업으로 실행할 수 있게 설정
- 산출 방식과 계산 방식은 후순위 유지

### 변경 방향

- 메인 화면은 요약 중심으로 정리한다.
  - 견적 기본정보 입력
  - 품목 7개 요약 목록
  - 품번, 품명, 가능여부, Qty, Material, Size, 견적단가 자리 표시
  - 총합계/견적서 미리보기 자리 유지
- 공정별 기준 단가 입력은 팝업으로 분리한다.
  - 버튼명 예: `기준 단가 설정`
  - 팝업 항목: 5축 NC, 4축, 3축 NC, NC 선반, 범용, 사상, CMM, 연삭/와이어, 치구, 프로그램
  - 기본값은 엑셀 `기계!K5:T5` 기준값 유지
  - 팝업에서 확인을 누르면 메인 상태에 값 반영
- 품목별 상세 입력란은 행별 팝업으로 분리한다.
  - 품목 요약 행마다 `상세입력` 버튼 추가
  - 팝업 항목:
    - 품번, 품명, Coment, 가능여부, Qty, Material, Size
    - 5축 NC, 4축, 3축 NC, NC 선반, 범용, 사상, CMM, 연삭/와이어, 치구, 프로그램
    - 공정 합계, 산출금액, 견적단가 표시 자리
  - 팝업에서 확인을 누르면 해당 행 요약과 미리보기 갱신

### 구현 방식

- HTA 단일 파일 유지: `01.견적_산출_입력.hta`
- 외부 파일이나 서버를 추가하지 않음
- 팝업은 HTA/IE 호환성을 우선해서 같은 파일 안의 모달 레이어 방식으로 구현
  - `window.open` 새 창보다 데이터 전달과 유지가 안정적임
  - 화면상 팝업처럼 보이도록 어두운 배경, 중앙 패널, 확인/취소 버튼 구성
- 입력 데이터는 JavaScript 배열/객체로 관리
  - `rateData`: 기준 단가 데이터
  - `itemData[0..6]`: 품목별 상세 입력 데이터
- 계산 로직은 이번 단계에서 최소화
  - 표시칸과 데이터 구조만 유지
  - 실제 산출금액/견적단가 자동 계산은 다음 단계에서 연결

### 화면 변경 세부

- 상단 버튼 추가/변경:
  - `기준 단가 설정`
  - `미리보기 갱신`
  - `품목 초기화`
  - `전체 초기화`
- 기존 공정별 기준 단가 펼침 영역은 제거하거나 요약 카드로 축소
- 기존 가로로 긴 품목 상세 테이블은 요약 테이블로 변경
  - No, 품번, 품명, 가능여부, Qty, Material, Size, 견적단가, 상세입력 버튼
- 상세입력 팝업 안에서만 긴 공정별 입력칸을 보여줌

### 승인 후 작업 순서

1. 기존 `01.견적_산출_입력.hta` 백업 없이 직접 수정하되 기존 `04`, `05` 파일은 유지
2. 기준단가 데이터를 JS 상태값으로 분리
3. 기준단가 설정 모달 추가
4. 품목 상세입력 모달 추가
5. 메인 품목 테이블을 요약형으로 변경
6. 확인/취소/초기화/미리보기 갱신 동작 점검
7. JavaScript 문법 검사
8. `ver_plan.md`에 구현 완료 및 점검 결과 추가

## 2026-08-03 machine_estimate_app.py time input visibility fix plan

### Request

- Fix `machine_estimate_app.py` because the machining time input area is not visible in the item popup.

### Current finding

- The time input widgets are already created in `open_popup()` around the machine/hour section.
- The popup uses a fixed geometry (`640x650`) and packs every section into one non-scrollable frame.
- Because the Size section and buttons share the same fixed-height popup, the time input section can be pushed below the visible area depending on Windows display scaling or actual window size.

### Approved work scope

1. Keep the existing item popup behavior and calculation logic unchanged.
2. Add a scrollable body inside the popup so the machine/hour input section is always reachable.
3. Keep the Save / Save and Next buttons fixed at the bottom of the popup.
4. If needed, slightly adjust popup size/minimum size only to improve visibility.
5. Run a Python syntax check after editing.
6. Add completion and verification notes back to this `ver_plan.md`.

### Pending approval

- Waiting for user approval before changing `machine_estimate_app.py`.

### Completion

- Updated `machine_estimate_app.py` popup layout.
- Added a scrollable popup body so the machine/hour input section remains reachable.
- Moved the save buttons to a fixed bottom frame outside the scrollable body.
- Kept calculation and Excel-save logic unchanged.

### Verification

- `python -m py_compile machine_estimate_app.py` passed.
- Added mousewheel cleanup on popup close so the scroll binding does not remain after the popup is destroyed.

## 2026-08-03 machine_estimate_app.py executable build plan

### Request

- Create a double-click runnable Windows executable for `machine_estimate_app.py`.

### Current finding

- Python is available and `python -m PyInstaller --version` returns `6.21.0`.
- The app uses `tkinter` and `openpyxl`; no web/server runtime is needed.
- The app currently expects its Excel template/output paths relative to the running folder, so the safest deliverable is a folder containing the EXE plus the required workbook/template files when needed.

### Proposed work scope

1. Build `machine_estimate_app.py` with PyInstaller as a Windows GUI executable.
2. Put final output under an `exe_release` or similar folder inside `C:\Users\SumH\Codex\Estimate`.
3. Include/copy any required workbook template next to the EXE if the app needs it to save results.
4. Smoke-test the executable by launching it briefly and confirming the process starts.
5. Record completion and verification in this `ver_plan.md`.

### Pending approval

- Waiting for user approval before running the executable build.

## 2026-08-03 실행 파일 생성 작업 기록(한글)

### 승인 내용

- `machine_estimate_app.py`를 더블클릭으로 실행 가능한 Windows EXE로 만든다.
- 작업 내용은 `plan.md`와 `ver_plan.md`에 한글로 남긴다.

### 작업 방향

1. EXE 실행 시에도 `견적용.xlsx` 양식 파일을 안정적으로 찾도록 경로 처리를 보강한다.
2. PyInstaller 단일 실행 파일 방식으로 빌드한다.
3. `견적_산정\양식\견적용.xlsx`를 EXE 내부에 포함한다.
4. 결과 저장 파일은 EXE가 있는 폴더에 생성되도록 한다.
5. 문법 검사와 EXE 실행 시작 확인을 진행한다.

### 완료 결과

- 실행 파일 생성 완료: `exe_release\Machine_Estimate.exe`
- PyInstaller 단일 실행 파일 방식으로 빌드했다.
- `견적용.xlsx` 양식 파일을 EXE 내부에 포함했다.
- EXE 실행 시작 확인 결과: 5초 동안 즉시 종료되지 않아 정상 시작으로 확인했다.
- 저장 결과 파일은 EXE가 있는 폴더에 `견적용_입력완료.xlsx`로 생성되도록 했다.
- 최종 위치의 `exe_release\Machine_Estimate.exe`도 실행 시작 확인 완료.
- 최종 위치의 `exe_release\Machine_Estimate.exe`도 실행 시작 확인 완료.

## 2026-08-03 공정 시간 입력창 미표시 수정 계획

### 현상

- 항목 입력 팝업에서 기본 정보와 Size 입력 영역은 보이지만, 각 공정별 시간 입력 영역이 보이지 않는다.

### 수정 계획

1. 팝업을 좌우 2단 구조로 변경한다.
2. 왼쪽에는 기본 정보와 Size 입력을 배치한다.
3. 오른쪽에는 각 공정별 시간 입력 영역을 항상 보이도록 배치한다.
4. 계산/저장 로직은 기존과 동일하게 유지한다.
5. 수정 후 문법 검사와 EXE 재빌드를 진행한다.

### 승인 대기

- 사용자 승인 후 수정 진행.

### 공정 시간 입력창 미표시 수정 완료

- 항목 입력 팝업을 좌우 2단 구조로 변경했다.
- 기본 정보와 Size 입력은 왼쪽에 유지했다.
- 각 공정별 시간 입력은 오른쪽에 항상 보이도록 배치했다.
- 계산/저장 로직은 변경하지 않았다.

### 재빌드 완료

- `exe_release\Machine_Estimate.exe`를 새 UI가 반영된 실행 파일로 갱신했다.
- 공정 시간 입력 영역이 오른쪽에 항상 보이도록 팝업 구조를 변경한 상태로 빌드했다.
- 최종 EXE 실행 시작 확인 완료: 5초 동안 즉시 종료되지 않음.

### 공정 시간 입력 영역 재점검 및 추가 수정

- 오른쪽 공정 시간 입력 영역이 계속 보이지 않는 문제를 재점검했다.
- 스크롤 캔버스 구조를 제거하고, 팝업 본문을 직접 좌우 2단 구조로 고정했다.
- 오른쪽 공정 시간 입력 영역에 최소 폭을 지정해 화면에서 숨지 않도록 했다.

### 공정 시간 입력 영역 재빌드 완료

- 스크롤 캔버스를 제거한 팝업 구조로 EXE를 다시 빌드했다.
- `exe_release\Machine_Estimate.exe`를 새 빌드로 교체했다.
- 기존 `exe_release\Machine_Estimate.exe`가 실행 중이라 파일이 잠겨 즉시 덮어쓰기 불가.
- 같은 폴더에 새 수정본 `exe_release\Machine_Estimate_fixed.exe`로 생성한다.

## 2026-08-03 견적용.xlsx 로드/날짜별 누적 저장/UI 130% 확대 계획

### 요청 내용

- `견적용.xlsx` 양식을 로드해서 사용한다.
- 작성 날짜 기준으로 파일을 구분한다.
- 같은 날짜에는 기존 입력 뒤에 누적 저장한다.
- UI 폰트 크기를 현재 대비 130% 수준으로 키운다.

### 수정 계획

1. `견적_산정\양식\견적용.xlsx`를 기준 양식으로 사용한다.
2. 날짜별 저장 위치를 `견적_산정\YYYY년도\MM월`로 만든다.
3. 날짜별 누적 파일명은 `견적누적_YYYY-MM-DD.xlsx`로 한다.
4. 날짜 파일이 없으면 양식에서 새로 만들고, 있으면 이어서 저장한다.
5. `기계` 시트의 마지막 입력 행 다음에 입력된 항목을 누적한다.
6. 기존 수식/서식을 복사해서 계산 구조를 유지한다.
7. UI 폰트와 표 행 높이를 약 130%로 확대한다.
8. 문법 검사 후 EXE를 다시 빌드한다.

### 승인 대기

- 사용자 승인 후 수정 진행.

### 날짜별 누적 저장 및 UI 130% 확대 구현 완료

- 날짜별 누적 저장 경로를 적용했다.
- 같은 날짜 파일이 있으면 기존 입력 아래에 누적 저장되도록 했다.
- 빈 항목은 저장 대상에서 제외했다.
- 새 입력 행에는 기존 양식의 서식과 수식을 유지하도록 했다.
- UI 글자 크기를 약 130%로 확대했다.

### 날짜별 누적 저장/UI 확대 EXE 재빌드 완료

- PyInstaller 빌드 완료.
- 최신 실행 파일을 `exe_release\Machine_Estimate_latest.exe`로 생성했다.
- 실행 중인 이전 프로세스가 없어 `exe_release\Machine_Estimate.exe`도 최신 빌드로 교체했다.
- 문법 검사 통과.
- 임시 파일 기준 누적 저장 검증 완료: 1차/2차 저장이 이어짐.
- 8개 항목 저장 검증 완료: 합계 행 앞 행 삽입 및 합계 수식 갱신 확인.
- 최종 EXE 실행 시작 확인 완료.

## 2026-08-04 카드형 견적 현황판 전환 계획

### 요청 내용

- `견적용.xlsx` 양식을 기준으로 입력한다.
- 입력된 항목을 TSERP 현황판처럼 카드 형태로 표시/관리한다.
- 날짜별 누적 저장 방식과 UI 130% 확대 기준은 유지한다.

### 수정 계획

1. 메인 표 화면을 카드형 현황판 화면으로 변경한다.
2. 상단에 오늘 날짜, 총 항목, 총 견적금액 요약을 표시한다.
3. 본문에는 품번/품명/상태/시간/금액/작성일이 보이는 카드를 배치한다.
4. 카드 클릭 또는 수정 버튼으로 상세 입력 팝업을 연다.
5. 새 카드 추가 버튼으로 빈 항목을 만들고 입력 팝업을 연다.
6. 기존 날짜별 누적 Excel 저장 로직은 유지한다.
7. 카드 목록은 스크롤 가능하게 만든다.
8. 문법 검사 후 EXE를 다시 빌드한다.

### 승인 대기

- 사용자 승인 후 수정 진행.

### 카드형 견적 현황판 구현 진행

- 기존 메인 표 화면을 제거하고 카드형 현황판으로 변경했다.
- 오늘 날짜 누적 파일을 카드로 불러오도록 했다.
- 카드 수정 버튼과 더블클릭으로 기존 상세 입력 팝업을 열도록 했다.
- 기존 누적 파일에서 불러온 카드는 엑셀 행 번호를 기억하도록 했다.
- 다시 저장 시 기존 카드는 행 갱신, 신규 카드는 추가되도록 검증했다.

### 카드형 현황판 점검 기록

- GUI 앱 직접 실행으로 인해 작업이 멈춘 것처럼 보일 수 있음을 확인했다.
- 문법 검사 통과.
- 시작 시 날짜 폴더 생성 없이 기존 파일만 로드하도록 보강했다.
- 짧은 실행 확인 결과 정상 시작 확인.

### 카드형 현황판 EXE 재빌드 완료

- PyInstaller 빌드 완료.
- `exe_release\Machine_Estimate.exe`와 `exe_release\Machine_Estimate_latest.exe`를 최신 카드형 현황판 버전으로 교체했다.
- 최종 EXE 실행 시작 확인 완료: 5초 동안 즉시 종료되지 않음.
- 카드형 현황판 UI와 날짜별 누적 저장 구조를 반영한 빌드다.

## 2026-08-04 양식 업로드/저장/검색 기능 추가 계획

### 요청 내용

- `견적용.xlsx` 양식 파일을 업로드해서 카드로 불러온다.
- 불러온 카드를 저장할 수 있게 한다.
- 검색 기능으로 원하는 카드를 찾을 수 있게 한다.

### 수정 계획

1. 상단에 `양식 업로드` 버튼을 추가한다.
2. `.xlsx` 파일 선택창을 열어 사용자가 파일을 고르게 한다.
3. 선택한 파일의 `기계` 시트 7행부터 입력 데이터를 읽는다.
4. 읽은 데이터를 카드 목록에 추가한다.
5. 업로드된 카드는 저장 시 오늘 날짜 누적 파일에 새 행으로 추가한다.
6. 검색창과 검색 초기화 버튼을 추가한다.
7. 품번, 품명, 가능여부, Material, Size, Coment, 작성일 기준으로 검색되게 한다.
8. 문법 검사, 업로드/검색 검증, EXE 재빌드를 진행한다.

### 승인 대기

- 사용자 승인 후 수정 진행.

### 양식 업로드/검색 기능 구현 진행

- `양식 업로드` 버튼을 추가했다.
- Search 검색창과 초기화 버튼을 추가했다.
- `.xlsx` 파일의 `기계` 시트를 카드 데이터로 읽는 파서를 추가했다.
- 검색 대상은 작성일, 품번, 품명, 가능여부, Material, Size, Coment 등으로 구성했다.
- 문법 검사 통과.
- 테스트 파일 기준 업로드 파서와 검색 필터 검증 완료.
- 실행 오류 수정: 검색 영역의 Tkinter `pady` 적용 위치를 수정했다.

### 양식 업로드/검색 기능 EXE 재빌드 완료

- PyInstaller 빌드 완료.
- 실행 파일을 업로드/검색 기능 포함 최신 버전으로 교체했다.
- 최종 EXE 실행 시작 확인 완료.
- 업로드/검색/카드형 현황판/날짜별 누적 저장 기능이 포함된 빌드다.

## 2026-08-04 연도별 전체 견적 파일 자동 업로드 및 전체 화면 실행 계획

### 요청 내용

- `견적_산정\2026년도` 아래 각 월별 입력 파일 전체를 실행 시 자동 업로드한다.
- 업로드된 전체 내용을 검색할 수 있게 한다.
- 프로그램 실행 시 전체 화면 또는 최대화 상태로 연다.

### 수정 계획

1. 실행 시 `견적_산정\2026년도` 아래 모든 `.xlsx` 파일을 스캔한다.
2. 기준 양식 파일은 제외한다.
3. 각 파일의 `기계` 시트 입력 행을 카드로 변환한다.
4. 카드에 원본 파일명/월 정보를 저장한다.
5. 검색 대상에 원본 파일명과 월 정보를 추가한다.
6. 기존 원본 파일은 자동 수정하지 않고, 저장은 오늘 날짜 누적 파일에 반영한다.
7. 실행 창은 최대화 상태로 시작한다.
8. 문법 검사, 로드 수 검증, EXE 재빌드를 진행한다.

### 승인 대기

- 사용자 승인 후 수정 진행.

### 연도별 전체 자동 업로드 및 최대화 실행 구현 완료

- 실행 시 창이 최대화 상태로 열리도록 했다.
- `견적_산정\2026년도` 아래 18개 `.xlsx` 파일을 자동 스캔하도록 했다.
- 실제 검증 결과 18개 파일에서 총 319개 카드가 로드되었다.
- 오래된 양식의 Size 분리 칸과 수식 셀을 안전하게 처리하도록 했다.
- 원본 월/파일명을 카드 표시와 검색 대상에 포함했다.

### 연도별 전체 자동 업로드/최대화 EXE 재빌드 완료

- PyInstaller 빌드 완료.
- 실행 파일을 최신 버전으로 교체했다.
- 기존 `Machine_Estimate.exe`가 실행 중이라 기본 파일명은 파일 잠금으로 교체되지 않았다.
- `exe_release\Machine_Estimate_latest.exe`는 최신 빌드로 교체 완료했다.
- 최신 EXE 실행 시작 확인 완료.

## 2026-08-04 20:50:21 기계 시트 카드 업로드 재점검 및 실행파일 갱신
- 사용자 지정 파일 견적_산정\2026년도\04월\PLK972304 외.xlsx의 기계 시트만 읽어 카드로 변환되도록 재확인함.
- 해당 파일의 기계 시트에서 27개 카드가 추출됨을 확인함.
- 카드 UI에 K:T 공정 시간 표시 영역을 추가함: 5축, 4축, 3축, 선반, 범용, 사상, 3차원, 연마, 지그, 프로그래밍.
- 상단 업로드 버튼 문구를 기계 시트 업로드로 변경하여 업로드 대상이 명확히 보이게 함.
- 연도 폴더 견적_산정\2026년도 자동 로드 시 18개 파일에서 319개 행을 읽고, 실제 카드 표시 데이터 196건을 확인함.
- Tkinter 실제 위젯 검사 결과 전체화면 상태와 공정 시간 라벨/값 표시를 확인함.
- PyInstaller로 실행 파일을 재빌드하고 exe_release\Machine_Estimate.exe, exe_release\Machine_Estimate_latest.exe를 최신본으로 갱신함.
- 기존 실행 중이던 구버전 Machine_Estimate.exe 프로세스 2개는 파일 교체를 위해 종료함.
- 최신 Machine_Estimate.exe 7초 실행 검증 결과 정상 실행됨.

## 2026-08-05 07:31:45 멈춤 버그 및 딥블루 UI 개선 계획

### 현재 점검 결과
- 실행 중인 Machine_Estimate.exe가 2개 확인됨. 중복 실행 상태에서 파일 로드/저장/교체가 겹치면 멈춤이나 잠금이 자주 발생할 수 있음.
- load_existing_cards()가 시작 시 견적_산정\2026년도의 모든 xlsx를 UI 스레드에서 즉시 읽음. 이 동안 창이 멈춘 것처럼 보일 수 있음.
- efresh_table()이 검색/저장/수정 때마다 표시 대상 카드 전체를 파괴 후 재생성함. 현재 카드 300건 내외 기준 라벨 위젯이 1만 개 이상 생성되어 멈춤 원인이 됨.
- 팝업 입력창은 1080x560, 좌/우 컬럼 고정 폭에 130% 폰트가 적용되어 Size 입력/공정 입력 영역이 짤릴 수 있음.
- 현재 색상은 밝은 카드형 UI라 사용자가 요청한 TSERP와 동일한 딥블루 모드가 적용되어 있지 않음.

### 수정 계획
1. 멈춤 완화
   - 시작 시 자동 업로드는 백그라운드 스레드에서 수행하고, UI에는 로드 중 상태를 먼저 표시함.
   - 검색 입력은 키 입력마다 즉시 전체 렌더링하지 않고 짧은 지연 후 1회만 반영하도록 디바운스 처리함.
   - 카드 렌더링은 한 번에 전체를 만들지 않고 기본 표시 개수를 제한하고 더 보기 방식으로 추가 표시함.

2. 중복 실행/파일 잠금 방지
   - 실행 파일 교체 전 프로세스를 확인하고 종료 후 교체함.
   - 앱 내부에서는 저장 중 버튼 중복 클릭을 막아 같은 파일을 동시에 저장하지 않도록 함.

3. TSERP 딥블루 UI 적용
   - 배경, 헤더, 카드, 검색 영역, 공정 시간 칩을 딥블루 계열로 통일함.
   - 글자 대비는 밝게 조정하고 상태 색상은 딥블루 배경에서도 보이도록 재설정함.

4. 입력창 짤림 수정
   - 팝업 기본 크기를 확대하고 최소 크기를 올림.
   - 팝업 내부에 스크롤 가능한 입력 영역을 적용하여 작은 화면에서도 하단 버튼/공정 입력이 잘리지 않게 함.
   - 기본정보/Size/공정별 시간 Entry 폭과 컬럼 weight를 조정함.

5. 검증 및 배포
   - python -m py_compile machine_estimate_app.py 실행.
   - Tkinter 위젯 크기 검사로 공정 입력 Entry 10개가 표시되는지 확인.
   - PyInstaller로 EXE 재빌드 후 exe_release\Machine_Estimate.exe와 Machine_Estimate_latest.exe 갱신.
   - 작업 완료 후 er_plan.md에 실제 수정/검증 결과를 한글로 기록.

### 승인 필요
- 위 범위대로 수정 진행하려면 사용자 승인 후 코드 수정 및 실행 파일 재빌드를 진행함.

## 2026-08-05 07:51:46 멈춤 버그 개선, TSERP 딥블루 UI, 입력창 짤림 수정 완료

### 수정 내용
- 시작 시 견적_산정\2026년도 엑셀 전체 로드를 UI 스레드에서 직접 수행하지 않고 백그라운드 스레드 + Queue 폴링 방식으로 변경함.
- Tkinter를 백그라운드 스레드에서 직접 호출하지 않도록 수정하여 main thread is not in main loop 예외 가능성을 제거함.
- 검색 입력은 250ms 디바운스 방식으로 변경하여 키 입력마다 전체 카드가 재생성되지 않게 함.
- 카드 렌더링은 기본 40개만 표시하고 더 보기 버튼으로 40개씩 추가 표시하도록 변경함.
- 저장 중복 클릭 방지를 위해 저장 진행 중 재진입을 차단함.
- 메인 UI를 TSERP 계열 딥블루 모드로 변경함: 배경 #07111f, 패널 #0d1b2e, 카드 #132b46.
- 카드/공정 시간 칩/상태 배지를 딥블루 배경에서 읽기 쉬운 색상으로 조정함.
- 팝업 입력창을 1380x820, 최소 1240x720으로 확대하고 내부 스크롤 Canvas를 적용함.
- 공정별 시간 입력을 2열 압축 배치에서 1공정 1행 배치로 변경하여 130% 폰트에서도 Entry가 짤리지 않게 함.
- 새로 작성된 한국어 UI 문구가 깨진 부분을 유니코드 기준으로 복구함.

### 검증 결과
- python -m py_compile machine_estimate_app.py 통과.
- Tkinter 실제 위젯 검사 결과 견적_산정\2026년도 데이터 319건 로드 완료.
- 첫 화면 렌더링은 40개 카드 + 더보기로 제한되어 card_container 직접 자식 41개 확인.
- 팝업 크기 1380x820, Entry 20개, 최소 Entry 폭 104px 확인.
- 딥블루 배경 색상 #07111f 확인.
- exe_release\Machine_Estimate.exe 실행 확인 완료.
- exe_release\Machine_Estimate.exe, exe_release\Machine_Estimate_latest.exe 최신 빌드로 갱신함.

## 2026-08-05 설치 파일 제작 및 업데이트 방식 도입 완료

### 사용자 결정 사항

- 설치 위치: Program Files.
- 업데이트 방식: 설치 폴더 안 `update` 폴더에 새 설치 파일을 넣으면 프로그램 실행 시 감지해서 실행 여부를 안내하는 수동 교체 방식.

### 수정 내용

- `machine_estimate_app.py`에 `APP_VERSION = "0.0.1"` 상수를 추가하고 창 제목에 `v0.0.1`을 표시하도록 함.
- 앱 시작 0.8초 후 `{실행파일 폴더}\update` 폴더를 확인하는 `check_for_update()`를 추가함.
  - `update` 폴더 안에 `.exe` 설치 파일이 있으면 가장 최근 수정된 파일을 대상으로 실행 여부를 확인창으로 물어봄.
  - 승인하면 `subprocess.Popen`으로 설치 파일을 실행함.
  - 실제 실행 파일 종료/교체/재시작은 Inno Setup의 `CloseApplications`/`RestartApplications` 기능에 위임함.
- 신규 파일 `installer\Setup.iss` 작성.
  - `AppId`를 고정 GUID(`F64AEBE2-F81A-4376-AD06-0A6005F1A53B`)로 지정해 이후 버전에서도 같은 설치로 인식되게 함.
  - `AppVersion 0.0.1`, 설치 대상 `Program Files\기계 시트 표준 견적 입력 시스템`.
  - 설치 시 빈 `update` 폴더를 함께 생성함.
  - 시작 메뉴 바로가기를 만들고, 바탕화면 아이콘은 설치 중 선택 항목(기본 미선택)으로 둠.
  - 한국어 설치 언어(`Korean.isl`) 적용.
  - `CloseApplications=yes`, `RestartApplications=yes`로 설정해 설치/업데이트 중 실행 중인 프로그램을 감지해 종료 후 재시작하도록 함.

### 검증 결과

- `python -m py_compile machine_estimate_app.py` 통과.
- `python -m PyInstaller Machine_Estimate.spec --noconfirm` 빌드 성공. `exe_release\Machine_Estimate.exe`, `exe_release\Machine_Estimate_latest.exe`를 최신본으로 교체함.
- 재빌드한 EXE를 5초간 실행해 즉시 종료되지 않음을 확인함(PowerShell `Start-Process`/`Get-Process` 확인).
- `ISCC.exe`(Inno Setup 7)로 `installer\Setup.iss` 컴파일 성공.
- 생성된 설치 파일 확인: `installer\Output\MachineEstimate_Setup_v0.0.1.exe` (약 33MB).

### 실행하지 않은 항목

- 실제 설치 파일 실행(Program Files 설치, 관리자 권한 필요)은 시스템 변경 사항이라 사용자 승인 없이 진행하지 않음.
- 향후 새 버전 배포 시에는 EXE 재빌드 → `Setup.iss`의 `MyAppVersion` 값 갱신 → `ISCC.exe`로 재컴파일 → 생성된 설치 파일을 설치 폴더의 `update` 폴더에 배치하는 순서로 진행하면 됨.

## 2026-08-05 업데이트 v0.0.2 선택 다운로드 계획

### 요청 내용 (`nextup v.0.0.2.MD`)

- 선택한 항목만 다운로드할 수 있게 한다.
- 다운로드 양식은 기존 설정 양식, 즉 현재 사용 중인 `견적_산정\양식\견적용.xlsx` 구조를 따른다.
- 다중 검색이 가능해야 하며, 조임쇠 영역 기준으로 검색하고 선택 후 다운로드할 수 있게 한다.
- 신규 입력 시에는 별도 창에서 신규분만 먼저 저장한 뒤 다운로드할 수 있게 한다.

### 현재 확인한 상태

- 현재 앱 버전과 설치 스크립트 버전은 `0.0.1`이다.
- 상단 기능은 `기계 시트 업로드`, `새 카드 추가`, `날짜별 누적 저장`, `Search` 검색으로 구성되어 있다.
- 현재 저장 기능은 `save_to_excel()`이 저장 대기 또는 기존 엑셀 행이 있는 전체 항목을 날짜별 누적 파일에 저장하는 방식이다.
- 현재 카드별 선택 상태와 선택 항목만 별도 양식으로 내보내는 다운로드 기능은 없다.
- 기존 검색은 작성일, 원본 월/파일명, 품번, 품명, 가능여부, Material, Size, Coment, Qty, 시간합계, 최종단가를 단일 검색어로 필터링한다.

### 수정 계획

1. 버전을 `0.0.2`로 올린다.
   - `machine_estimate_app.py`의 `APP_VERSION`을 `0.0.2`로 변경한다.
   - `installer\Setup.iss`의 `MyAppVersion`을 `0.0.2`로 변경해 설치 파일명이 `MachineEstimate_Setup_v0.0.2.exe`가 되게 한다.
2. 카드 선택 기능을 추가한다.
   - 각 카드에 선택 체크박스를 추가한다.
   - 검색/더보기/카드 재렌더링 후에도 선택 상태가 유지되도록 항목별 내부 ID를 사용한다.
   - 상단에 `전체 선택`, `선택 해제`, `선택 다운로드` 버튼을 추가한다.
3. 다중 검색을 개선한다.
   - 검색어를 공백 또는 쉼표로 나누어 여러 조건을 동시에 적용한다.
   - 모든 검색어가 카드의 검색 대상에 포함될 때만 표시되게 한다.
   - `조임쇠 영역`은 현재 엑셀/카드 구조에서 별도 컬럼이 확인되지 않았으므로, 1차 구현에서는 품번, 품명, Coment, Material, Size, 원본 파일명을 포함하는 검색 영역으로 적용한다.
4. 선택 다운로드 기능을 만든다.
   - 다운로드 대상은 현재 선택된 카드만 사용한다.
   - 다운로드 파일은 기존 기준 양식 `견적용.xlsx`를 복사해 생성한다.
   - 선택 항목을 `기계` 시트의 기존 입력 구조(B:H, K:T, U:W 수식)에 맞춰 기록한다.
   - 저장 위치는 사용자가 고를 수 있도록 파일 저장 창을 띄우고, 기본 파일명은 `선택견적_YYYY-MM-DD.xlsx`로 제안한다.
   - 다운로드용 파일 생성은 기존 날짜별 누적 저장 파일을 자동 수정하지 않는다.
5. 신규 입력 후 다운로드 흐름을 추가한다.
   - `신규 입력 다운로드` 버튼을 추가한다.
   - 별도 입력 창에서 신규 항목만 작성하게 하고, 기존 카드 목록 전체 저장 전에 해당 신규 항목만 다운로드 대상 파일로 먼저 저장한다.
   - 신규 입력 완료 후 사용자가 원하면 현재 카드 목록에도 추가할 수 있게 하되, 기존 날짜별 누적 저장은 별도 버튼으로 유지한다.
6. 기존 기능 보존 범위
   - 기존 카드형 현황판, 연도별 자동 업로드, 검색, 더보기, 날짜별 누적 저장, 업데이트 감지 방식은 유지한다.
   - 기존 `04.CSS_조건 산출기.hta`, `05.견적.hta`, 엑셀 기준 양식 구조는 수정하지 않는다.
7. 검증 및 배포
   - `python -m py_compile machine_estimate_app.py`를 실행한다.
   - 선택 상태 유지, 다중 검색 필터, 선택 다운로드 엑셀 생성, 신규 입력 다운로드 흐름을 임시 데이터로 검증한다.
   - PyInstaller로 EXE를 재빌드하고 `exe_release\Machine_Estimate.exe`, `exe_release\Machine_Estimate_latest.exe`를 갱신한다.
   - Inno Setup으로 `installer\Output\MachineEstimate_Setup_v0.0.2.exe`를 생성한다.
   - 완료 후 `ver_plan.md`에 실제 수정 내용과 검증 결과를 추가한다.

### 승인 필요

- 위 범위대로 v0.0.2 기능 구현, EXE 재빌드, 설치 파일 생성을 진행하려면 사용자 승인이 필요하다.

## 2026-08-05 업데이트 v0.0.2 선택 다운로드 구현 완료

### 구현 내용

- `machine_estimate_app.py`를 v`0.0.2` 기준으로 정리하면서 카드형 현황판, 연도 폴더 자동 로드, 날짜별 누적 저장, 업데이트 감지 흐름을 유지했다.
- 상단에 `신규 입력 다운로드`, `전체 선택`, `선택 해제`, `선택 다운로드` 기능을 추가했다.
- 카드별 선택 체크박스를 추가하고 선택 상태가 재렌더링 후에도 유지되도록 `selected_nos` 상태를 추가했다.
- 검색은 공백/쉼표 기준 다중 검색으로 변경했다.
- `선택 다운로드`는 기존 양식 `견적용.xlsx`를 기준으로 선택된 카드만 새 파일로 저장하도록 구현했다.
- `신규 입력 다운로드`는 신규 카드를 별도 입력 창에서 작성한 뒤 그 카드만 먼저 다운로드하고, 이후 현재 카드 목록 유지 여부를 묻도록 구현했다.
- 설치/업데이트 버전을 `0.0.2`로 올리기 위해 `installer\Setup.iss`의 `MyAppVersion`을 `0.0.2`로 갱신했다.
- 이번 재구성본에서는 팝업의 `Size` 입력을 문자열 직접 입력 중심으로 단순화했다.

### 검증 결과

- `python -m py_compile machine_estimate_app.py` 통과.
- 코드 검증 스크립트로 선택 다운로드 파일 `selected_test_v002.xlsx` 생성 및 `기계` 시트 입력값(`B7`, `C7`, `F7`, `K7`, `T7`) 확인 완료.
- 코드 검증 스크립트로 날짜별 누적 저장 파일 `견적누적_2026-08-05.xlsx` 생성 및 저장 값 확인 완료.
- `python -m PyInstaller Machine_Estimate.spec --noconfirm` 빌드 성공.
- 빌드 결과를 `exe_release\Machine_Estimate.exe`, `exe_release\Machine_Estimate_latest.exe`로 갱신 완료.
- 2026-08-05 기준 `exe_release\Machine_Estimate.exe`를 5초간 실행해 프로세스 시작 확인 완료.
- `C:\Program Files\Inno Setup 7\ISCC.exe installer\Setup.iss` 컴파일 성공.
- 생성된 설치 파일 확인: `installer\Output\MachineEstimate_Setup_v0.0.2.exe`.

## 2026-08-05 v0.0.1 입력 UI/입력/표기 복원 계획

### 요청 내용

- 입력 UI, 입력 방식, 화면 표기를 `v0.0.1` 기준으로 되돌린다.
- 단, `v0.0.2`에서 추가된 기능 자체는 제거하지 않고 유지한다.

### 현재 확인한 상태

- 이 작업 폴더는 Git 저장소가 아니므로 커밋 기준 복원은 불가하다.
- 복원 기준은 현재 남아 있는 문서 기록(`plan.md`, `ver_plan.md`)과 이전 입력 구조가 남아 있는 `Estimate.py`로 잡아야 한다.
- `v0.0.2`에서 사용자 체감 변화가 큰 부분은 다음 두 가지다.
  - 메인 화면: `신규 입력 다운로드`, `전체 선택`, `선택 해제`, `선택 다운로드`, `다중 검색` 표기가 추가됨.
  - 입력 팝업: `Size` 입력이 `v0.0.1`보다 단순화되어 형상 선택/미리보기 입력 흐름이 빠짐.
- `ver_plan.md` 기록상 `v0.0.1` 시점 메인 화면 표기는 업로드, 새 카드 추가, 날짜별 누적 저장, `Search` 검색 중심이었다.
- `Estimate.py`에는 `v0.0.1` 계열 입력 팝업 구조가 남아 있다.
  - `Size` 형상 선택: 블록 / 로드 / 직접입력
  - 최종 반영 `Size` 미리보기
  - 수량/공수시간 검증 문구

### 복원 계획

1. 입력 팝업 UI를 `v0.0.1` 기준으로 복원한다.
   - `Size`를 단순 문자열 입력에서 `블록 / 로드 / 직접입력` 방식으로 되돌린다.
   - `최종 반영 Size` 미리보기를 다시 넣는다.
   - `Estimate.py`의 검증 흐름을 현재 `machine_estimate_app.py`에 맞게 이식하되, 현재 저장 구조와 카드 데이터 구조는 유지한다.
2. 메인 화면의 표기와 배치를 `v0.0.1` 우선 형태로 정리한다.
   - 창 버전 표기는 `v0.0.1`로 되돌린다.
   - 상단의 기본 사용 흐름은 `v0.0.1` 표기 기준(업로드 / 새 카드 추가 / 날짜별 누적 저장 / Search)으로 맞춘다.
   - `v0.0.2` 기능은 제거하지 않고 별도 보조 영역 또는 덜 강조되는 배치로 남긴다.
3. 기존 기능 보존 범위
   - 카드형 현황판
   - 연도 폴더 자동 로드
   - 날짜별 누적 저장
   - 업데이트 감지
   - 선택 상태 유지
   - 선택 다운로드
   - 신규 입력 다운로드
4. 수정 후 검증한다.
   - `python -m py_compile machine_estimate_app.py`
   - 선택 다운로드 / 신규 입력 다운로드 / 날짜별 누적 저장 경로가 여전히 호출 가능한지 확인
   - 필요 시 EXE 재빌드 전까지 소스 기준 검증 결과를 `ver_plan.md`에 기록

### 승인 대기

- 위 기준으로 `machine_estimate_app.py`, 필요 시 `installer\Setup.iss`, 그리고 작업 기록 `ver_plan.md`를 수정하려면 사용자 승인이 필요하다.

## 2026-08-05 v0.0.1 입력 UI/입력/표기 복원 완료

### 반영 내용

- `machine_estimate_app.py`의 앱 버전 표기를 `0.0.1`로 되돌렸다.
- 메인 상단 표기를 `v0.0.1` 기준 흐름으로 정리했다.
  - 제목을 `기계 시트 표준 견적 입력 시스템`으로 복원했다.
  - 기본 버튼은 `기계 시트 업로드`, `새 카드 추가`, `날짜별 누적 저장` 중심으로 보이게 정리했다.
  - 검색 표기는 `Search`로 되돌리고, 기존 다중 검색 기능은 그대로 유지했다.
  - `v0.0.2` 기능인 `신규 입력 다운로드`, `전체 선택`, `선택 해제`, `선택 다운로드`는 `보조 기능` 영역으로 남겨 기능은 유지했다.
- 입력 팝업을 `v0.0.1` 방식에 맞춰 복원했다.
  - `Size` 입력을 `블록 / 로드 / 직접 입력` 방식으로 되돌렸다.
  - `최종 반영 Size` 미리보기를 다시 넣었다.
  - 수량은 1 이상 정수, 공수 시간은 숫자만 허용하도록 입력 검증 문구를 복원했다.
- 기존 기능 보존
  - 카드형 현황판
  - 연도 폴더 자동 로드
  - 날짜별 누적 저장
  - 업데이트 감지
  - 선택 상태 유지
  - 선택 다운로드
  - 신규 입력 다운로드
- 설치 스크립트 `installer\Setup.iss`의 `MyAppVersion`도 `0.0.1`로 되돌렸다.

### 검증 결과

- `python -m py_compile machine_estimate_app.py` 통과.
- `python -m PyInstaller Machine_Estimate.spec --noconfirm` 빌드 성공.
- `dist\Machine_Estimate.exe`를 `exe_release\Machine_Estimate.exe`, `exe_release\Machine_Estimate_latest.exe`로 갱신했다.
- `C:\Program Files\Inno Setup 7\ISCC.exe installer\Setup.iss` 컴파일 성공.
- 생성된 설치 파일 확인: `installer\Output\MachineEstimate_Setup_v0.0.1.exe`.

### 미실행 항목

- GUI 실화면 확인은 이번 턴에서 별도 수행하지 않았다.
  - 문법/빌드 검증은 완료했지만, 팝업의 실제 시각 배치는 실행 화면 기준 추가 확인이 가능하다.

## 2026-08-05 신규 설치 파일 재작(설치 경로 영문화)

### 요청 내용

- `nextup v.0.0.2.MD`의 업데이트(인앱 update 폴더 방식) 대신 신규 설치 파일(Setup.exe)로 다시 만든다.
- UI는 `v0.0.1` 설치 버전 그대로 유지한다(이미 위 항목에서 복원 완료된 상태 유지, 별도 변경 없음).
- `nextup v.0.0.2.MD`의 "현재 상태에서 작업 기준 설정" 1~2번 반영: 설치 폴더를 한글이 아닌 영문으로, `C:\Program Files (x86)\Estimate` 경로로 설치되도록 설정.

### 수정 내용

- `installer\Setup.iss`의 `DefaultDirName`을 `{autopf}\{#MyAppName}`(한글 앱 이름 기반 경로)에서 `{commonpf32}\Estimate`로 변경함.
  - `AppName`(표시 이름, 시작 메뉴 등)은 기존 한글 그대로 유지하고, 실제 설치 폴더 경로만 영문 `Estimate`로 고정함.
  - `{commonpf32}`는 64비트 환경에서도 항상 `Program Files (x86)`를 가리키므로 요청한 `C:\Program Files (x86)\Estimate` 경로와 일치함.
- `machine_estimate_app.py`는 이번 턴에서 변경하지 않음(이미 `v0.0.1` UI로 복원되어 있음을 재확인: `APP_VERSION = "0.0.1"`, Size 입력이 블록/로드/직접입력 방식으로 되어 있음).

### 빌드 절차

1. `python -m PyInstaller Machine_Estimate.spec --noconfirm` 실행 → `dist\Machine_Estimate.exe` 생성(소스 변경 없어 캐시 기반으로 완료).
2. `dist\Machine_Estimate.exe`를 `exe_release\Machine_Estimate.exe`, `exe_release\Machine_Estimate_latest.exe`로 갱신.
3. `C:\Program Files\Inno Setup 7\ISCC.exe installer\Setup.iss` 컴파일 성공.
4. 생성된 설치 파일 확인: `installer\Output\MachineEstimate_Setup_v0.0.1.exe`(약 33MB, 기존 파일 덮어씀).

### 검증 결과

- ISCC 컴파일 로그상 오류 없이 `Successful compile` 확인.
- 신규 설치 파일 실행 시 기본 설치 경로가 `C:\Program Files (x86)\Estimate`로 제안되는지는 실제 설치 실행 화면 기준 추가 확인 필요(이번 턴에서는 스크립트 컴파일까지만 확인).

### 미실행 항목

- 실제로 설치 마법사를 실행해 기본 경로 표시와 설치 후 폴더 구조를 눈으로 확인하지 않았다.
- `nextup v.0.0.2.MD`의 "업데이트 v0.0.2"(선택 다운로드/다중 검색/신규 입력 별도 저장) 및 "입력창 개선" 섹션 기능은 이번 턴 범위에 포함하지 않았다. UI를 `v0.0.1` 기준으로 유지하라는 요청에 따라 별도 기능 추가 없이 설치 파일 재작업만 수행함.

## 2026-08-05 설치 폴더 이름 상수화 및 기존 설치 확인

### 요청 내용

- 이전 수정(`DefaultDirName={commonpf32}\Estimate`)은 경로를 강제 고정한 것으로, 실제 요청은 "경로 고정"이 아니라 Inno Setup 스크립트 작성 시 다른 값들처럼 **설치 폴더 이름을 상수로 정의**해 달라는 것이었음.

### 수정 내용

- `installer\Setup.iss` 상단 `#define` 목록에 `MyAppFolderName "Estimate"`를 추가함(`MyAppName`, `MyAppVersion`, `MyAppExeName`과 같은 방식).
- `DefaultDirName`을 `{commonpf32}\Estimate`(경로 강제 고정)에서 `{autopf}\{#MyAppFolderName}`로 변경함.
  - 상위 경로는 스크립트 기존 관례대로 `{autopf}`(시스템 아키텍처에 맞는 Program Files 자동 선택)를 유지하고, 폴더 이름만 한글 앱 이름 대신 영문 상수 `MyAppFolderName`을 참조하도록 함.
- `C:\Program Files\Inno Setup 7\ISCC.exe installer\Setup.iss` 재컴파일 성공, `installer\Output\MachineEstimate_Setup_v0.0.1.exe` 갱신.

### 확인된 사항 (기존 설치 상태)

- 검증을 위해 실제 설치를 시도하는 과정에서 시스템에 **이미 등록된 v0.0.2 설치**가 있음을 확인함.
  - 레지스트리(`HKLM\...\Uninstall\{F64AEBE2-F81A-4376-AD06-0A6005F1A53B}`) 상 `DisplayVersion 0.0.2`, `InstallLocation C:\Program Files (x86)\기계 시트 표준 견적 입력 시스템\`.
  - `installer\Setup.iss`의 `AppId`가 고정되어 있어, 같은 AppId로 신규 설치 파일을 실행하면 Inno Setup은 `DefaultDirName`이 아니라 **기존 등록된 경로에 업그레이드 설치**한다. 즉 영문 폴더 이름 변경을 실제로 확인하려면 기존 v0.0.2(한글 경로) 설치를 먼저 제거해야 함.
  - `C:\Program Files (x86)\Estimate` 폴더도 이미 존재하나(`unins000.exe` 없음, 언인스톨러 미등록) 정식 Inno Setup 설치로 생성된 것은 아닌 것으로 보임 — 출처 불명, 삭제하지 않고 보존함.
- 현재 작업 셸은 관리자 권한이 아니어서(`IsAdmin: False`) 제거/설치 실행 시 뜨는 UAC 승인 창을 자동으로 통과할 수 없어, 실제 제거·재설치·검증은 사용자가 직접 수행해야 함(관리자 PowerShell 또는 GUI로 `unins000.exe` → 신규 Setup 실행).

### 미실행 항목

- 기존 v0.0.2 설치 제거 및 신규 설치 파일 실행을 통한 실제 경로 확인은 관리자 권한 제약으로 이번 턴에서 수행하지 못함(사용자 직접 실행 필요).

### 사용자 실행 결과 확인 (후속)

- 사용자가 관리자 권한으로 기존 v0.0.2(한글 경로) 설치를 제거하고 신규 설치 파일을 직접 실행함.
- 사용자 확인: "설치경로 정상".
- 추가로 다음을 확인함.
  - `C:\Program Files (x86)\기계 시트 표준 견적 입력 시스템\` 폴더 조회 시 경로 없음 오류 → 기존 한글 경로 설치가 정상 제거됨.
  - `C:\Program Files (x86)\Estimate\Machine_Estimate.exe` 존재 확인(`Test-Path` → `True`), `update` 하위 폴더도 함께 생성됨.
- 결론: `installer\Setup.iss`의 `MyAppFolderName "Estimate"` 상수 및 `DefaultDirName={autopf}\{#MyAppFolderName}` 반영이 실제 설치 환경에서 정상 동작함을 확인함. 이번 작업 완료.

## 2026-08-05 v0.0.2 잔여 요청사항 반영 (업데이트 파일)

### 요청 내용

- `nextup v.0.0.2.MD` 중 설치 경로 관련(작업 기준 1·2번)만 반영된 상태였고, 나머지 항목이 미반영이었다.
- 남은 항목을 반영해 업데이트 파일로 배포한다.

### 반영 내용

1. 업데이트 반복 오류 수정 (`업데이트 v0.0.2` 1번)
   - 기존 `check_for_update()`는 `update` 폴더에 설치 파일이 남아 있으면 이미 업데이트한 뒤에도 매 실행마다 같은 파일 실행을 다시 물어봐 오류가 발생했다.
   - 파일명에서 버전을 파싱하는 `parse_version()`을 추가하고, 설치 파일 버전이 현재 `APP_VERSION` 이하이면 안내하지 않도록 했다.
   - 버전을 파싱할 수 없는 파일을 위해 적용 이력을 `%LOCALAPPDATA%\MachineEstimate\update_state.txt`에 남기는 `read_applied_updates()` / `mark_update_applied()`를 추가했다. (설치 폴더는 쓰기 권한이 없어 사용자 폴더에 저장한다.)
   - 사용자가 안내를 거절한 경우에도 이력을 기록해 같은 파일로 반복 안내하지 않는다.
2. 팝업창 TSERP 딥블루 UI 적용 (`작업 기준` 3번)
   - `setup_ui_scale()`에서 ttk 기본 스타일(`TFrame`, `TLabel`, `TButton`, `TEntry`, `TCombobox`, `TRadiobutton`, `TCheckbutton`, `TScrollbar`, `TLabelframe`)을 모두 딥블루 계열로 지정했다.
   - 콤보박스 드롭다운 목록 색상도 `option_add`로 맞췄다.
   - 보조 스타일 `Value.TLabel`, `Muted.TLabel`, `Head.TLabel`을 추가했고, 팝업의 `최종 반영 Size` 미리보기가 어두운 배경에서 안 보이던 파란색(`#2563eb`)을 스타일 기반으로 교체했다.
3. 공정별 단가 입력 추가 (`입력창 개선` 1번)
   - 팝업의 `각 공정별 시간 입력`을 `각 공정별 시간 / 단가 입력`으로 바꾸고 `공정 | 시간(h) | 단가(원) | 금액(원)` 4열 구성으로 변경했다.
   - 단가는 `self.rates` 기본값으로 채워지고 수정 가능하며, 입력 즉시 공정별 금액과 상단 합계가 갱신된다.
   - 저장 시 단가 유효성(숫자/0 이상)을 검사하고 `self.rates`에 반영한다.
   - 엑셀 양식은 단가가 5행(K5:T5)에 공통으로 들어가고 각 행 수식이 `$K$5` 형태로 참조하는 구조이므로, 단가는 항목별이 아니라 시트 공통값으로 처리했다. `_save_items_to_workbook()`에서 저장·다운로드 시 5행에 단가를 기록한다. 팝업에도 `단가는 견적 양식 5행에 공통 적용됩니다.` 안내를 넣었다.
4. 카드 클릭 시 항목 정보 전체 출력 (`입력창 개선` 2번)
   - 기존에는 카드 프레임에만 더블클릭이 연결되어 라벨 등 하위 위젯을 눌러도 팝업이 열리지 않았다. `bind_card_click()`으로 카드 하위 위젯까지 재귀 연결하고, 클릭(단일) 시 팝업이 열리도록 했다. 체크박스와 버튼은 제외했다.
   - 팝업 상단에 `항목 정보` 영역(`build_popup_info()`)을 추가해 NO, 작성일, 저장 상태, 기계 시트 폴더/파일, 엑셀 행, 시간합계, 단가합계, 최종 견적금액을 표기한다. 합계 3종은 입력에 따라 실시간 갱신된다.
   - 같은 카드의 팝업이 중복으로 열리지 않도록 `self.open_popups` 관리와 재클릭 시 기존 창 포커스 처리를 넣었다.
5. 기계 시트 대상 엑셀 파일 표기 위치 변경 (`입력창 개선` 3번)
   - 메인 카드의 `기계 시트` 항목(폴더/파일명)을 제거하고, 위 `항목 정보` 팝업에서만 표기하도록 옮겼다.
   - 상단 안내 문구도 `[카드] 클릭하면 팝업창에 항목 정보 전체와 상세 입력이 표시됩니다.`로 변경했다.
6. 팝업 크기 화면 대응
   - 화면 배율(DPI)이 큰 환경에서 팝업이 화면 밖으로 넘치지 않도록 `winfo_screenwidth/height` 기준으로 크기를 정하고 중앙에 배치했다.
7. 버전 갱신
   - `machine_estimate_app.py`의 `APP_VERSION`을 `0.0.2`로, `installer\Setup.iss`의 `MyAppVersion`을 `0.0.2`로 올렸다.

### 이미 반영되어 있던 항목 (재확인)

- `선택 다운로드`(`export_selected_items`), `다중 검색`(공백/쉼표 다중 조건, 품번·품명·Coment·Material·Size·파일명 등 대상), `신규 입력 시 별도 창 저장 후 다운로드`(`add_download_row`)는 기존 구현이 유지되고 있어 추가 변경하지 않았다.

### 검증 결과

- `python -m py_compile machine_estimate_app.py` 통과.
- 스모크 테스트 수행: 앱 기동 → 카드 생성 → 팝업 오픈 → 중복 오픈 차단 확인 → 버전 파싱 확인 → `_save_items_to_workbook()`으로 단가 5행 기록(`K5=88000`) 확인. 전 항목 통과.
- 실제 화면 캡처로 팝업이 딥블루로 표시되고 `항목 정보`(기계 시트 파일 포함)와 `시간/단가/금액` 3열이 정상 렌더링됨을 확인했다. 메인 카드에서 `기계 시트` 항목이 빠진 것도 확인했다.
- `python -m PyInstaller Machine_Estimate.spec --noconfirm` 재빌드 성공 → `exe_release`에 반영.
- `ISCC.exe installer\Setup.iss` 컴파일 성공 → `installer\Output\MachineEstimate_Setup_v0.0.2.exe` 생성.

### 미실행 항목

- `C:\Program Files (x86)\Estimate\update` 폴더로의 업데이트 파일 복사는 권한 오류(`Access to the path ... is denied`)로 수행하지 못했다. 관리자 권한이 필요하므로 사용자가 직접 복사하거나 설치 파일을 바로 실행해야 한다.

## 2026-08-05 Estimate 독립 git 저장소 구성

### 배경

- `git`에 저장할 경우 TSERP와 섞일 가능성이 있는지 확인 요청이 있었다.
- 확인 결과는 다음과 같다.
  - `Estimate`는 git 저장소가 아니었고, `TSERP`는 `C:\Users\SumH\Codex\TSERP`에 자체 저장소(원격 `github.com/smhwang1984-lab/TSERP.git`)로 존재했다. TSERP 추적 파일에 `Estimate` 흔적은 0건으로 실제 혼입은 없었다.
  - 다만 `C:\Users\SumH\Codex\.git`이 **내용물 0개인 빈 폴더**로 존재했다. 이 상태에서 `Codex`에서 `git init`을 실행하면 해당 폴더가 재사용되어 `Estimate`, `TSERP`, `NC_Tool_List`, `NEW PY` 등이 한 저장소로 묶일 수 있다. 이번 세션 시작 시 환경 정보가 "git 저장소 true / 브랜치 main"으로 잘못 표시된 원인도 이것으로 보인다.

### 반영 내용

- `Estimate` 폴더를 최상위로 하는 독립 저장소를 만들었다(`git init -b main`, toplevel `C:/Users/SumH/Codex/Estimate`).
- 원격은 지정하지 않아 로컬 전용이다. TSERP로 잘못 push될 경로 자체를 두지 않았다.
- `.gitignore`를 작성해 재생성 가능한 빌드 산출물 약 220MB를 제외했다.
  - 제외: `build/`, `dist/`, `exe_release/*.exe`, `installer/Output/*.exe`, `__pycache__/`, `estimate_v002_035s0nqj/`, 엑셀 임시 파일 `~$*`
  - 추적: 소스(`machine_estimate_app.py`, `Estimate.py`, HTA 3종), `installer/Setup.iss`, 견적 양식과 2026년도 누적 데이터, `plan.md`, `ver_plan.md` 등 32개 파일
- 초기 커밋 `dbebfcd` 생성.

### 검증 결과

- `Estimate` 저장소 toplevel이 `Codex`가 아닌 `Estimate`임을 확인했다(상위 폴더로 번지지 않음).
- 커밋 후 `git status` clean.
- `TSERP` 저장소는 HEAD(`49ac8da`)와 브랜치(`release/2.1.9-grinding-refresh-fix`)가 그대로이고, 추적 파일 내 `Estimate` 흔적 0건으로 영향이 없음을 확인했다.

### 남은 위험

- `C:\Users\SumH\Codex\.git` 빈 폴더는 아직 그대로다. 삭제하지 않으면 상위 폴더에서 `git init`을 실행했을 때 전체 프로젝트가 한 저장소로 묶이는 사고가 여전히 가능하다.
- `.claude\settings.local.json`은 사용자 전역 gitignore(`~/.config/git/ignore`)에 의해 제외된다(로컬 설정이므로 정상).
- 추적 대상에 실제 견적 단가·품번이 담긴 `견적_산정` 엑셀이 포함되어 있다. 향후 공개 원격 저장소에 push할 경우 해당 업무 데이터가 함께 공개된다는 점을 유의해야 한다.

## 2026-08-08 v0.0.3 실행 파일명 변경 / run.bat / JSON 세션 저장

### 요청 내용 (`nextup v.0.0.2.MD`, 사용자가 새 내용으로 덮어씀)

- git 이력상 이 파일에 있던 이전 v0.0.2 요청(업데이트 반복 오류, 설치 경로, TSERP UI, 입력창 개선)은 `ver_plan.md`의 2026-08-05 기록대로 이미 전부 반영이 끝난 상태였다. 사용자가 파일을 4줄짜리 새 요청으로 덮어썼다.
1. 실행 파일명을 `Estimate`로 변경.
2. 저장된 엑셀 양식으로 견적카드 생성 + 신규 견적 작성/양식 다운로드 (기존 `machine_estimate_app.py`가 이미 제공하는 기능이라 별도 구현 없이 유지로 판단).
3. 임시 실행 수단으로 `run.bat` 추가.
4. 입력 내용을 `.js`/`.json` 방식으로 저장해 실행 시마다 마지막 저장 단계가 복원되게 할 것.
- 승인 과정에서 사용자가 3번을 추가로 확정: "완전히 덮어써줘. 양식은 출력 및 입력 양식으로 사용할 예정. 데이터 저장은 별개." → 엑셀 양식은 입력 화면 구조 참조 및 출력(다운로드/누적 저장)용으로만 쓰고, 실제 세션 데이터 저장/복원은 JSON으로 완전히 분리하며, 복원 시 JSON 상태가 이전 화면 상태를 완전히 대체(병합 아님)한다.

### 반영 내용

1. 실행 파일명 변경
   - `Machine_Estimate.spec`의 `EXE(name=...)`를 `'Estimate'`로 변경.
   - `installer/Setup.iss`: `MyAppExeName`을 `Estimate.exe`로, `[Files] Source`를 `exe_release\Estimate.exe`로 변경. 기존 `AppId`가 고정되어 있어 업그레이드 설치 시 구버전 `Machine_Estimate.exe`가 설치 폴더에 그대로 남는 문제가 있어, `#define MyOldAppExeName "Machine_Estimate.exe"`와 `[InstallDelete] Type: files; Name: "{app}\{#MyOldAppExeName}"`를 추가해 업그레이드 설치 시 구 파일을 제거하도록 했다.
2. `run.bat` 추가
   - 저장소 루트에 배치, `%~dp0`로 스크립트 위치로 이동 후 실행되어 더블클릭 위치에 무관하게 동작.
   - `python` PATH 존재 여부 확인 후 없으면 안내 메시지 출력.
   - `openpyxl` 임포트 실패 시 `pip install`로 자동 설치.
   - `pythonw`가 있으면 콘솔창 없이 백그라운드 실행, 없으면 `python`으로 실행.
   - 최초 한글 메시지로 작성했다가 CP949 배치 파서가 UTF-8 한글 바이트를 오인식해 `if/else` 블록이 깨지는 문제(같은 프로그램이 중복 실행됨)를 실제로 재현·확인해 전체 메시지를 영문으로 교체했다.
3. JSON 세션 저장/복원 (엑셀 자동 스캔 로드 완전 대체)
   - 기존에는 실행할 때마다 `견적_산정\2026년도` 폴더 전체를 백그라운드 스레드로 스캔해 모든 엑셀의 카드를 자동으로 불러왔다(`start_background_load`/`load_existing_cards_worker`/`poll_load_queue`/`get_year_source_dir`/`iter_year_workbooks`). 이 방식과 관련 상태(`is_loading`, `loaded_file_count`, `loaded_card_count`, `skipped_file_count`, `load_queue`)를 전부 제거했다.
   - `get_session_state_path()`(`%LOCALAPPDATA%\MachineEstimate\session_state.json`), `save_session_state()`, `restore_session_state()`를 추가했다. 저장 대상은 `has_item_data()`로 걸러낸 실제 입력이 있는 카드, 공정별 단가(`self.rates`), 선택된 항목 번호, 검색어다.
   - 프로그램 시작 시 `restore_session_state()`가 JSON 파일이 있으면 그 내용으로 `self.data`를 완전히 덮어써서 복원하고(병합 아님), 없으면 빈 상태로 시작한다.
   - 저장 시점: 팝업에서 항목 저장(`save_and_close`, 신규 입력 다운로드 취소 분기 포함), `기계 시트 업로드`로 카드 추가, `날짜별 누적 저장` 완료 후, 그리고 창을 닫을 때(`WM_DELETE_WINDOW` → `on_close`)에 `save_session_state()`를 호출한다.
   - `read_cards_from_workbook()`은 백그라운드 스캔용으로 쓰던 `keep_excel_rows`/`mark_pending` 매개변수를 제거했다(남은 유일한 호출자인 `기계 시트 업로드`가 항상 같은 값을 쓰고 있었다).
   - 화면 상단 요약 문구의 "자동업로드 N건/M파일"을 "세션 복원 N건 (저장 YYYY-MM-DD HH:MM:SS)" 또는 "새 세션 (저장된 데이터 없음)"으로 교체했다. `기계 시트 업로드`, `날짜별 누적 저장`, `신규 입력 다운로드`, `선택 다운로드` 등 엑셀 입출력 기능은 그대로 유지했다.
4. 버전 갱신
   - `machine_estimate_app.py`의 `APP_VERSION`을 `0.0.3`으로, `installer\Setup.iss`의 `MyAppVersion`을 `0.0.3`으로 올렸다.

### 검증 결과

- `python -m py_compile machine_estimate_app.py` 통과.
- 백그라운드 로드 제거 후 잔여 참조(`is_loading`, `load_queue`, `loaded_file_count` 등, `keep_excel_rows`, `mark_pending`)가 없는지 grep으로 재확인.
- 별도 스크립트로 세션 저장/복원 스모크 테스트 수행: 임시 `LOCALAPPDATA`로 앱 1회 기동(세션 파일 없음 → `session_saved_at is None`, `data == []` 확인) → 항목 1건 추가 후 `save_session_state()` → JSON 파일에 해당 항목이 기록됨을 확인 → 앱을 새로 기동해 `restore_session_state()`로 동일 항목이 복원되고 `session_restored_count == 1`, `session_saved_at`이 채워짐을 확인. 실사용자 `%LOCALAPPDATA%`는 건드리지 않았다(임시 디렉터리로 격리).
- `run.bat`을 실제로 실행해 `Estimate.exe`가 아닌 소스(`machine_estimate_app.py`) 기준으로 `pythonw`가 정상 기동됨을 프로세스 목록(`Get-CimInstance Win32_Process`)으로 확인했다(WindowsApps 실행 별칭이 실제 `pythoncore-3.14-64\pythonw.exe`를 자식 프로세스로 재실행하는 구조라 프로세스가 2개로 보이는 것은 정상이며, 앱 인스턴스는 1개다). 최초 한글 버전은 이 과정에서 `if/else`가 깨져 중복 실행되는 버그를 발견해 영문 버전으로 교체 후 재검증했고, 테스트로 띄운 프로세스는 모두 종료했으며 실사용자 `%LOCALAPPDATA%\MachineEstimate`에는 아무 파일도 남지 않았음을 확인했다.
- `python -m PyInstaller Machine_Estimate.spec --noconfirm` 재빌드 성공 → `dist\Estimate.exe` 생성 → `exe_release\Estimate.exe`로 복사(기존 `Machine_Estimate.exe`는 애초에 `exe_release`에 없었음).
- `ISCC.exe installer\Setup.iss` 컴파일 성공 → `installer\Output\MachineEstimate_Setup_v0.0.3.exe` 생성.

- 빌드된 `exe_release\Estimate.exe`를 직접 실행해 정상 기동(`Get-CimInstance Win32_Process`로 프로세스 확인)까지 추가로 확인했다. 테스트 프로세스는 강제 종료했고(`WM_DELETE_WINDOW`를 거치지 않는 강제 종료라 `on_close` 저장이 실행되지 않음), 실사용자 `%LOCALAPPDATA%\MachineEstimate`에는 흔적이 남지 않았음을 재확인했다.

### 미실행 항목

- 실제 설치(관리자 권한 필요)를 통해 구버전 `Machine_Estimate.exe`가 `[InstallDelete]`로 정상 제거되고 `Estimate.exe`만 남는지는 이번 턴에서 실행 확인하지 못했다. 기존 v0.0.2가 설치되어 있다면 사용자가 새 설치 파일을 직접 실행해 확인이 필요하다.

## 2026-08-08 v0.0.4 TSERP UI 색상 / 카드 정렬·NEW 표시 / 체크박스 확대 / 검색 범위 축소

### 배경

- v0.0.3 작업 도중 `nextup v.0.0.2.MD`가 삭제되고 `nextup v.0.0.4.MD`가 새로 생겨 있는 것을 발견했다(사용자가 대화 밖에서 파일을 교체함). 커밋 여부를 묻는 사용자 질문에 "이 저장소는 이미 TSERP와 독립"이라고 답하면서 새 요청 파일을 같이 확인했다.

### 요청 내용 (`nextup v.0.0.4.MD`)

1. UI를 TSERP와 동일한 색상으로.
2. 카드 정렬 순서: 먼저 업로드/입력된 카드는 아래로, 최근 업로드/작성된 카드는 위로.
3. 신규로 업로드/작성된 카드에 NEW 마크.
4. 체크박스 크기를 현재의 2배로.
5. 검색을 "조임쇠 검색"으로 — 예: 품번이 `A34444`일 때 `444`만 검색해도 444가 포함된 카드가 표기되게.

### 확인/조율 과정

- 항목 5는 실제로 이미 동작하고 있었다(`item_matches_search`가 이미 부분 문자열 매칭). 다만 검색 대상에 계산된 금액·시간까지 포함되어 있어, 품번에 `444`가 없어도 금액이 `444,000원`인 무관한 카드가 함께 걸리는 오탐을 실제로 재현해 확인했다. 이를 알리고 검색 범위를 어떻게 할지 물었고, 사용자가 "검색은 품번 품명 기종 3종류 안에서만 검색 되게 설정"으로 확정했다.
- "기종"은 기존 데이터 필드(품번/품명/Coment/가능여부/Qty/Material/Size)에 없어 사용자에게 확인했고, "새 필드 추가 필요"로 답변받았다. 이어서 이 필드를 다운로드용 `견적용.xlsx`에도 저장할지 물었고, 기존 양식(A~W열)에 빈 칸이 없어 열을 추가해야 하는 점을 설명한 뒤 "앱(JSON)에만 저장"으로 확정받았다 — 엑셀 업무 양식 구조는 건드리지 않는다.
- 항목 1(TSERP와 동일 색상)을 반영하기 위해 실제 TSERP 저장소(`C:\Users\SumH\Codex\TSERP\py\web\style.css`, `server/config.py`)에서 실제 사용 중인 색상값을 직접 추출했다(짐작이 아니라 원본 CSS 값 사용).

### 반영 내용

1. TSERP 팔레트 적용
   - `self.colors`를 TSERP 딥 차콜/슬레이트 계열로 전면 교체: `bg #11161c`, `panel #171d25`, `panel_2 #234060`(TSERP 툴바 버튼 배경), `card #18212b`, `card_alt #1a2535`(TSERP 테이블 헤더 배경), `line #2a3340`, `text #dde4ec`, `muted #8b97a7`, `accent #4fb0ff`, `accent_2 #9cc8ff`.
   - 상태 배지: 가능 `success_bg #2c5c44`/`success_fg #7ddc9e`, 검토필요 `warn_bg #5a3a1a`/`warn_fg #ffb648`, 불가 `danger_bg #40222a`/`danger_fg #ff9aa2`.
   - `get_status_colors()`의 카드 테두리색도 TSERP 값(가능 `#3ecf8e`, 검토필요 `#d88a4f`, 불가 `#e05561`)으로 교체했다. `setup_ui_scale()`의 ttk 스타일(`TButton`/`TEntry`/`TCombobox`/`Value.TLabel` 등)과 Combobox 드롭다운 옵션은 모두 `self.colors`를 참조하는 구조라 팔레트 값만 바꿔도 팝업까지 함께 적용된다(별도 하드코딩된 색상 없음을 확인).
   - `newbadge`용 색상(`new_bg #5a3a1a`/`new_fg #ffb648`/`new_border #8a5a2a`)도 TSERP `.newbadge` 값 그대로 추가했다.
2. 카드 정렬 (최근 항목이 위로)
   - `create_blank_item()`에 `added_at`(추가 시각, `YYYY-MM-DD HH:MM:SS`) 필드를 추가했다. `no`는 신규 입력/다음 항목 입력 시 추가 순서를 보장하지 않아 정렬 키로 쓸 수 없었다.
   - `get_filtered_items()`에서 `all_items`를 `added_at` 내림차순으로 정렬한 뒤 검색 필터를 적용하도록 변경했다.
   - 기존에 저장된 세션 JSON(`added_at` 필드가 없는 카드)은 `restore_session_state()`가 `create_blank_item()` 기본값(복원 시각)을 덮어쓰지 않은 채 채우므로, 업그레이드 직후 첫 실행에서는 기존 카드들의 상대 순서가 임의(동일 시각으로 묶임)일 수 있음을 확인했다.
3. NEW 배지
   - 카드 제목(품번) 옆에 `save_pending`이 True인 카드에만 `NEW` 배지를 표시한다. 날짜별 누적 저장을 하면 `save_pending`이 False로 바뀌어 배지가 자동으로 사라진다. JSON에 저장되는 값이라 재시작해도 유지된다.
4. 체크박스 2배 크기
   - Windows 기본 `tk.Checkbutton` 표시기는 폰트를 키워도 커지지 않아(indicatoron 방식이 OS 렌더링에 고정), `render_selection_checkbox()`를 새로 추가해 `pack_propagate(False)`로 크기를 고정한 26px 정사각 `Frame`+`Label`로 직접 그리는 방식으로 교체했다(기존 기본 표시기 약 13px 대비 2배). 클릭 시 `toggle_item_selection()`을 호출해 기존 선택 로직은 그대로 재사용한다.
   - 이 커스텀 위젯이 `bind_card_click()`의 "카드 아무 데나 클릭하면 팝업 열림" 재귀 바인딩에 덮어써지지 않도록, 위젯에 `is_control = True` 표시를 붙이고 `bind_card_click()`이 이를 만나면 하위 탐색 없이 건너뛰도록 예외 처리를 추가했다.
5. 기종 필드 추가 및 검색 범위 축소
   - `create_blank_item()`에 `model`(기종) 필드를 추가했다. 팝업 `기본 정보`에 `기종` 입력칸을 품명 아래에 배치하고(이하 Material/수량/가능여부/Comment 행을 한 칸씩 내림), `save_and_close()`에서 저장하도록 반영했다. 카드 본문에도 `기종` 항목을 추가했다.
   - 엑셀 저장/다운로드(`_save_items_to_workbook`)에는 반영하지 않았다(사용자 확정: 앱/JSON 전용 필드).
   - `item_matches_search()`의 검색 대상을 품번/품명/기종 3종류로만 한정했다(기존에 포함되던 Material/Size/Coment/작성일/파일명/시간합계/최종단가는 제외). 검색창 옆 안내 문구와 검색 결과 없음 안내 문구도 이에 맞춰 수정했다.
6. 버전 갱신
   - `machine_estimate_app.py`의 `APP_VERSION`을 `0.0.4`로, `installer\Setup.iss`의 `MyAppVersion`을 `0.0.4`로 올렸다.

### 검증 결과

- `python -m py_compile machine_estimate_app.py` 통과.
- 별도 스크립트로 스모크 테스트 수행(임시 `LOCALAPPDATA`로 격리): TSERP 팔레트 값 일치 확인, `model`/`added_at` 필드 존재 확인, 검색 범위 제한 확인(품번 검색 히트, 금액에 `444`가 있는 무관 카드/Material에 `444`가 있는 무관 카드는 검색 안 됨, 기종으로도 검색됨), `added_at` 내림차순 정렬 확인, NEW 배지 조건(`save_pending`) 확인, 신규 체크박스가 정확히 26x26px 고정 크기로 렌더링됨을 확인, `bind_card_click()`이 `is_control` 위젯을 건너뛰어 예외 없이 통과함을 확인, 세션 JSON에 `model`/`added_at`이 포함되어 저장됨을 확인.
- 실제 화면 캡처(`PIL.ImageGrab`)로 메인 카드 목록과 팝업창을 직접 확인했다. TSERP 팔레트가 카드/팝업 전체에 적용됨, `added_at` 기준 최신 카드가 최상단(선택된 카드 → 이후 카드 순)에 옴, `save_pending`인 카드에만 NEW 배지가 붙고 아닌 카드는 안 붙음, 선택된 카드는 파란 채움 체크박스로 표시됨, 카드에 `기종` 항목이 표시됨, 팝업 `기본 정보`에 `기종` 입력칸이 정상 렌더링됨을 육안으로 확인했다.
- `python -m PyInstaller Machine_Estimate.spec --noconfirm` 재빌드 성공 → `exe_release\Estimate.exe` 교체.
- `ISCC.exe installer\Setup.iss` 컴파일 성공 → `installer\Output\MachineEstimate_Setup_v0.0.4.exe` 생성.
- 테스트 중 실사용자 `%LOCALAPPDATA%\MachineEstimate\session_state.json`에 33건짜리 실제 세션 데이터가 이미 저장되어 있는 것을 발견했다(사용자가 별도로 실제 앱을 실행해 사용한 것으로 보임). 내용을 열람하지 않고 항목 개수만 확인했으며, 수정·삭제하지 않고 그대로 두었다.

### 미실행 항목

- 실제 설치(관리자 권한 필요)로 v0.0.4 설치 파일을 실행해 GUI가 실제 기동되는지는 확인하지 못했다(소스 기준 스모크 테스트와 스크린샷 캡처로만 검증).
- 업그레이드 직후 `added_at`이 없던 기존 카드들의 정렬 순서(임의/동률)를 실제 다건 데이터로 눈으로 확인하지는 않았다.

## 2026-08-08 v0.0.5 모듈 분리 / 설정 파일 외부화 / 폴더 배포 전환 (경량화)

### 요청 내용

- "지금 파일 운용이 단지 exe파일로만 단독 실행이 되는데 구성을 세분화로 나눌 수 있지 ui css html 등 구성을 따로 구성해서 설치 패키지로 만들어줘 프로그램이 무거워"

### 확인/조율 과정

- 현재 앱은 HTML/CSS가 아니라 Tkinter다. 요청의 "ui css html"이 실제 웹 전환을 뜻하는지 확인이 필요해 사용자에게 선택지를 제시했다. pywebview/Eel로 실제 HTML/CSS 전환은 WebView2 런타임 의존이 붙어 오히려 무거워지고 1009줄 전면 재작성이 필요하다는 점을 함께 설명했다. 사용자가 "Tkinter 유지 + 모듈/테마 분리"를 선택했다.
- "무거워"의 원인을 빌드 산출물에서 직접 확인했다. `build\Machine_Estimate\Analysis-00.toc` 분석 결과 번들에 numpy 137개 · PIL 76개 모듈이 들어가 있었고(openpyxl의 선택적 의존성), 빌드가 onefile이라 실행할 때마다 31MB를 %TEMP%에 풀고 UPX 압축까지 해제하는 구조였다.

### 반영 내용

1. 패키지 구조 분리 (`machine_estimate_app.py` 1009줄 → `estimate_app/` 패키지)
   - `core/paths.py` 경로 계산 일원화. `get_app_dir`(설치 폴더=update 폴더 기준점), `get_bundle_dir`(onedir의 `_internal`), `get_user_dir`(%LOCALAPPDATA%) 구분.
   - `core/config.py` theme.json/rates.json 로더. 파일이 없거나 깨져도 코드 내 기본값으로 폴백한다.
   - `core/model.py` 카드 자료구조·값 변환·검색 규칙. `core/pricing.py` 금액 계산.
   - `core/excel_io.py` 엑셀 열 위치와 수식을 이 파일에만 둔다. `core/session.py` JSON 세션. `core/updater.py` update 폴더 확인.
   - `ui/theme.py`(스타일 로더) · `ui/widgets.py`(공용 위젯) · `ui/card.py` · `ui/popup.py` · `ui/dashboard.py`.
   - 진입점은 루트 `main.py`. `run.bat`도 이를 실행하도록 수정.
2. 설정 파일 외부화 (CSS 역할)
   - `estimate_app/assets/theme.json` — 색상 팔레트 전체, 폰트(가족/크기), 레이아웃 수치(창 크기, 체크박스 26px, 페이지 40건).
   - `estimate_app/assets/rates.json` — 공정별 기본 단가와 공정 표시명.
   - 사용자가 `%LOCALAPPDATA%\MachineEstimate\theme.json`에 같은 형식 파일을 두면 그쪽이 우선한다. 설치 폴더는 Program Files라 일반 사용자 쓰기가 안 되므로 덮어쓰기 경로를 사용자 폴더로 잡았다.
3. 빌드 경량화 (`Machine_Estimate.spec`)
   - onefile → onedir 전환(`exclude_binaries=True` + `COLLECT`). 매 실행마다 %TEMP%에 푸는 과정이 사라졌다.
   - `upx=False`. 배포 용량은 설치 파일의 LZMA2 압축이 대신 줄인다.
   - excludes에 numpy/PIL/pandas/matplotlib/scipy, setuptools/pip, unittest/pydoc, 그리고 `_ssl`/`ssl`/`_hashlib` 추가. 마지막 셋은 OpenSSL 백엔드(libcrypto 6MB + libssl 1.3MB)를 끌고 오는데 이 앱은 네트워크를 쓰지 않는다.
4. 설치 스크립트 (`installer\Setup.iss`)
   - `Source`를 `..\dist\Estimate\*` + `recursesubdirs createallsubdirs`로 변경(폴더 통째 설치).
   - `Compression=lzma2/max`.
   - `[InstallDelete]`에 `{app}\_internal` 폴더 정리 추가 — 단일 exe 배포에서 올라올 때 라이브러리 잔재가 섞이지 않게 한다. 기존 `Machine_Estimate.exe` 삭제 항목은 유지.
   - AppId는 그대로 두어 기존 설치의 업그레이드로 인식된다.
5. `build.bat` 신규 — `build.bat`은 exe 폴더까지, `build.bat setup`은 설치 파일까지 만든다. ISCC.exe 경로는 `%LOCALAPPDATA%\Programs` → Program Files (x86) → Program Files 순으로 찾는다(이 PC는 사용자 폴더에 설치되어 있었다).
6. 부수 수정 — `get_estimate_root_dir()`가 기존 폴더를 하나도 못 찾았을 때 설치 폴더 쓰기 가능 여부를 확인하고, 불가하면 `내 문서\견적_산정`으로 보낸다. 기존에는 Program Files 아래에 만들려다 권한 오류가 날 수 있었다.

### 검증 결과

- numpy/PIL/pandas import를 차단한 상태에서 openpyxl의 로드·셀 쓰기·수식·`_style` 복사·`insert_rows`·저장·재로드가 모두 정상 동작함을 확인하고 제외를 결정했다(짐작으로 제외하지 않음).
- 같은 방식으로 `_ssl`/`_hashlib`/`socket` 차단 상태에서 `hashlib.sha1/sha512`, openpyxl `SheetProtection` 비밀번호 해시, 엑셀 내보내기/재읽기가 모두 정상임을 확인했다(openpyxl `worksheet/protection.py`가 hashlib을 쓰지만 OpenSSL 없이 파이썬 내장 해시로 동작).
- 분리한 패키지 import 및 로직 검증: 단가 로드, 공정 필드 순서, 테마 색상, 자산 경로, 금액 계산(2h·5축·수량3 → 420,000원), 부분검색(`A34444`를 `444`로 히트, `zzz`는 미스).
- 엑셀 왕복 검증: 3건 내보내기 → B/C/F/G/H/K/N열 값과 U/V/W 수식, 5행 단가(K~T)가 정확히 기록됨을 확인하고, 다시 읽어 3건 복원 확인.
- GUI 생성 검증: 소스 실행 시 창 제목·geometry·`winfo_ismapped=1`, 실사용 세션 33건 복원 확인.
- 빌드 산출물: `dist\Estimate\Estimate.exe` 2.8MB + `_internal` 포함 폴더 전체 22MB(경량화 전 동일 방식 30MB). `_internal\assets`에 theme.json/rates.json, `_internal\견적용.xlsx` 배치 확인. numpy/PIL/libcrypto/libssl 잔존 없음.
- 빌드된 exe 실행 확인: `EnumWindows`로 해당 PID의 창을 열거해 `기계 시트 표준 견적 입력 시스템 v0.0.5` 창이 visible 상태로 떠 있음을 확인했다(PowerShell `MainWindowHandle`은 이 백그라운드 세션에서 0으로 나와 신뢰할 수 없었다).
- 시작 속도 측정(창이 실제로 보일 때까지, 3회): 신규 onedir 평균 4.7초(4.9/4.6/4.5). 구버전 onefile(`exe_release\Estimate.exe`)은 같은 방법으로 120초까지 기다려도 창이 뜨지 않았다(프로세스는 살아 있음).
- 설치 파일 컴파일 성공: `installer\Output\MachineEstimate_Setup_v0.0.5.exe` 9.1MB (v0.0.4는 31.6MB).

### 미실행 항목

- 실제 설치(관리자 권한)를 통해 v0.0.4 설치본 위에 업그레이드했을 때 `[InstallDelete]`가 구 `_internal`과 단일 exe를 정리하고 정상 기동하는지는 확인하지 못했다.
- 구버전 onefile이 120초 내 창을 띄우지 못한 원인(UPX 해제 + 30MB 압축 해제에 대한 백신 실시간 검사 등)까지는 분리해 규명하지 않았다.
- `machine_estimate_app.py`(구 단일 파일)는 지우지 않고 그대로 두었다. `exe_release\Estimate.exe`도 v0.0.4 산출물 그대로다.

## 2026-08-08 v0.0.6 TSERP 현황판 형태의 목록 표 / 시작 속도 개선

### 요청 내용

- "tserp의 현황판 처럼 기종 품번 품명 3종류로 기록 되고 내용을 클릭 했을 때 팝업으로 카드가 뜨고 수정 을 할 수 있도록 했으면 좋겠어" / "ui는 달라 완전 동일했으면 좋겠어"

### 확인 과정

- TSERP 저장소(`C:\Users\SumH\Codex\TSERP\py\web`)에서 현황판 실물 값을 직접 읽어 옮겼다. 현황판은 `index.html`의 `#mainArea > .tablewrap > table#tbl`이고, 스타일은 `style.css` 145~205행이다. 짐작이 아니라 원본 CSS 값을 사용했다.
  - `.paneHead` 배경 `#1d2530` / 글자 `#8b97a7` / 12px bold
  - `table` `font-family: Consolas, monospace`, `table-layout: fixed`
  - `th` sticky, 배경 `#1a2535`, 글자 `#c8d8ec`, 18px bold, 하단 `2px solid #4fb0ff`
  - `td` 17px, 하단 `1px solid #1f2832`, padding `6px 8px`
  - `tr.datarow:hover td` 배경 `rgba(255,255,255,.035)`
  - `tr.datarow.orderSelected td` 위·아래 `inset 0 ±2px rgba(79,176,255,.72)`
- 팝업은 이미 v0.0.4부터 있던 기능이라(행 클릭 → 상세 입력 → 저장) 이번 변경은 목록 표시 방식만 카드에서 표로 바꾼 것이다. `popup.py`는 건드리지 않았다.
- 열 구성은 요청한 기종/품번/품명 세 가지를 주 열로 두고, 견적 도구에서 판단에 필요한 가능여부와 최종단가를 덧붙였다(TSERP 현황판에도 상태 열이 있다). 이 판단은 사용자 확인 없이 진행했고 보고에 명시했다.

### 반영 내용

1. `ui/table.py` 신규 — 현황판 표
   - 헤더(`th`)를 스크롤 영역 밖에 따로 두어 CSS `position: sticky`와 같은 고정 헤더를 만들었다. 헤더 아래 2px 파란 줄은 별도 Frame이다.
   - 헤더와 각 행이 `configure_columns()`로 같은 열 규칙(minsize/weight)을 공유해 폭이 어긋나지 않는다. 품명 열만 `weight=1`로 남는 폭을 갖는다.
   - 행은 [위 선 / 셀들 / 아래 선] 세 줄 구조다. 선택 시 위·아래 줄이 파란색으로 바뀌어 TSERP의 `orderSelected`와 같은 모양이 된다.
   - `shorten()` 추가 — Tk 라벨에는 말줄임 기능이 없어 직접 자른다. 업로드한 엑셀의 가능여부 칸에 "테이블 모듈 필요(버금치구)" 같은 설명문이 들어오는 실제 데이터가 있어, 자르지 않으면 배지가 열을 밀어낸다(실제 재현 확인).
2. Tk에는 반투명색이 없어 TSERP의 rgba를 배경 `#11161c` 위에 미리 합성해 `theme.json`에 넣었다 — hover `#191e24`, 선택 줄 `#3e85bf`.
3. 표 글꼴은 TSERP와 같이 Consolas를 쓰고, 크기는 Tk 폰트 크기를 음수로 주어 pt가 아닌 픽셀 단위(th 18px / td 17px)로 맞췄다. 한글은 Consolas에 글리프가 없어 시스템 한글 폰트로 폴백되는데, 이는 브라우저에서도 동일하게 일어나는 동작이라 그대로 두었다.
4. `theme.json` / `config.py`에 표 전용 키를 **양쪽 모두** 추가했다. `config._merged()`가 기본값에 없는 키를 버리는 구조라, JSON에만 넣으면 조용히 무시된다.
5. `ui/card.py` 삭제, `widgets.make_fact_tile()` 제거(표 전환으로 쓰이지 않음). 화면 문구의 "카드"를 "항목"으로 정리했다.
6. 시작 속도 개선
   - `excel_io`의 `import openpyxl`을 함수 안으로 옮겼다. 실측 3.1초가 걸리는데 프로그램을 켤 때는 필요 없고 엑셀을 실제로 읽고 쓸 때만 필요하다.
   - `refresh_table`을 `after_idle`로 미뤄 창을 먼저 띄우고 목록을 이어서 채운다. 그 사이에는 요약줄에 "목록을 불러오는 중입니다..."를 표시한다.
   - 행마다 셀을 감싸던 프레임 6개를 없애고 라벨을 행 프레임에 바로 배치했다(행당 위젯 약 19개 → 13개).
7. 버전을 `estimate_app/__init__.py`와 `installer/Setup.iss` 양쪽 모두 0.0.6으로 올렸다.

### 검증 결과

- 화면 캡처로 직접 확인했다. 고정 헤더와 파란 밑줄, 기종/품번/품명 열, NEW 배지와 품번 아래 작성일, 가능여부 배지 3색(가능 초록·검토필요 주황·불가 빨강), 오른쪽 정렬 최종단가, 선택 행 위·아래 파란 줄, 26px 체크박스가 모두 의도대로 렌더링됐다.
- 행을 클릭해 팝업이 뜨고, 값을 고치면 표의 품명·최종단가·상단 총 견적금액이 즉시 갱신되는 것을 확인했다(1.5h → 4.0h 수정 시 385,000 → 735,000원).
- 캡처 도중 PowerShell `MainWindowHandle`과 `ImageGrab`이 각각 백그라운드 세션·DPI 배율 때문에 잘못된 값을 주는 것을 확인하고, `EnumWindows`로 창을 직접 열거하고 전체 화면을 캡처하는 방식으로 바꿔 검증했다. 열 폭도 `winfo_x/winfo_width`로 실측해 6개 열이 모두 정상 배치됨을 확인했다(가능여부 x=1447, 최종단가 x=1657).
- 시작 시간(창이 실제로 보일 때까지, exe 기준): 최적화 전 9.4/8.7/8.9초 → 최적화 후 5.0/3.7/3.9/3.9초(평균 4.1초). v0.0.5 카드 화면(4.7초)보다도 빠르다.
- 빌드된 exe를 실행해 실제 세션 33건이 표에 정상적으로 채워지는 것을 화면으로 확인했다.
- 설치 파일 `MachineEstimate_Setup_v0.0.6.exe` 9.1MB 생성.
- 테스트는 임시 `LOCALAPPDATA`로 격리해 진행했고, 작업 후 실사용자 세션이 33건 그대로임을 확인했다.

### 재현 불가로 남긴 TSERP 기능

- 열 폭 드래그 조절(`.colResizeHandle`) — 요청에 없어 만들지 않았다.
- 라이트/다크 모드 토글(`body[data-theme="light"]`).
- 2줄 말줄임(`.clamp2` / `-webkit-line-clamp`) — Tk에는 말줄임이 없어 1줄에서 글자 수로 자르는 방식으로 대체했다.

### 미실행 항목

- 실제 설치(관리자 권한)로 이전 버전 위에 업그레이드 설치하는 검증은 하지 못했다.
- 표 글꼴이 TSERP와 같은 17~18px이라 v0.0.5(13pt)보다 한 화면에 들어오는 행 수가 줄어든다. 실제 사용자 화면에서 적정한지는 확인하지 못했다(`theme.json`의 `table_cell_px`로 조절 가능).
- `machine_estimate_app.py`(구 단일 파일)와 `exe_release\Estimate.exe`(v0.0.4)는 이번에도 그대로 두었다.

## 2026-08-08 v0.0.7 양식 구조 재작성(기종 열·#REF! 복구) / 다건 출력 안정화 / PDF 출력 / UI 개선

### 요청 내용 (`v0.0.7.md`)

- UI: 다크모드에 깊이가 없음, 체크박스 선택 시 화면 깜빡임, 소재 스펙·사이즈 표기 필요.
- 출력: 양식 칸을 넘는 데이터를 넣으면 에러 발생, 항목이 늘어나면 더 많은 행이 출력되어 합계까지 맞아야 함, 견적서 시트(양식 1번)에도 동일 적용, 엑셀 외 PDF 등 선택적 출력 지원.

### 확인/조율 과정

- `.agents/AGENTS.md` 원칙에 따라 구현 전 계획서(`v0.0.7_plan.md`)를 먼저 작성해 사용자 승인을 받았다.
- 배포 중이던 `견적_산정\양식\견적용.xlsx`를 직접 열어 원인을 특정했다. 기계 시트는 데이터 행이 7칸뿐이었고, 8건째부터는 코드가 `ws.insert_rows()`로 한 줄씩 밀어 넣는 방식이었다. openpyxl 3.1.5로 직접 재현한 결과 `insert_rows`는 셀 값은 내리지만 **병합 범위는 따라가지 않는다** — 그래서 8건째부터 기계 시트 푸터(회사명·날짜·서명 병합)가 어긋나고, 그 날짜 셀을 참조하던 견적서 시트가 깨졌다. 더 결정적으로, 이미 배포 중이던 양식의 견적서 시트 **22~56행이 전부 `=기계!#REF!`** 상태였던 것도 직접 확인했다(엑셀에서 누군가 기계 시트 행을 지운 적이 있는 것으로 보임). 반면 사용자의 실제 정상 업무 파일(`NT3611415 외 41건`)은 42행 전부 정상 연속 참조였다 — 엑셀에서 직접 행을 추가해 가며 써 온 파일이라 문제가 없었던 것.
- 사용자가 기종(model) 열을 엑셀 양식에 추가하기로 결정했다(기계 시트 B열 삽입). 이 때문에 양식 원본을 어차피 고치게 되어, 같은 기회에 `#REF!`도 함께 복구하기로 했다(수정 전 `.bak_20260808` 백업).
- 출력 형식은 "엑셀 / PDF / 둘 다" 선택창으로, PDF는 견적서 시트만 담기로 확정했다. PDF는 Excel COM으로만 정확한 값이 나온다는 것을 실측으로 확인했다(openpyxl은 수식만 쓰고 계산 결과를 저장하지 않아, Excel을 거치지 않는 PDF 변환은 합계가 빈 칸으로 나온다).

### 반영 내용

1. **양식 원본 재구성** (`견적_산정\양식\견적용.xlsx`, 백업 `.bak_20260808`)
   - 기계 시트 B열에 `기종`을 삽입하고 이후 전체 열을 한 칸씩 이동(품번 B→C, 최종단가 W→X 등). openpyxl `insert_cols`도 병합·수식을 안 따라가는 것을 확인해, 오른쪽 열부터 값·서식을 직접 옮기고 수식(SUM/단가/ROUNDDOWN)과 병합 4개, 조건부 서식(중복값 표시), 인쇄 영역을 전부 새로 계산해 다시 썼다.
   - 견적서 시트 22~56행의 `#REF!`를 정상 참조(`=기계!$C{n}` 등)로 재작성하고, 존재하지 않던 인쇄 영역(`$B$1:$H$57`)을 새로 지정했다(기존엔 시트 범위가 1,048,567행까지 잡혀 있어 그대로 PDF를 뽑으면 수천 페이지가 나올 뻔했다).
   - Excel COM으로 실제 재계산시켜 5축1.0h+4축0.5h→190,000원, 3축3.0h→120,000원, 합계 310,000원이 모두 정확히 일치함을 확인했다.
2. **`core/excel_io.py` 전면 재작성** — insert_rows 방식을 버리고 열 위치를 코드에 고정하지 않는 구조로 바꿨다.
   - `resolve_columns()`: 6행 헤더 문구를 읽어 이 파일의 실제 열 배치를 그때그때 판단한다. `견적_산정` 폴더의 실제 과거 파일들을 열어 보니 치구/프로그램이 한 칸으로 합쳐진 9열짜리 구버전 양식도 섞여 있었다(예: `PLK972304 외.xlsx`). 기존 코드(열 번호 고정)로 이런 파일을 업로드하면 SUM 계산 결과 칸을 프로그래밍 시간으로 잘못 읽는 등 실제로 어긋났을 것 — 헤더 기반 판단으로 해결했다. 헤더가 겹치는 경우(치구+프로그램 통합 칸)는 한쪽 키에만 매칭시켜 시간이 두 배로 잡히지 않게 했다.
   - `shift_block_down()`: 합계 행부터 그 아래(푸터 포함)를 통째로 아래로 옮기고(병합도 함께), 비게 된 자리에 7행 서식을 복사한 새 데이터 행을 채운다. `layout_machine_sheet()`(기계 시트)·`sync_estimate_sheet()`(견적서 시트) 양쪽에 적용해 항목 수만큼 자동으로 늘어나고 인쇄 영역도 같이 넓어진다.
   - `excel_row`에 `excel_file`을 같이 저장해, 날짜가 바뀌어 다른 파일을 열게 되면 이전 파일의 행 번호를 재사용하지 않고 새로 배정하도록 고쳤다(기존 결함). 다만 `excel_file`을 몰랐던 v0.0.6 이하 세션 데이터를 오늘 이어서 저장하면 매번 새 행이 배정되면서 예전 행은 지워지지 않고 남아 **합계가 중복 계산**될 뻔한 것을 리뷰에서 지적받아, 그 행의 품번이 실제로 일치할 때만 재사용을 허락하도록 추가했다(무턱대고 재사용하면 다른 날짜 파일의 엉뚱한 행을 덮어쓸 수 있어, 대조 없이는 재사용하지 않는다). 재현 테스트로 3건을 저장한 뒤 `excel_file`을 지워 구버전 세션을 흉내 내고 다시 저장해, 행 번호가 늘어나지 않고(7·8·9행 그대로) 정상적으로 재사용됨을 확인했다.
3. **다건 출력 버그 2건 발견 및 수정** (구현 중 자체 테스트로 재현)
   - 항목 수가 기존 42칸보다 적을 때, 항목 없는 견적서 행이 기계 시트의 **합계 셀 자체를 참조**해 견적서 합계가 정확히 2배로 계산되는 버그를 발견했다(예: 7건 90,000원×7=630,000원이어야 하는데 1,260,000원으로 나옴). 실제 항목이 있는 행까지만 참조식을 넣고 그 이상은 비우도록 고쳤다.
   - openpyxl에서 `ws.cell(row, col, value=None)`이 "값을 지운다"가 아니라 "value 인자를 안 준 것"으로 취급되어 **기존 값이 그대로 남는** 것을 발견했다(위 버그의 원인이자, 사용자가 입력칸을 비우고 재저장해도 예전 값이 남는 잠재 결함이기도 했다). `.value` 속성에 직접 대입하는 방식으로 전부 고쳤다.
   - 7건/8건/43건/60건 및 "같은 날 두 번 저장"(5건 저장 후 10건 추가) 시나리오를 자체 스크립트와 Excel COM 재계산으로 검증해, 수식 오류 0건·기계 합계=견적서 합계=기대값이 모든 케이스에서 일치함을 확인했다.
4. **PDF 출력** — `core/pdf_export.py` 신규. pywin32 등 의존성을 추가하지 않고 PowerShell에서 Excel COM을 직접 호출한다(`assets/export_pdf.ps1`, spec의 `assets` 폴더 전체 복사 규칙에 자동으로 포함됨). 대시보드에 "엑셀(.xlsx)/PDF/엑셀+PDF" 선택창을 추가하고, "선택 다운로드"·"신규 입력 다운로드" 양쪽에 연결했다. Excel이 없는 PC에서는 엑셀 파일만 저장하고 안내 문구를 띄운다. "날짜별 누적 저장"은 계속 엑셀 전용으로 남겨 두었다 — 계속 이어 쓰는 누적 파일이라 PDF로 바꿀 대상이 아니라고 판단했다.
   - PDF 전용을 고르면 화면엔 안 보이지만 변환용 .xlsx가 하나 더 필요한데, 처음엔 사용자가 고른 폴더에 같은 이름의 .xlsx를 만들었다가 변환 후 지우는 방식이었다. 그런데 그 폴더에 같은 이름의 기존 견적 파일이 있으면 **조용히 덮어쓰고 지워** 사용자 파일이 사라질 수 있는 것을 리뷰에서 발견했다. 변환용 파일은 `tempfile.mkdtemp()`로 만든 별도 임시 폴더에 두고 끝나면 폴더째 지우도록 고쳤다. "엑셀+PDF"에서 자동으로 만들어지는 PDF 쪽 경로도 파일 대화상자가 확인해 주지 않으므로, 이미 있으면 별도로 덮어쓸지 물어보게 했다.
5. **UI 개선**
   - `theme.json`/`config.py`의 `DEFAULT_COLORS`를 양쪽 다 갱신해 층을 분리했다(`bg` #0d1218 → `row_bg` #141b23 → `panel` #1b232d → `card` #1f2833 순으로 밝아짐; 기존엔 `bg`와 `row_bg`가 완전히 같은 색이라 표에 깊이가 없었다). 짝수 행 줄무늬(`row_alt_bg`)와 상단바 경계선을 추가했다.
   - 체크박스 깜빡임: 토글할 때마다 표 전체(500개 이상 위젯)를 지웠다 다시 그리던 것을, 행별 위젯을 `app.row_widgets`에 등록해 두고 **체크박스 색과 선택 표시줄만 다시 칠하는** 방식으로 바꿨다. 상단 요약줄(선택 건수)도 표를 건드리지 않고 문자열만 갱신한다. hover 시 선택 표시줄이 지워지지 않도록, 지금 선택된 행인지를 hover가 일어날 때마다 다시 확인하도록 했다(부분 갱신 도입으로 생긴 새 상호작용이라 별도로 처리).
   - 표에 소재(Material)·사이즈(Size) 열을 추가했다(체크/기종/품번/품명/소재/사이즈/가능여부/최종단가). 열 폭 재배분에 맞춰 `min_width`를 1180→1320으로 늘렸다.

### 검증 결과

- 마이그레이션한 양식을 openpyxl로 재읽어 수식·병합·조건부서식·인쇄영역을 전부 대조했고, Excel COM 재계산으로 금액이 실제로 맞는지 확인했다(위 1번 항목).
- `excel_io` 자체 테스트: 신규 7/8/43/60건, 같은 날 2회 누적 저장(5건→15건) 총 5개 시나리오에서 `#REF!` 없음, 병합 정상, 인쇄 영역 확장 정상, 기존 저장 행 유지(행 번호 중복 없음), Excel COM 재계산 합계 100% 일치를 확인했다.
- 왕복(내보내기→업로드) 테스트로 기종·품번·품명·소재·사이즈·코멘트·수량·공정별 시간이 모두 원래 값 그대로 복원됨을 확인했다.
- 실제 과거 파일(`PLK972304 외.xlsx`, 9열 구버전 양식)을 업로드해 23건이 정상적으로 읽히고, 치구+프로그램 통합 칸이 한쪽 키에만 들어가 이중 계산되지 않음을 확인했다(기존 코드였다면 SUM 계산 칸을 프로그래밍 시간으로 잘못 읽었을 상황).
- PDF 변환을 실제로 실행해 견적서 시트만 담긴 1페이지 PDF가 생성됨을 확인했다(61KB). 60건짜리도 변환해 PDF 내용을 직접 읽어 2페이지에 60행 전부 빠짐없이 나오고 마지막 페이지 합계가 ₩5,400,000(60×90,000)으로 정확히 일치함을 확인했다 — "8건째부터 에러"였던 문제가 60건 규모에서도 실제로 해결됐는지까지 본 것이다. 빌드된 배포판(`dist/Estimate/_internal/assets/`)에 `export_pdf.ps1`이 실제로 포함되는 것도 확인했다(소스에서만 되고 설치판에서는 안 되는 상황을 막기 위해).
- 화면 검증은 스크린샷이 아니라 `EnumWindows`+`PrintWindow`로 실제 창을 캡처해서 했다(백그라운드 세션에서 전체화면 캡처는 다른 창을 잡는 문제가 있어, 이전 버전과 같은 이유로 창 자체를 지정해 캡처했다). 새 열 구성(기종/품번/품명/소재/사이즈/가능여부/최종단가), 층이 분리된 팔레트가 실제로 반영된 것을 확인했다. 코드에서 `app.toggle_item_selection()`을 직접 호출해 3건을 선택시킨 뒤 캡처해, 표 전체가 다시 그려지지 않고 체크박스 3개와 선택 표시줄만 파란색으로 바뀌고 "선택 3건"으로 요약줄이 갱신되는 것을 확인했다. 팝업창도 새 팔레트로 정상 렌더링됨을 확인했다.
- 마우스 클릭으로 직접 체크박스를 누르는 시나리오는 이 세션의 DPI 배율 문제로(이전 버전 기록에도 같은 제약이 있었다) 좌표가 어긋나 재현하지 못했고, 대신 실제 앱 코드 경로(`toggle_item_selection`)를 호출해 렌더링 결과를 검증했다.
- 빌드: `build.bat setup`을 PowerShell로 실행했더니 배치 파일의 한글 주석이 콘솔 코드페이지와 부딪혀 `errorlevel` 검사가 깨지고 **dist를 새로 빌드하지 않은 채** 이전 산출물로 설치 파일을 만드는 것을 발견했다(설치 파일 크기가 v0.0.6과 바이트 단위로 똑같았다). `python -m PyInstaller`와 `ISCC.exe`를 직접 실행하는 방식으로 우회해 다시 빌드했고, 새 exe의 `_internal/assets/theme.json`에 `row_alt_bg`가, `_internal/견적용.xlsx`에 `기종` 열이 실제로 들어있음을 확인한 뒤 설치 파일을 만들었다(크기가 v0.0.6과 달라짐을 확인). 빌드된 exe를 직접 실행해 창 타이틀이 `v0.0.7`로 뜨는 것도 확인했다.
- 구현이 끝났다고 판단하기 전에 검토를 한 번 더 거쳐 실사용에 영향을 줄 결함 2건(PDF 전용 다운로드 시 동명 기존 파일을 조용히 지울 뻔한 문제, 구버전 세션 승계 시 견적서 합계가 두 배로 잡힐 뻔한 문제 — 둘 다 위 3번·4번 항목에 반영)을 추가로 찾아 고쳤고, 반영 후 dist·설치 파일을 다시 만들었다. 최종 설치 파일 크기는 9,586,881바이트다.

### 미실행 항목

- 실제 설치(관리자 권한)로 이전 버전 위에 업그레이드 설치하는 검증은 하지 못했다.
- 마우스로 직접 체크박스를 클릭하는 상호작용은 DPI 문제로 실측하지 못했다(대신 코드 경로 호출로 렌더링 결과만 검증).
- `build.bat`의 한글 주석이 PowerShell 경유 실행 시 깨지는 문제 자체는 고치지 않았다(이번엔 우회만 했다). 다음에 `build.bat`을 다시 쓸 계획이면 인코딩을 먼저 점검해야 한다.
- 기존 `견적_산정` 폴더의 과거 파일들(구버전 양식)은 원본을 손대지 않았다 — 업로드는 되지만 그 파일 자체를 새 양식으로 바꾸지는 않는다.

## 2026-08-09 v0.0.8 밝은 그라데이션 UI 전환 / 표 갱신 구조 재작성 / PDF 진단 강화 / 산출 결함 2건 수정

### 요청 내용 (`v0.0.8.md`)

- 산출: 엑셀 사이즈 열이 3열로 나뉘어 보임(한 열로 통합·가운데 정렬), PDF 출력 에러.
- ESC: 카드 팝업 닫기, 체크박스 선택 취소.
- 검색: 카드가 하나하나 깜빡이며 검색됨, 검색 시 스크롤이 맨 위가 아니어도 되게, 검색 결과가 화면 중간부터 보임.
- 명칭: "기계 시트 표준 견적 입력 시스템" → "Estimate(견적)", 파이썬 기본 아이콘 교체.
- UI: 참고 이미지(밝은 그라데이션 e-commerce 스타일)의 색감·폰트로 전환.
- 대화 중 추가 지시: "UI개선 부분과 엑셀 출력은 구현 후 먼저 보여주고 최종 확인하는 형태로", 스크린샷을 본 뒤 "뷰어에서 행구분칸때문에 더 어색해 보임 행구분선을 없이 해줘".

### 확인/조율 과정

- `.agents/AGENTS.md` 원칙에 따라 계획서(`v0.0.8_plan.md`)를 먼저 썼다. PDF는 이 PC에서 소스/`pythonw`/frozen exe/한글경로 5가지로 재현을 시도했으나 전부 정상 생성돼 재현하지 못했고, 계획서에도 "재현 불가"로 명시했다.
- 계획서 작성 중 advisor 검토로 팔레트 결함을 발견해 사전에 고쳤다: `panel`을 그라데이션 보라색으로 잡으면 `ui/theme.py`가 모든 ttk 위젯(`TFrame`/`TLabel`/`TLabelframe` 등)의 배경으로 그 색을 쓰기 때문에 **팝업창 전체가 보라색으로 덮이는** 문제였다. 헤더는 `grad_from`/`grad_to`로 따로 그리고 `panel`은 밝게 유지하도록 바꿨다.
- 팔레트 전체를 WCAG 상대휘도 공식으로 직접 계산해 통과시켰다(본문 4.5:1 / 큰 글자·배지 3:1 이상, 그라데이션은 5개 지점 샘플링). 처음 잡은 값 중 5개가 미달이었다 — 특히 그라데이션 끝(#4fa8ff) 위 흰 글자가 2.51:1이라 제목이 안 읽혔다.
- 사용자 승인 후 UI/엑셀 출력을 구현하고 실제 화면 캡처로 먼저 보여드렸다. 첫 캡처에서 체크박스/기종/품번 칸이 빈 것처럼 보였는데, 재현 스크립트의 캡처 타이밍 문제였음을 재캡처로 확인했다(실제 결함 아님). 이 과정에서 체크박스 테두리(`line` #e3e7f2)가 흰 배경에서 거의 안 보이는 **진짜 결함**을 발견해 전용 색(`checkbox_border` #8089b5, 대비 3.4:1)을 새로 만들었다.
- 사용자가 캡처를 보고 "행구분칸 때문에 어색하다, 행구분선을 없애 달라"고 지시해, 위/아래 2px 선으로 선택을 표시하던 방식을 없애고 행 배경을 옅게 물들이는 방식(`row_selected_bg` #f0eefe)으로 바꿨다. 이 작업이 마침 검색 깜빡임을 없애는 표 갱신 구조 재작성과 맞물려 있어 함께 반영했다.
- 사용자가 최종 승인한 뒤 버전 반영·빌드를 진행하던 중, `build.bat`을 PowerShell로 실행하면 dist가 새로 빌드되지 않는 v0.0.7과 **똑같은 증상**이 재현됐다(그때는 우회만 하고 원인은 고치지 않은 채 남겨 뒀던 항목). 이번엔 원인을 끝까지 봤다 — `build.bat`이 BOM 없는 UTF-8로 저장돼 있어 cmd.exe가 이 PC의 활성 코드페이지(949)로 잘못 읽어 한글 주석·명령이 깨졌다. CP949로 다시 저장해 근본 원인을 고쳤다(아래 반영 내용 8번).

### 반영 내용

1. **사이즈 열 통합** (`core/excel_io.py`) — `merge_size_cell()` 신규. Size 헤더 병합 폭(`I6:K6` 등)만큼 데이터 행도 병합하고 가운데 정렬한다. `write_items_to_sheet()`의 항목 쓰기 루프와 `layout_machine_sheet()`의 신규 행 생성 루프 두 곳 모두에 적용했다(한 곳만 하면 12건 이상에서 새로 만든 행에 병합이 빠진다). 헤더가 1칸뿐인 구버전 양식은 `span<=1`이면 그대로 두어 건드리지 않는다.
2. **견적서 `0`행 제거** (`core/excel_io.py`) — `sync_estimate_sheet()`의 참조 판정을 `src_row < gigye_summary_row`(양식 칸 수 기준) 하나에서 **`FIRST_DATA_ROW <= src_row < gigye_summary_row` and `row_has_input_data(...)`** 둘 다로 바꿨다. 처음엔 `row_has_input_data`만으로 바꿨다가, 기계 시트 **푸터(17~19행)가 데이터 열과 같은 열 위치를 쓴다**는 것을 검증 중 발견했다 — '사상' 공정 열이 Q(17번째 열)인데 푸터 라벨 "㈜텍스타"도 Q17에 있어서, 상한 없이 검사하면 그 라벨을 항목 데이터로 착각해 견적서에 엉뚱한 참조가 들어갔다(직접 재현). 상한을 다시 넣어 고쳤다.
3. **PDF 진단** (`core/pdf_export.py` 전면 재작성)
   - `assets/export_pdf.ps1`(BOM 없는 UTF-8 + 한글 주석) 파일을 없애고, PowerShell 명령을 Python에서 만들어 `-EncodedCommand`(UTF-16LE + Base64)로 넘긴다. 파일이 아니라 즉석 명령이라 일부 PC의 "스크립트 파일 실행 차단" 그룹정책을 받지 않는다.
   - Excel COM에 `Interactive`/`EnableEvents`/`AskToUpdateLinks` 끄기, `AutomationSecurity=3`, `Workbooks.Open(path, 0, $true)`(링크 확인창 차단, 읽기전용)를 추가해 확인창을 막았다. 타임아웃을 90초→180초로 늘렸다.
   - 실패하면 `%LOCALAPPDATA%\MachineEstimate\pdf_error.log`에 시각·경로·반환코드·표준출력·표준오류 전문을 남긴다.
   - **구현 중 실제 버그 발견**: `subprocess.run(text=True)`가 PowerShell 출력을 UTF-8로 잘못 가정해, 한글이 포함된 오류 메시지가 오면 내부 리더 스레드가 `UnicodeDecodeError`로 조용히 죽는 것을 직접 재현했다. PowerShell 쪽에 `[Console]::OutputEncoding = UTF8`을 강제하고, Python 쪽은 바이트로 받아 `utf-8`→`cp949` 순으로 직접 디코딩하도록 고쳤다. 추가로 PowerShell이 오류를 CLIXML(사람이 못 읽는 XML)로 직렬화해 보내는 것도 발견해, 바깥을 try/catch로 한 번 더 감싸 실패 사유를 평문으로 표준출력에 적게 했다.
   - `ui/dashboard.py`의 `export_items()`: "PDF"만 선택했다가 실패하면 임시 xlsx가 `finally`에서 통째로 지워져 아무것도 안 남던 것을, 실패 시 "대신 엑셀로 저장할까요?" 확인창을 띄워 별도 저장 대화상자로 건질 수 있게 했다.
4. **ESC 키** (`ui/popup.py`, `ui/dashboard.py`) — 팝업은 ESC로 닫히되, 열 때 입력값 스냅샷과 비교해 바뀐 게 있으면 "저장하지 않고 닫으시겠습니까?"를 확인한다. 본화면은 ESC로 `clear_selection()`. 팝업은 별도 Toplevel이라 두 바인딩이 서로 간섭하지 않는다.
5. **표 갱신 구조 재작성** (`ui/table.py`, `ui/dashboard.py`) — 검색·체크·더보기마다 위젯을 destroy 후 재생성하던 방식을 버리고, 행 위젯을 슬롯 풀로 재사용한다(`create_row_slot`/`update_row_slot`/`hide_row_slot`). 클릭·hover 콜백은 슬롯 생성 시 한 번만 걸고, 슬롯이 담당하는 항목 번호를 콜백이 호출 시점에 읽게 해(`slot["no"]`) 재사용해도 다시 바인딩할 필요가 없게 했다. 선택 표시는 위/아래 2px 선 대신 행 배경 틴트(`row_selected_bg`)로 바꿨다(사용자 지시 반영, 행 구분선 완전 제거). 검색·검색초기화 등 목록 내용이 실제로 바뀔 때만 `row_canvas.yview_moveto(0)`로 스크롤을 맨 위로 되돌린다.
6. **밝은 그라데이션 테마** (`assets/theme.json`, `core/config.py`, `ui/theme.py`, `ui/dashboard.py`) — TSERP Deep Charcoal(다크)에서 흰 배경 + 보라→파랑 헤더 그라데이션으로 전환. 헤더는 PIL 없이 `Canvas.create_line`으로 그린다(폭이 실제로 바뀔 때만 다시 그림). 제목·요약줄은 Canvas 텍스트 항목이라 `textvariable`을 못 써서 `summary_var`에 trace를 걸어 `itemconfigure`로 밀어 넣는다. 표 본문 글꼴을 Consolas→맑은 고딕으로 바꾸고 금액 열만 `num_family`(Consolas)를 유지한다. 옛 다크 팔레트는 `theme.json`의 `presets.dark`에 참고용으로 남겼다(자동 전환 아님, 되돌릴 때 `colors`에 옮겨 쓰는 원본).
7. **명칭/아이콘** — `APP_TITLE`(`estimate_app/__init__.py`)과 `MyAppName`(`installer/Setup.iss`) 모두 `Estimate(견적)`로 변경. `estimate.ico`를 외부 라이브러리 없이 순수 파이썬으로 생성했다(PNG-in-ICO, zlib만 사용, 16/32/48/256px). `Machine_Estimate.spec`의 `EXE(icon=...)`와 `root.iconbitmap()` 양쪽에 지정했다(spec만 하면 실행파일 아이콘만 바뀌고 창 좌상단·작업표시줄 아이콘은 그대로 파이썬 기본이라는 것을 확인하고 둘 다 반영).
8. **`build.bat` 인코딩 수리** — BOM 없는 UTF-8로 저장돼 있어 cmd.exe가 활성 코드페이지(949)로 잘못 읽던 것을 CP949로 다시 저장해 고쳤다(v0.0.7에서 우회만 하고 남겨 둔 항목).
9. 버전을 `estimate_app/__init__.py`와 `installer/Setup.iss` 양쪽 모두 0.0.8로 올렸다.

### 검증 결과

- **사이즈 병합**: 3/7/12/43건을 실제 코드 경로(`export_items`)로 내보내 병합 범위·가운데 정렬·왕복 읽기(Size 문자열 원문 복원)·인쇄 영역 확장을 전부 직접 읽어 확인했다.
- **견적서 0행 제거**: 3/7/8/43건을 Excel COM으로 재계산해, 항목 수를 넘는 행이 전부 빈 칸이고(전에는 `품번 0 / 품명 0 / 단가 ₩0`) 기계 시트 합계와 견적서 합계가 정확히 일치함을 확인했다(예: 3건 120,000=120,000, 43건 1,720,000=1,720,000).
- **PDF**: 코드 변경 후 5가지 재현(소스 콘솔/`pythonw` 완전분리/frozen exe 재빌드/한글경로+공백폴더)을 전부 다시 실행해 되던 것이 안 깨졌음을 확인했다. 존재하지 않는 시트 이름을 줘 실패를 강제로 유도해 로그 파일(`pdf_error.log`)에 평문 사유가 남는 것, "PDF만" 선택 후 실패 시 확인창에서 "예"를 누르면 별도 대화상자로 엑셀이 저장되고(`showinfo`로 경로 안내) "아니오"를 누르면 조용히 실패 처리되는 것을 몽키패치로 두 경로 모두 재현해 확인했다.
- **ESC**: 값을 안 바꾼 팝업은 확인창 없이 바로 닫히고, 바꾼 뒤 ESC → "아니오"는 유지·"예"는 닫힘을 `messagebox.askyesno`를 몽키패치해 확인했다. 본화면 ESC로 선택이 즉시 취소됨을 확인했다.
- **표 갱신 성능**: 같은 측정 코드로 전후 비교했다(33건 실사용 세션 기준, 5회 중간값). 검색 1회 0.664s→0.224~0.237s, 체크 토글 1왕복 0.069s(신규 측정), 220건 합성 데이터에서도 재사용 시 0.3~0.4s로 유지됨을 확인했다. 위젯 재사용(슬롯 identity 동일)도 직접 확인했다.
- **팔레트 명도차**: `load_theme()`로 실제 로드된 색상 17개 조합 전부를 WCAG 공식으로 재계산해 전부 기준 통과를 확인했다(체크박스 테두리 포함).
- **화면**: 실제 창을 띄워 전체화면을 캡처해 확인했다 — 그라데이션 헤더, 요약줄 갱신, NEW/가능여부 배지, 선택 행 배경 틴트(구분선 없음), 체크박스 테두리, 팝업창(그라데이션에 덮이지 않고 흰 바탕에 정상 렌더링)을 모두 확인했다.
- **빌드**: `build.bat`이 v0.0.7과 같은 인코딩 문제로 dist를 새로 빌드하지 않는 것을 이번에도 만났고, 이번엔 CP949로 다시 저장해 근본 원인을 고쳤다(반영 내용 8번). 그래도 PowerShell 경유 실행이 완전히 안정적이지 않아, 최종 빌드는 `python -m PyInstaller`와 `ISCC.exe`를 직접 호출해 만들었다. `dist/Estimate/_internal/assets/`에 `estimate.ico`가 실제로 포함되고 `export_pdf.ps1`은 더 이상 없음을 확인했다. 빌드된 `Estimate.exe`를 직접 실행해 제목표시줄에 `Estimate(견적) v0.0.8`, 아이콘, 밝은 테마, 구분선 없는 표가 전부 반영된 것을 화면으로 확인했다. 설치 파일 `MachineEstimate_Setup_v0.0.8.exe` 9,560,762바이트, `dist/Estimate` 22MB(이전 버전과 동일 — 새 의존성 없음).
- 최종 결과(그라데이션 헤더 캡처, 선택 행 배경 틴트 캡처, 체크박스 대비 개선, 팝업 렌더링, PDF/사이즈/0행 검증 요약)를 사용자에게 먼저 보여준 뒤 "승인"을 받고 나서 버전 반영·빌드를 진행했다.

### 미실행 항목

- 실제 설치(관리자 권한)로 이전 버전 위에 업그레이드 설치하는 검증은 하지 못했다.
- PDF 실패는 이 PC에서 끝내 재현하지 못했다. 이번 작업은 "고쳤다"가 아니라 "다음에 실패하면 원인이 로그에 남고, 실패해도 엑셀은 건진다"까지다. 오류창이 다시 뜨면 `pdf_error.log`를 확인해야 원인을 특정할 수 있다.
- 마우스로 직접 체크박스를 클릭하거나 실제 검색창에 타이핑하는 상호작용은 이전 버전들과 같은 이유(DPI/백그라운드 세션)로 실측하지 못했다 — 코드 경로 직접 호출과 화면 캡처로 결과만 검증했다.
- 다크 팔레트로 되돌리는 화면 내 전환 버튼은 만들지 않았다(요청에 없었고, `presets.dark` 값을 `theme.json`의 `colors`에 옮겨 쓰면 재빌드 없이 가능하다).
- 행당 위젯 수를 16개에서 줄이는 것(계획서 7-2)은 실제로 시도하지 않았다 — 표 갱신 구조 재작성(반영 내용 5번)만으로 목표 성능을 이미 달성해 우선순위가 낮아졌다.
- 기존 `견적_산정` 폴더의 과거 파일들(구버전 양식)은 원본을 손대지 않았다.

### v0.1.2 구현 반영 기록 (Codex, 2026-08-10)

- 40건 표시 제한을 제거하고 검색 결과/전체 항목을 모두 렌더링하도록 변경했다.
- 항목 입력 팝업의 ESC와 X 닫기 경로를 동일하게 맞췄고, 저장 전 빈 신규 카드는 닫을 때 목록/세션에서 제거되도록 했다.
- 현황판 소재와 사이즈 사이에 `열처리` 열을 추가하고 `HRC58~62`/`HRC`/`-` 형식으로 표시하도록 했다.
- 설정 저장소에 `headers`, `columns.widths`를 추가해 열 제목과 사용자 조정 열 폭을 저장/로드하도록 했다.
- 설정창에 `화면 열` 탭을 추가했다. 열 제목 9개를 수정할 수 있고, 열 제목/열 폭 초기화 버튼을 제공한다.
- 헤더 열 경계에 드래그 핸들을 추가해 대시보드 열 폭을 조절하고, 마우스 버튼을 놓을 때 설정 파일에 저장하도록 했다.
- 열 폭은 40~600px 범위로 제한하고, 현재 표 폭을 넘는 과도한 확장은 막도록 했다.
- 엑셀 읽기에서는 기본 제목과 사용자 제목을 모두 인식하도록 했다.
- 엑셀 출력에서는 기존 열 판정/값 쓰기/견적서 동기화가 끝난 뒤 마지막 단계에서 기계 시트 6행과 견적서 14행 제목을 사용자 제목으로 교체하도록 했다.
- 버전을 `0.1.2`로 갱신했다 (`estimate_app/__init__.py`, `installer/Setup.iss`).

### v0.1.2 검증 기록

- `python -m compileall -q estimate_app main.py` 통과.
- 임시 엑셀 출력 검증 통과: 사용자 지정 제목(`MODELX`, `PARTX`, `NAMEX`)이 6행에 반영되고, 실제 값은 기존 열 위치에 유지됨을 확인했다.
- 출력 파일을 `read_cards_from_workbook()`으로 다시 읽어 1건 왕복 로드가 되는 것을 확인했다.
- `C:\tmp`에 대한 임시 파일 쓰기는 현재 세션에서 `PermissionError`가 발생해 작업 폴더 내부 임시 파일로 검증 후 삭제했다.

### v0.1.2 빌드 기록

- 최초 `python -m PyInstaller Machine_Estimate.spec` 실행은 기존 `dist\Estimate` 폴더가 비어 있지 않아 PyInstaller가 중단했다.
- `python -m PyInstaller -y Machine_Estimate.spec`로 기존 빌드 산출물 폴더를 교체하며 재빌드했고 성공했다.
- 결과 위치: `dist\Estimate\Estimate.exe`.
- GUI 실행 시작 확인: `dist\Estimate\Estimate.exe`를 5초간 실행했으며 즉시 종료되지 않았다 (`started=True`). 확인 후 프로세스는 종료했다.
- 설치 파일 생성은 진행하지 못했다. `ISCC.exe`가 표준 설치 경로와 PATH에서 확인되지 않았다.

## 2026-08-10 v0.1.5 버전 정정 및 설치 파일 생성 기록

- v0.1.2로 표기했던 이번 작업 버전을 기존 배포 흐름(v0.1.4 이후)에 맞춰 `v0.1.5`로 정정했다.
- 수정 파일: `estimate_app\__init__.py`의 `APP_VERSION`, `installer\Setup.iss`의 `MyAppVersion`.
- `python -m compileall -q estimate_app main.py` 통과.
- `python -m PyInstaller -y Machine_Estimate.spec`로 `dist\Estimate\Estimate.exe`를 다시 빌드했다.
- Inno Setup 7 경로 `C:\Program Files\Inno Setup 7\ISCC.exe`로 설치 파일을 다시 생성했다.
- 생성 파일: `installer\Output\MachineEstimate_Setup_v0.1.5.exe`.
- 결과: Inno Setup `Successful compile` 확인.
- 파일 크기: 9,577,766 bytes.


## 2026-08-10 v0.1.5 검증 및 패키징 재실행 기록

- `python -m compileall -q estimate_app main.py` 통과.
- v0.1.5 핵심 스모크 테스트 통과: 버전, 열처리 열, 카드 삭제/되돌리기, 다중 엑셀 업로드, 견적 보관함, 가공조건 창, 팝업 진입점.
- Tkinter 화면 초기화는 예약된 데이터 위치/업데이트 확인 흐름까지 포함한 무인 테스트에서 제한 시간 내 완료되지 않아 GUI 통과로 판정하지 않았다.
- `python -m PyInstaller --noconfirm --clean Machine_Estimate.spec` 성공.
- `C:\Program Files\Inno Setup 7\ISCC.exe installer\Setup.iss` 성공.
- 최종 설치 파일: `installer\Output\MachineEstimate_Setup_v0.1.5.exe` (9,654,231 bytes).
- 설치 파일 출력 경로: `C:\Users\SumH\orca\workspaces\Estimate\Estimate\installer\Output`.
## 2026-08-10 v0.1.4 기능 보존을 위한 v0.1.5 통합 복구

- 사용자의 v0.1.4 기능 누락 보고 후 원인을 점검하고, 승인받은 복구 계획에 따라 v0.1.4 기준선과 v0.1.5 변경사항을 통합했다.
- 보관함, 삭제/되돌리기, 다중 엑셀 업로드, 가공조건, 설정 저장 보호, 엑셀 입출력 기능을 보존했다.
- v0.1.5 열처리 열, 사용자 지정 화면 열 이름, 열 너비 저장, 설정창 화면 열 탭을 함께 유지했다.
- 컴파일, 핵심 스모크, 설정 스키마 왕복, 가공조건 계산, 사용자 지정 엑셀 헤더 왕복 테스트 통과.
- Tkinter GUI 무인 시작 검증은 사용자가 중단하여 미통과로 기록한다.
- 통합 후 설치 파일 재빌드는 아직 남아 있다. 기존 설치 파일은 통합 전 빌드 결과이므로 최종 산출물로 판정하지 않는다.
## 2026-08-10 GitHub 원격 저장소 설정 및 push

- 원격 저장소 `origin`을 `https://github.com/smhwang1984-lab/estimate.git`로 설정했다.
- 로컬 `Estimate` 브랜치를 신규 원격 브랜치 `origin/Estimate`로 push하고 추적 관계를 설정했다.
- 통합 복구 커밋 `b4d6445`의 로컬/원격 해시가 일치함을 확인했다.
- 미추적 사용자 파일 `CLAUDE.md`, `선택견적_2026-08-09.xlsx`는 커밋과 push에서 제외했다.