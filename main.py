"""기계 시트 표준 견적 입력 시스템 실행 스크립트.

소스에서 바로 띄울 때:   python main.py
빌드할 때:               pyinstaller Machine_Estimate.spec  (이 파일이 진입점)
"""

from estimate_app.main import main

if __name__ == "__main__":
    main()
