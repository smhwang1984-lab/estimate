; 기계 시트 표준 견적 입력 시스템 설치 스크립트
; Inno Setup Compiler(ISCC.exe)로 컴파일한다.
; AppId는 이후 버전에서도 동일 설치로 인식되도록 고정한다. 변경하지 말 것.

#define MyAppName "기계 시트 표준 견적 입력 시스템"
#define MyAppFolderName "Estimate"
#define MyAppVersion "0.0.4"
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
Compression=lzma
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
Source: "..\exe_release\Estimate.exe"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
Name: "{app}\update"

[InstallDelete]
; v0.0.2 이하 버전은 실행 파일명이 Machine_Estimate.exe였다. 이름 변경 후 구 파일이 남지 않도록 업그레이드 설치 시 삭제한다.
Type: files; Name: "{app}\{#MyOldAppExeName}"

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
