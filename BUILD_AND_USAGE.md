송장 자동화 실행 파일 빌드 및 배포 가이드
===========================================

이 문서는 macOS/Windows에서 실행 파일을 빌드하고, 다른 PC에서 사용할 때 필요한 주의사항과 사용법을 정리합니다.

준비 사항
---------
- Python 3.11 이상 (64bit) 설치
- git/압축 해제 툴
- (선택) `python -m venv .venv` 로 가상환경 생성 후 활성화
- 의존성 설치: `pip install --upgrade pip` 후 `pip install .` (루트의 `pyproject.toml`을 사용)

macOS 빌드
-----------
1) 터미널에서 프로젝트 루트로 이동 후 가상환경을 활성화합니다.  
2) `pip install .` 로 의존성을 설치합니다.  
3) 빌드 실행: `python build_mac.py`  
4) 결과물: `dist/송장자동화.app/`  
5) 배포: `dist/송장자동화.app` 전체를 압축(zip)해서 전달합니다.  
   - Gatekeeper 경고 시: 우클릭 → "열기" 또는 시스템 설정 > 개인정보 보호 및 보안 > "어쨌든 열기"로 한 번만 허용합니다.

Windows 빌드
-------------
1) PowerShell/cmd에서 프로젝트 루트로 이동 후 가상환경을 활성화합니다.  
2) `pip install .` 로 의존성을 설치합니다.  
3) 빌드 실행:
   ```powershell
   pyinstaller --noconfirm --clean --windowed --onedir `
     --name "송장자동화" `
     --add-data "app.py;." `
     --add-data "output;output" `
     --hidden-import streamlit `
     --hidden-import streamlit.web `
     --hidden-import streamlit.web.cli `
     --hidden-import pandas `
     --hidden-import openpyxl `
     --collect-all streamlit `
     --collect-all altair `
     run_streamlit.py
   ```
4) 결과물: `dist/송장자동화/송장자동화.exe` (폴더 전체 필요)  
5) 배포: `dist/송장자동화` 폴더 전체를 압축(zip)해서 전달합니다. SmartScreen 경고 시 "추가 정보" → "실행"으로 한 번만 허용하면 됩니다.

배포 시 체크리스트
-------------------
- `config.json`에 올바른 OpenAI API 키가 있는지 확인하고, 공개 공유 전에 키를 제거하거나 새 키로 교체합니다.  
- `output` 폴더에 필요한 리소스가 있다면 빌드 전에 최신 상태로 채워두세요.  
- 빌드된 결과물은 폴더 단위로 전달해야 합니다(단일 exe만 전달하지 말 것).  
- 사내 네트워크 보안 정책으로 8501 포트가 차단되지 않았는지 확인합니다.

다른 컴퓨터에서 사용법
----------------------
- macOS: 받은 `송장자동화.app`를 압축 해제 후 더블클릭 실행. 보안 경고는 한 번만 허용.  
- Windows: `송장자동화` 폴더를 압축 해제 후 `송장자동화.exe` 실행. 관리자 권한은 필요하지 않습니다.  
- 실행 후 자동으로 로컬 웹 서버가 올라가며 브라우저가 열립니다. 기본 주소는 `http://localhost:8501`이며, 같은 Wi-Fi의 다른 기기는 `http://<해당 PC IP>:8501`로 접속할 수 있습니다.  
- 프로그램을 종료할 때는 런처 창의 “프로그램 종료” 버튼을 눌러야 백그라운드 서버가 함께 종료됩니다.

문제 해결
---------
- 포트 충돌: 8501 포트를 다른 앱이 사용 중이면 해당 앱을 종료하거나 `run_streamlit.py`의 포트를 변경 후 재빌드하세요.  
- 폰트/렌더링 깨짐: 한글 경로를 포함한 폴더에서 실행 시 일부 보안 정책에 걸릴 수 있으니 영문 경로로 이동 후 실행해 보세요.  
- 빌드 실패: `build`/`dist` 폴더를 삭제한 뒤(스크립트가 자동 삭제) 다시 실행하고, `pip show pyinstaller`로 6.17+ 버전인지 확인합니다.
