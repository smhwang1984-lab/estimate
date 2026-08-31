@echo off
REM 빌드 + 설치 파일 생성 한 번에.
REM   build.bat        exe 폴더(dist\Estimate)만 만든다
REM   build.bat setup  설치 파일(installer\Output)까지 만든다
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found in PATH.
    exit /b 1
)

echo [1/3] Cleaning previous build...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo [2/3] Building with PyInstaller (onedir)...
python -m PyInstaller --noconfirm Machine_Estimate.spec
if errorlevel 1 (
    echo [ERROR] PyInstaller build failed.
    exit /b 1
)

if /i not "%~1"=="setup" (
    echo.
    echo [DONE] Output: dist\Estimate\Estimate.exe
    echo        Run "build.bat setup" to also create the installer.
    exit /b 0
)

echo [3/3] Compiling installer with Inno Setup...
REM Inno Setup은 설치 방식에 따라 위치가 달라진다. 흔한 세 곳을 차례로 본다.
set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" (
    echo [ERROR] ISCC.exe not found. Install Inno Setup 6 first.
    echo         https://jrsoftware.org/isdl.php
    exit /b 1
)
"%ISCC%" installer\Setup.iss
if errorlevel 1 (
    echo [ERROR] Inno Setup compile failed.
    exit /b 1
)

echo.
echo [DONE] Installer: installer\Output
endlocal
