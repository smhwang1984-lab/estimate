; 기계 시트 표준 견적 입력 시스템 설치 스크립트
; Inno Setup Compiler(ISCC.exe)로 컴파일한다.
; AppId는 이후 버전에서도 동일 설치로 인식되도록 고정한다. 변경하지 말 것.
;
; v0.0.5부터 배포 형태가 단일 exe에서 폴더(onedir)로 바뀌었다.
; 프로그램 본체는 {app}\Estimate.exe, 나머지 런타임은 {app}\_internal 아래로 들어간다.
; 설정 파일(theme.json / rates.json)은 {app}\_internal\assets 에 놓이고,
; 사용자가 색이나 단가를 직접 고치고 싶으면 %LOCALAPPDATA%\MachineEstimate 에 같은 이름으로 두면 그쪽이 우선한다.

#define MyAppName "Estimate(견적)"
#define MyAppFolderName "Estimate"
#define MyAppVersion "0.0.8"
#define MyAppExeName "Estimate.exe"
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
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"

[Tasks]
Name: "desktopicon"; Description: "바탕화면에 아이콘 만들기"; GroupDescription: "추가 아이콘:"; Flags: unchecked

[Files]
; onedir 빌드 결과 폴더를 통째로 설치한다.
Source: "..\dist\Estimate\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Dirs]
Name: "{app}\update"

[InstallDelete]
; v0.0.2 이하: 실행 파일명이 Machine_Estimate.exe였다.
Type: files; Name: "{app}\{#MyOldAppExeName}"
; v0.0.4 이하: 단일 exe 배포였다. 폴더 배포로 바뀌면서 남은 옛 파일과
; 옛 _internal 잔재를 지워야 라이브러리 버전이 섞이지 않는다.
Type: filesandordirs; Name: "{app}\_internal"

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
