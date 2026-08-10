; 기계 시트 표준 견적 입력 시스템 설치 스크립트
; Inno Setup Compiler(ISCC.exe)로 컴파일한다.
; AppId는 이후 버전에서도 동일 설치로 인식되도록 고정한다. 변경하지 말 것.
;
; v0.0.5부터 배포 형태가 단일 exe에서 폴더(onedir)로 바뀌었다.
; 프로그램 본체는 {app}\Estimate.exe, 나머지 런타임은 {app}\_internal 아래로 들어간다.
; 설정 파일(theme.json / rates.json)은 {app}\_internal\assets 에 놓이고,
; 사용자가 색이나 단가를 직접 고치고 싶으면 %LOCALAPPDATA%\MachineEstimate 에 같은 이름으로 두면 그쪽이 우선한다.
;
; v0.0.9 아이콘 처리 — "바탕화면 바로가기가 아직 파이썬 아이콘"이라는 지적에 대한 대응이다.
; 확인해 보니 exe에는 아이콘이 정상적으로 박혀 있고 바로가기도 exe를 제대로 가리키고 있었다
; (dist·설치본 양쪽에서 리소스를 추출해 확인). 남은 원인은 윈도우 셸의 아이콘 캐시로,
; v0.0.2~v0.0.4 시절 같은 경로에 있던 파이썬 아이콘이 캐시에 남아 계속 쓰이는 것이다.
; 그래서 아래 네 가지를 함께 건다.
;   1) estimate.ico를 {app}에 따로 설치하고 바로가기가 그 파일을 직접 가리키게 한다(IconFilename).
;      아이콘 출처가 exe가 아니게 되어 exe 단위로 굳어 버린 캐시를 피해 간다.
;   2) 기존 바로가기를 지우고 새로 만든다(InstallDelete + desktopicon).
;   3) ChangesAssociations=yes 로 설치 후 셸에 변경을 알린다(SHChangeNotify).
;   4) ie4uinit.exe -show 로 아이콘 캐시를 다시 만들게 한다.
; 주의: desktopicon 작업의 unchecked 플래그를 없앤 것은 실수가 아니다. InstallDelete는 작업
; 선택과 무관하게 실행되므로, 체크되지 않은 채 설치하면 기존 바로가기만 지워지고 새로
; 만들어지지 않아 바탕화면에서 아이콘이 아예 사라진다.

#define MyAppName "Estimate(견적)"
#define MyAppFolderName "Estimate"
#define MyAppVersion "0.1.5"
#define MyAppExeName "Estimate.exe"
#define MyAppIconName "estimate.ico"
#define MyOldAppExeName "Machine_Estimate.exe"

[Setup]
AppId={{F64AEBE2-F81A-4376-AD06-0A6005F1A53B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\{#MyAppFolderName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=admin
OutputDir=Output
OutputBaseFilename=MachineEstimate_Setup_v{#MyAppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=yes
UninstallDisplayIcon={app}\{#MyAppIconName}
; 설치가 끝나면 셸에 알려 아이콘 캐시를 다시 읽게 한다.
ChangesAssociations=yes

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"

[Tasks]
Name: "desktopicon"; Description: "바탕화면에 아이콘 만들기"; GroupDescription: "추가 아이콘:"

[Files]
; onedir 빌드 결과 폴더를 통째로 설치한다.
Source: "..\dist\Estimate\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; 바로가기가 직접 가리킬 아이콘 파일. (빌드 결과의 _internal\assets 에도 같은 파일이 있지만,
; 바로가기가 참조할 경로는 버전이 바뀌어도 흔들리지 않게 {app} 바로 아래에 둔다.)
Source: "..\estimate_app\assets\{#MyAppIconName}"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
Name: "{app}\update"

[InstallDelete]
; v0.0.2 이하: 실행 파일명이 Machine_Estimate.exe였다.
Type: files; Name: "{app}\{#MyOldAppExeName}"
; v0.0.4 이하: 단일 exe 배포였다. 폴더 배포로 바뀌면서 남은 옛 파일과
; 옛 _internal 잔재를 지워야 라이브러리 버전이 섞이지 않는다.
Type: filesandordirs; Name: "{app}\_internal"
; v0.0.8 이하에서 만들어진 바로가기는 아이콘 출처가 exe라 옛 캐시를 계속 물고 있다.
; 지우고 아래 [Icons]에서 새로 만든다.
; 관리자 설치라 {autodesktop}은 모든 사용자 바탕화면(C:\Users\Public\Desktop)을 가리킨다.
; 실제로 기존 바로가기가 놓여 있던 자리도 거기다(직접 확인). 개인 계정 바탕화면
; ({userdesktop})은 건드리지 않는다 — 관리자 권한으로 올라간 계정 기준이라 엉뚱한 곳을
; 지울 수 있고, Inno도 그 조합을 경고한다.
Type: files; Name: "{autodesktop}\{#MyAppName}.lnk"
Type: files; Name: "{group}\{#MyAppName}.lnk"

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppIconName}"; IconIndex: 0
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppIconName}"; IconIndex: 0; Tasks: desktopicon

[Run]
; 셸 아이콘 캐시를 다시 만들게 한다. 실패해도 설치는 계속되어야 하므로 오류를 무시한다.
Filename: "{sys}\ie4uinit.exe"; Parameters: "-show"; Flags: runhidden skipifdoesntexist
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
