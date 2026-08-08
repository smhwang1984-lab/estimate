"""엑셀 파일의 한 시트를 PDF로 내보낸다.

openpyxl로 쓴 수식은 계산 결과값이 저장되어 있지 않다(엑셀이 열 때 계산한다).
그래서 엑셀을 거치지 않는 PDF 변환(reportlab 등)은 합계·최종단가가 빈 칸으로 나온다.
Microsoft Excel을 실제로 실행해 재계산시키는 방법만 값이 맞으므로 Excel COM을 쓴다.
pywin32 의존성을 추가하지 않으려고 PowerShell에서 COM을 직접 호출한다.

v0.0.8: 스크립트 파일(-File) 대신 -EncodedCommand로 명령을 통째로 넘긴다. 이유 둘.
  1. 일부 PC의 그룹 정책은 .ps1 "스크립트 파일" 실행 자체를 막는다. -EncodedCommand는
     파일이 아니라 즉석 명령이라 그 제한을 받지 않는다.
  2. 예전 방식(assets/export_pdf.ps1, BOM 없는 UTF-8 + 한글 주석)은 PowerShell 5.1이
     BOM 없는 .ps1을 시스템 ANSI 코드페이지로 읽는 잠재 위험이 있었다. 명령을 Python에서
     만들어 UTF-16LE로 인코딩해 넘기면 이 문제 자체가 사라진다.
이 PC에서는 재현되지 않는 실패라(0-2 참고) 원인을 못 찍었다. 대신 실패하면
%LOCALAPPDATA%\\MachineEstimate\\pdf_error.log에 사유를 남겨 다음에는 원인을 알 수 있게 한다.
"""

import base64
import os
import subprocess
from datetime import datetime

from . import paths

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
TIMEOUT_SECONDS = 180
LOG_FILE = "pdf_error.log"


def _ps_literal(value):
    """PowerShell 홑따옴표 문자열 리터럴로 안전하게 감싼다(홑따옴표만 두 번 반복하면 된다)."""
    return "'" + str(value).replace("'", "''") + "'"


def _build_ps_command(xlsx_path, pdf_path, sheet_name):
    """Excel COM으로 시트 하나를 PDF로 내보내는 PowerShell 명령 전문.

    - AutomationSecurity=3(msoAutomationSecurityForceDisable): 매크로 보안 경고창이
      뜨지 않게 한다.
    - Interactive/EnableEvents/AskToUpdateLinks를 꺼서 팝업이 하나도 안 뜨게 한다.
    - Workbooks.Open(path, 0, $true): UpdateLinks=0(링크 갱신 확인창 안 뜸),
      ReadOnly=$true(원본을 실수로 고치지 않음).
    - Console 출력 인코딩을 UTF-8로 고정한다. 한글 Windows는 콘솔 기본 코드페이지가
      cp949라 Excel 오류 메시지가 그 코드페이지로 나오는데, 파이썬 쪽은 UTF-8로 읽는다
      (직접 재현 확인: 안 맞추면 오류 메시지 디코딩 단계에서 리더 스레드가 죽는다).
    - 바깥을 한 번 더 try/catch로 감싸 실패 사유를 Write-Output(표준출력)으로 평문 출력한다.
      안 감싸면 PowerShell이 콘솔이 아닌 대상으로 리디렉션될 때 오류를 CLIXML로 직렬화해
      내보내는데(사람이 못 읽는 XML 뭉치, 직접 재현 확인), 로그에 그대로 남으면 다음에
      원인을 읽기 어렵다.
    """
    return (
        "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8\n"
        "$OutputEncoding = [System.Text.Encoding]::UTF8\n"
        "$ErrorActionPreference = 'Stop'\n"
        "try {\n"
        "    $excel = $null\n"
        "    try {\n"
        "        $excel = New-Object -ComObject Excel.Application\n"
        "        $excel.Visible = $false\n"
        "        $excel.DisplayAlerts = $false\n"
        "        $excel.Interactive = $false\n"
        "        $excel.EnableEvents = $false\n"
        "        $excel.AskToUpdateLinks = $false\n"
        "        $excel.AutomationSecurity = 3\n"
        f"        $wb = $excel.Workbooks.Open({_ps_literal(xlsx_path)}, 0, $true)\n"
        "        try {\n"
        f"            $ws = $wb.Sheets.Item({_ps_literal(sheet_name)})\n"
        f"            $ws.ExportAsFixedFormat(0, {_ps_literal(pdf_path)})\n"
        "        } finally {\n"
        "            $wb.Close($false)\n"
        "        }\n"
        "    } finally {\n"
        "        if ($excel) {\n"
        "            $excel.Quit()\n"
        "            [System.Runtime.Interopservices.Marshal]::ReleaseComObject($excel) | Out-Null\n"
        "        }\n"
        "    }\n"
        "} catch {\n"
        "    Write-Output ('PDF 변환 실패: ' + $_.Exception.Message)\n"
        "    exit 1\n"
        "}\n"
    )


def _log_failure(xlsx_path, pdf_path, returncode, stdout, stderr, note=None):
    """실패 사유를 사용자 폴더에 남긴다. 화면 안내창이 사라져도 다음에 원인을 알 수 있게."""
    paths.ensure_user_dir()
    log_path = paths.get_user_file(LOG_FILE)
    lines = [
        "=" * 60,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        f"xlsx: {xlsx_path}",
        f"pdf : {pdf_path}",
        f"returncode: {returncode}",
        f"stdout: {stdout or '(없음)'}",
        f"stderr: {stderr or '(없음)'}",
    ]
    if note:
        lines.append(f"비고: {note}")
    try:
        with open(log_path, "a", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
    except OSError:
        return None
    return log_path


def _decode_console_bytes(data):
    """PowerShell 출력 바이트를 안전하게 문자열로 바꾼다.

    subprocess.run(text=True)에 맡기면 내부 리더 스레드가 자체적으로 디코딩하다
    깨진 바이트를 만나면 그 스레드가 통째로 죽는다(직접 재현 확인 -- UnicodeDecodeError
    가 콘솔에만 찍히고 조용히 삼켜진다). 그래서 바이트로 받은 뒤 여기서 직접,
    실패해도 절대 죽지 않는 방식으로 디코딩한다.
    """
    if not data:
        return ""
    for encoding in ("utf-8", "cp949"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def convert_to_pdf(xlsx_path, pdf_path, sheet_name):
    """(성공 여부, 실패 사유) 를 돌려준다. Excel이 없거나 실패하면 False."""
    command = _build_ps_command(xlsx_path, pdf_path, sheet_name)
    encoded = base64.b64encode(command.encode("utf-16-le")).decode("ascii")
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
             "-EncodedCommand", encoded],
            capture_output=True, timeout=TIMEOUT_SECONDS, creationflags=NO_WINDOW)
    except subprocess.TimeoutExpired:
        note = f"{TIMEOUT_SECONDS}초 안에 응답하지 않았습니다(Excel이 느리게 켜지고 있거나 멈춰 있을 수 있습니다)."
        log_path = _log_failure(xlsx_path, pdf_path, "TIMEOUT", None, None, note)
        detail = note + (f"\n\n자세한 내용: {log_path}" if log_path else "")
        return False, detail
    except OSError as exc:
        log_path = _log_failure(xlsx_path, pdf_path, "OSERROR", None, str(exc))
        detail = f"PowerShell을 실행하지 못했습니다.\n{exc}" + (f"\n\n자세한 내용: {log_path}" if log_path else "")
        return False, detail

    stdout = _decode_console_bytes(result.stdout)
    stderr = _decode_console_bytes(result.stderr)
    if result.returncode != 0 or not os.path.exists(pdf_path):
        log_path = _log_failure(xlsx_path, pdf_path, result.returncode, stdout, stderr)
        # catch 블록이 실패 사유를 표준출력(stdout)에 평문으로 적는다. 표준오류(stderr)는
        # PowerShell이 진행 표시줄 등을 CLIXML로 직렬화해 보내는 자리라 사람이 읽기
        # 어렵다(직접 재현 확인) -- stdout에 내용이 있으면 그쪽을 우선한다.
        detail = (stdout or stderr or "Microsoft Excel이 설치되어 있는지 확인해 주세요.").strip()
        return False, detail[:500] + (f"\n\n자세한 내용: {log_path}" if log_path else "")
    return True, None
