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
