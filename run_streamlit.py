#!/usr/bin/env python3
"""
송장 자동화 앱 런처
이 스크립트는 Streamlit 앱을 실행하고 GUI를 표시합니다.
"""
import sys
import os
import webbrowser
import time
import subprocess
import threading
import tkinter as tk
from tkinter import ttk
from pathlib import Path

# PyInstaller로 패키징된 경우 리소스 경로 설정
if getattr(sys, 'frozen', False):
    # PyInstaller로 실행되는 경우
    bundle_dir = Path(sys._MEIPASS)
else:
    # 일반 Python으로 실행되는 경우
    bundle_dir = Path(__file__).parent

# 작업 디렉토리 변경
os.chdir(bundle_dir)

# PyInstaller로 빌드된 실행 파일이 streamlit 서버를 재귀적으로 계속 띄우는 것을 막기 위한 처리.
# 자식 프로세스는 이 분기에서 streamlit CLI만 실행하고 종료한다.
if os.environ.get("RUN_AS_STREAMLIT") == "1":
    from streamlit.web import cli as stcli

    sys.argv = [
        "streamlit",
        "run",
        str(bundle_dir / "app.py"),
        "--server.headless=true",
        "--browser.gatherUsageStats=false",
        "--global.developmentMode=false",
        "--server.port=8501",
    ]
    stcli.main()
    sys.exit(0)

# 전역 변수로 스트림릿 프로세스 관리
streamlit_process = None
APP_URL = "http://localhost:8501"

def start_streamlit():
    """Streamlit 서버를 백그라운드로 시작"""
    global streamlit_process

    # PyInstaller 빌드 시에는 자기 자신을 다시 실행하면 무한 생성되므로
    # 자식 프로세스에 플래그를 전달해 Streamlit만 실행하도록 함.
    if getattr(sys, "frozen", False):
        env = os.environ.copy()
        env["RUN_AS_STREAMLIT"] = "1"
        streamlit_process = subprocess.Popen(
            [sys.executable],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )
    else:
        streamlit_process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                str(bundle_dir / "app.py"),
                "--server.headless=true",
                "--browser.gatherUsageStats=false",
                "--global.developmentMode=false",
                "--server.port=8501",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )

def open_browser():
    """브라우저에서 앱 열기"""
    webbrowser.open(APP_URL)

def quit_app(root):
    """앱 종료"""
    global streamlit_process

    # Streamlit 프로세스 종료
    if streamlit_process:
        streamlit_process.terminate()
        try:
            streamlit_process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            streamlit_process.kill()

    # GUI 종료
    root.destroy()
    sys.exit(0)

def create_gui():
    """GUI 생성"""
    root = tk.Tk()
    root.title("송장 자동화")
    root.geometry("500x250")
    root.resizable(False, False)

    # 창 닫기 이벤트 처리
    root.protocol("WM_DELETE_WINDOW", lambda: quit_app(root))

    # 메인 프레임
    main_frame = ttk.Frame(root, padding="20")
    main_frame.pack(fill=tk.BOTH, expand=True)

    # 제목
    title_label = ttk.Label(
        main_frame,
        text="송장 자동화 프로그램",
        font=("Helvetica", 18, "bold")
    )
    title_label.pack(pady=(0, 20))

    # 안내 메시지
    info_label = ttk.Label(
        main_frame,
        text="아래 버튼을 클릭해서 앱을 사용하세요",
        font=("Helvetica", 12)
    )
    info_label.pack(pady=(0, 10))

    # URL 표시
    url_frame = ttk.Frame(main_frame)
    url_frame.pack(pady=(0, 20))

    url_label = ttk.Label(
        url_frame,
        text=f"접속 주소: {APP_URL}",
        font=("Courier", 11),
        foreground="blue"
    )
    url_label.pack()

    # 버튼 프레임
    button_frame = ttk.Frame(main_frame)
    button_frame.pack(pady=10)

    # 브라우저 열기 버튼
    open_button = ttk.Button(
        button_frame,
        text="🌐 브라우저에서 열기",
        command=open_browser,
        width=25
    )
    open_button.pack(pady=5)

    # 종료 버튼
    quit_button = ttk.Button(
        button_frame,
        text="❌ 프로그램 종료",
        command=lambda: quit_app(root),
        width=25
    )
    quit_button.pack(pady=5)

    # 상태 표시
    status_label = ttk.Label(
        main_frame,
        text="서버 시작 중...",
        font=("Helvetica", 10),
        foreground="gray"
    )
    status_label.pack(pady=(20, 0))

    # 서버 시작 확인 후 상태 업데이트
    def check_server():
        time.sleep(2)
        status_label.config(text="✓ 서버 실행 중", foreground="green")

    threading.Thread(target=check_server, daemon=True).start()

    return root

if __name__ == '__main__':
    # Streamlit 서버 시작
    start_streamlit()

    # 잠시 대기 (서버 시작)
    time.sleep(1)

    # GUI 생성 및 실행
    root = create_gui()
    root.mainloop()
