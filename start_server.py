#!/usr/bin/env python3
"""
네트워크 서버 모드로 실행
같은 WiFi를 쓰는 다른 기기에서도 접속 가능합니다.
"""
import subprocess
import socket

def get_local_ip():
    """로컬 IP 주소 확인"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "IP를 가져올 수 없음"

if __name__ == "__main__":
    local_ip = get_local_ip()

    print("=" * 60)
    print("🚀 송장 자동화 서버 시작")
    print("=" * 60)
    print(f"\n📍 접속 주소:")
    print(f"   - 이 컴퓨터:      http://localhost:8501")
    print(f"   - 다른 기기:      http://{local_ip}:8501")
    print(f"\n💡 같은 WiFi를 사용하는 기기에서 위 주소로 접속하세요")
    print(f"\n⚠️  Mac 방화벽 차단 시:")
    print(f"   시스템 설정 → 네트워크 → 방화벽 → Python 허용")
    print(f"\n종료하려면 Ctrl+C를 누르세요\n")
    print("=" * 60)

    subprocess.run([
        "streamlit",
        "run",
        "app.py",
        "--server.address=0.0.0.0",
        "--server.port=8501",
        "--browser.gatherUsageStats=false",
    ])
