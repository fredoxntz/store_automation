# 🖥️ 서버 배포 가이드

내 컴퓨터를 서버로 사용해서 다른 사람들이 접속할 수 있게 하는 방법입니다.

## 🔒 방법 1: 같은 WiFi 네트워크 (권장 - 가장 안전)

같은 사무실/집 WiFi를 쓰는 사람만 접속 가능합니다.

### 실행 방법

```bash
# 방법 A: 간단한 스크립트 실행
python start_server.py

# 방법 B: GUI 앱 실행 (수정된 버전)
python run_streamlit.py
```

### 접속 방법

1. **내 컴퓨터에서**: `http://localhost:8501`
2. **다른 기기에서**: `http://192.168.1.82:8501` (IP는 자동으로 표시됨)

### 보안
- ✅ 데이터가 내부 네트워크에서만 전송됨
- ✅ 외부 인터넷에서는 접속 불가
- ✅ 회사/집 WiFi 사용자만 접속 가능

### Mac 방화벽 설정

차단되면 다음 설정:
1. **시스템 설정** → **네트워크** → **방화벽**
2. Python 또는 Streamlit 앱 **허용**

---

## 🌍 방법 2: ngrok - 인터넷 어디서나 접속

**주의: 보안이 중요하면 사용하지 마세요!**

### 설치

```bash
brew install ngrok
```

### 실행

```bash
python start_ngrok.py
```

실행하면 다음과 같은 URL이 생성됩니다:
```
https://abc123.ngrok.io
```

### 접속
- 위 URL을 다른 사람에게 공유
- 인터넷만 되면 전 세계 어디서나 접속 가능

### 보안 주의사항
- ⚠️ 생성된 URL은 **누구나** 접속 가능
- ⚠️ 고객 데이터가 ngrok 서버를 거침
- ⚠️ 무료 버전은 2시간마다 URL 변경
- 🔒 비밀번호 설정 권장 (아래 참고)

### ngrok 비밀번호 설정

더 안전하게 사용하려면:

```bash
ngrok http 8501 --basic-auth="username:password"
```

---

## 🏢 방법 3: 회사 서버에 설치 (가장 전문적)

Linux 서버가 있다면:

### 1. 서버에 코드 업로드

```bash
scp -r . user@server:/path/to/app
```

### 2. 서버에서 실행

```bash
ssh user@server
cd /path/to/app
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py --server.port=8501 --server.address=0.0.0.0
```

### 3. 백그라운드 실행 (재부팅 후에도 자동 실행)

`systemd` 서비스 설정:

```ini
# /etc/systemd/system/songja.service
[Unit]
Description=송장 자동화 서비스
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/app
Environment="PATH=/path/to/app/venv/bin"
ExecStart=/path/to/app/venv/bin/streamlit run app.py --server.port=8501 --server.address=0.0.0.0
Restart=always

[Install]
WantedBy=multi-user.target
```

실행:
```bash
sudo systemctl enable songja
sudo systemctl start songja
```

### 4. 도메인 연결 (옵션)

nginx 리버스 프록시 설정으로 `https://songja.company.com` 같은 도메인 사용 가능

---

## 📊 방법 비교

| 방법 | 보안 | 편의성 | 비용 | 추천 |
|------|------|--------|------|------|
| **같은 WiFi** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 무료 | ✅ 권장 |
| **ngrok** | ⭐⭐ | ⭐⭐⭐⭐⭐ | 무료~유료 | ⚠️ 주의 |
| **회사 서버** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | 서버 비용 | ✅ 권장 |

---

## 🔐 보안 체크리스트

- [ ] 같은 WiFi 방식 사용 중
- [ ] 방화벽 설정 완료
- [ ] 고객 데이터는 로컬에서만 처리됨
- [ ] ngrok 사용 시 비밀번호 설정
- [ ] 사용하지 않을 때는 서버 종료

---

## 🆘 문제 해결

### "This site can't be reached" 오류
- 방화벽 확인
- 서버가 실행 중인지 확인 (`ps aux | grep streamlit`)
- IP 주소가 맞는지 확인

### 느린 속도
- 같은 WiFi 방식: 라우터 재시작
- ngrok: 무료 버전 속도 제한

### 포트 충돌
```bash
# 다른 포트 사용
streamlit run app.py --server.port=8502
```
