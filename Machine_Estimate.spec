# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 빌드 설정.

v0.0.5부터 단일 exe(onefile)가 아니라 폴더 배포(onedir)로 만든다.
onefile은 실행할 때마다 30MB를 %TEMP%에 통째로 풀고 지우기 때문에 시작이 느렸다.
onedir은 푸는 과정이 없어 바로 뜨고, 배포 용량은 설치 파일의 LZMA 압축이 대신 줄여 준다.

EXCLUDES: 아래 두 덩어리가 용량 대부분을 차지하고 있었다.
  - numpy(모듈 137개) / PIL(76개): openpyxl이 차트·이미지용으로 선택 참조한다.
    이 프로그램은 둘 다 쓰지 않으며, 없어도 읽기/쓰기/서식복사/수식이 정상 동작함을 확인했다.
  - _ssl / _hashlib: OpenSSL 백엔드(libcrypto 6MB + libssl 1.3MB)를 끌고 온다.
    이 프로그램은 네트워크를 쓰지 않고, openpyxl이 필요로 하는 hashlib은
    OpenSSL 없이 파이썬 내장 해시 구현으로 그대로 동작함을 확인했다.
제외 후 실제 동작을 검증한 항목만 목록에 넣는다. 확인 없이 늘리지 말 것.

주의: 나중에 이 프로그램에 인터넷 통신 기능(예: 서버에서 새 버전 내려받기)을 붙이면
_ssl / ssl / _hashlib 제외를 반드시 되돌려야 한다. 안 그러면 통신할 때만 오류가 난다.
"""

EXCLUDES = [
    "numpy", "PIL", "Pillow", "pandas", "matplotlib", "scipy",
    "setuptools", "pip", "pkg_resources",
    "unittest", "doctest", "pydoc", "pydoc_data", "lib2to3",
    "test", "tkinter.test", "idlelib",
    "_ssl", "ssl", "_hashlib",
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('견적_산정\\양식\\견적용.xlsx', '.'),
        ('estimate_app\\assets', 'assets'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDES,
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,   # onedir의 핵심. 빼면 exe가 다시 뚱뚱해진다.
    name='Estimate',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,               # UPX는 매 실행마다 풀어야 해서 시작만 느려진다.
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='estimate_app\\assets\\estimate.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='Estimate',
)
