#!/usr/bin/env python3
"""
ngrok을 사용해서 인터넷 어디서나 접속 가능하게 만들기
주의: 공개 URL이 생성되므로 보안에 유의하세요!
"""
import subprocess
import threading
import time
import webbrowser

def start_streamlit():
    """Streamlit 서버 시작"""
    subprocess.run([
        "streamlit",
        "run",
        "app.py",
        "--server.port=8501",
        "--browser.gatherUsageStats=false",
        "--server.headless=true",
    ])

def start_ngrok():
    """ngrok 터널 시작"""
    time.sleep(3)  # Streamlit 서버가 시작될 때까지 대기

    print("\n" + "=" * 60)
    print("🌍 ngrok 터널 생성 중...")
    print("=" * 60)
    print("\n⚠️  주의사항:")
    print("   - 생성된 URL은 누구나 접속 가능합니다")
    print("   - 민감한 데이터는 되도록 업로드하지 마세요")
    print("   - 무료 버전은 2시간마다 URL이 변경됩니다")
    print("\n종료하려면 Ctrl+C를 누르세요\n")

    subprocess.run(["ngrok", "http", "8501"])

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 송장 자동화 - 외부 접속 모드")
    print("=" * 60)
    print("\n📦 ngrok이 설치되어 있어야 합니다.")
    print("   설치: brew install ngrok")
    print("   (또는 https://ngrok.com 에서 다운로드)\n")

    # Streamlit을 백그라운드에서 실행
    streamlit_thread = threading.Thread(target=start_streamlit, daemon=True)
    streamlit_thread.start()

    # ngrok 실행
    try:
        start_ngrok()
    except KeyboardInterrupt:
        print("\n\n종료합니다...")
    except FileNotFoundError:
        print("\n❌ ngrok이 설치되어 있지 않습니다.")
        print("   설치 명령: brew install ngrok")
