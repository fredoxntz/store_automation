import streamlit as st

from ui.coupang_bulk import render_coupang_bulk
from ui.coupang_cj import render_coupang_cj
from ui.naver_cj import render_naver_cj
from ui.naver_bulk import render_naver_bulk
from ui.settings import render_settings
from ui.login import render_login
from utils.auth import is_authenticated, logout


st.set_page_config(page_title="송장 자동화", page_icon="📦", layout="wide")

STYLE = """
<style>
:root {
    --bg: #ffffff;
    --text: #1e293b;
    --primary: #a8dadc;
    --primary-dark: #457b9d;
    --secondary: #b8d4e0;
}

/* Streamlit 기본 UI 제거/초기화 */
[data-testid="stToolbar"],
[data-testid="stDecoration"],
header,
footer,
#MainMenu {
    display: none;
}
[data-testid="stSidebar"] {
    background: transparent;
    box-shadow: none;
}
[data-testid="stSidebarNav"] {
    padding: 0;
}
[data-testid="stHeader"] {
    background: transparent;
    box-shadow: none;
}
[data-testid="stAppViewContainer"],
.stApp,
.main {
    padding: 0;
    background: var(--bg);
}
.block-container {
    padding: 0 32px 48px;
    background: var(--bg);
    max-width: 1200px;
}

/* 폼 요소 기본 스타일 재정의 */
input, textarea, select {
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    box-shadow: none;
    background: #fff;
    color: var(--text);
}
label, .stCheckbox, .stRadio {
    color: var(--text);
}
/* 버튼 기본 스타일 재정의 */
button, [role="button"] {
    border-radius: 12px;
    box-shadow: none;
}

/* 다크모드 강제 비활성화 */
[data-testid="stAppViewContainer"],
.stApp,
.main,
.block-container,
body {
    background-color: #f8fafc;
    background: #f8fafc;
    color: #1e293b;
}

[data-testid="stHeader"] {
    background-color: transparent;
}

/* 모든 텍스트 요소 색상 고정 */
p, span, div, label {
    color: #1e293b;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

.card {
    border-radius: 20px;
    padding: 24px;
    background: white;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.card:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 30px rgba(0, 0, 0, 0.08);
}

button[kind] {
    background: white;
    border: 2px solid #e2e8f0;
    color: var(--text);
    border-radius: 16px;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.04);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    font-weight: 600;
    letter-spacing: -0.02em;
}
button[kind]:hover {
    background: #f8fafc;
    border-color: var(--primary);
    transform: translateY(-2px);
    box-shadow: 0 4px 20px rgba(168, 218, 220, 0.2);
}
button:focus {
    outline: none;
    box-shadow: 0 0 0 4px rgba(168, 218, 220, 0.3);
}

[data-testid="stHorizontalBlock"]:has(button[aria-label="🚚 CJ 발주서 만들기"]),
[data-testid="stHorizontalBlock"]:has(button[aria-label="📑 대량등록 파일 만들기"]),
[data-testid="stHorizontalBlock"]:has(button[aria-label="🟢 네이버"]),
[data-testid="stHorizontalBlock"]:has(button[aria-label="🟠 쿠팡"]) {
    display: flex;
    gap: 20px; /* 버튼 간격 고정 */
}
[data-testid="stHorizontalBlock"]:has(button[aria-label="🚚 CJ 발주서 만들기"]) [data-testid="column"],
[data-testid="stHorizontalBlock"]:has(button[aria-label="📑 대량등록 파일 만들기"]) [data-testid="column"],
[data-testid="stHorizontalBlock"]:has(button[aria-label="🟢 네이버"]) [data-testid="column"],
[data-testid="stHorizontalBlock"]:has(button[aria-label="🟠 쿠팡"]) [data-testid="column"] {
    width: auto; /* columns shrink to button size */
}
[data-testid="stHorizontalBlock"]:has(button[aria-label="🚚 CJ 발주서 만들기"]) > [data-testid="column"] > div,
[data-testid="stHorizontalBlock"]:has(button[aria-label="📑 대량등록 파일 만들기"]) > [data-testid="column"] > div,
[data-testid="stHorizontalBlock"]:has(button[aria-label="🟢 네이버"]) > [data-testid="column"] > div,
[data-testid="stHorizontalBlock"]:has(button[aria-label="🟠 쿠팡"]) > [data-testid="column"] > div {
    align-items: flex-start;
}

button[aria-label="🚚 CJ 발주서 만들기"],
button[aria-label="📑 대량등록 파일 만들기"] {
    width: 220px;
    min-width: px;
    max-width: 220px;
    margin: 0;
    display: block;
    padding: 16px 28px;
    background: linear-gradient(135deg, #a8dadc 0%, #89cff0 100%);
    color: #1e293b;
    font-size: 15px;
    border: none;
    font-weight: 700;
}
button[aria-label="🚚 CJ 발주서 만들기"]:hover,
button[aria-label="📑 대량등록 파일 만들기"]:hover {
    background: linear-gradient(135deg, #89cff0 0%, #6eb5d0 100%);
    transform: translateY(-3px) scale(1.02);
    box-shadow: 0 8px 30px rgba(168, 218, 220, 0.4);
}

button[aria-label="🟢 네이버"],
button[aria-label="🟠 쿠팡"] {
    margin: 0;
    display: block;
    padding: 16px 28px;
    font-size: 15px;
    font-weight: 700;
    border: none;
}

button[aria-label="🟢 네이버"] {
    background: linear-gradient(135deg, #c9e4ca 0%, #a8d5ba 100%);
    color: #1e5128;
}
button[aria-label="🟢 네이버"]:hover {
    background: linear-gradient(135deg, #a8d5ba 0%, #88c9a1 100%);
    transform: translateY(-3px) scale(1.02);
    box-shadow: 0 8px 30px rgba(168, 213, 186, 0.4);
}

button[aria-label="🟠 쿠팡"] {
    background: linear-gradient(135deg, #ffd7ba 0%, #ffb997 100%);
    color: #7c2d12;
}
button[aria-label="🟠 쿠팡"]:hover {
    background: linear-gradient(135deg, #ffb997 0%, #ff9d6e 100%);
    transform: translateY(-3px) scale(1.02);
    box-shadow: 0 8px 30px rgba(255, 185, 151, 0.4);
}

.settings-btn button {
    background: #f1f5f9;
    border: none;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
    padding: 10px;
    font-size: 24px;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    color: #64748b;
    border-radius: 12px;
}
.settings-btn button:hover {
    background: #e2e8f0;
    transform: rotate(90deg) scale(1.15);
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
    color: var(--primary-dark);
}
.settings-btn button:active {
    transform: rotate(90deg) scale(0.95);
}

/* 타이틀 스타일 */
h1 {
    color: #1e293b;
    font-weight: 800;
    letter-spacing: -0.03em;
}

/* 서브타이틀 스타일 */
.stCaption, [data-testid="stCaption"] {
    color: #64748b;
}

h2, h3, h4, h5, h6 {
    color: #1e293b;
    font-weight: 700;
}

/* Streamlit 기본 스타일 오버라이드 */
[data-testid="stMarkdownContainer"] {
    color: #1e293b;
}
</style>
"""


def init_session_state():
    defaults = {
        "step": "landing",
        "job": None,
        "channel": None,
        "coupang_cj_result": None,
        "coupang_bulk_result": None,
        "naver_bulk_result": None,
        "last_uploaded_name": None,
        "last_bulk_names": (None, None),
        "last_naver_bulk_names": (None, None),
        "show_settings": False,
        "chat_history": [],
        "naver_cj_result": None,
        "last_naver_uploaded_name": None,
        "naver_intermediate_table": None,
        "naver_raw_data": None,
        "naver_workflow_step": "upload",
        "authenticated": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset():
    st.session_state.step = "landing"
    st.session_state.job = None
    st.session_state.channel = None
    st.rerun()


def section_heading(title: str, subtitle: str | None = None):
    st.subheader(title)
    if subtitle:
        st.caption(subtitle)


def go(step: str, job: str | None = None, channel: str | None = None):
    if job is not None:
        st.session_state.job = job
    if channel is not None:
        st.session_state.channel = channel
    st.session_state.step = step
    st.rerun()


def render_header():
    st.markdown(STYLE, unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns([8, 1, 1, 1])
    with col1:
        st.title("📦 송장 자동화")
    with col2:
        st.write("")
        st.markdown('<div class="settings-btn">', unsafe_allow_html=True)
        if st.button("🏠", help="홈으로", key="home_btn"):
            st.session_state.show_settings = False
            reset()
        st.markdown("</div>", unsafe_allow_html=True)
    with col3:
        st.write("")
        st.markdown('<div class="settings-btn">', unsafe_allow_html=True)
        if st.button("⚙️", help="설정", key="settings_btn"):
            st.session_state.show_settings = True
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
    with col4:
        st.write("")
        st.markdown('<div class="settings-btn">', unsafe_allow_html=True)
        if st.button("🚪", help="로그아웃", key="logout_btn"):
            logout()
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    st.caption("CJ 발주서 · 대량등록 파일 자동 생성")


def render_main():
    if st.session_state.step == "landing":
        section_heading("무엇을 하시겠어요?")

        col1, col2 = st.columns(2, gap="small")
        with col1:
            if st.button("🚚 CJ 발주서 만들기", type="secondary", key="cj_btn"):
                go("channel", job="cj")
        with col2:
            if st.button("📑 대량등록 파일 만들기", type="secondary", key="bulk_btn"):
                go("channel", job="bulk")

    elif st.session_state.step == "channel":
        section_heading(
            "채널을 선택하세요",
            f"선택 작업: {'CJ 발주서' if st.session_state.job == 'cj' else '대량등록 파일'}",
        )

        col1, col2 = st.columns(2, gap="small")
        with col1:
            if st.button("🟢 네이버", type="secondary", key="naver_btn"):
                go("form", channel="naver")
        with col2:
            if st.button("🟠 쿠팡", type="secondary", key="coupang_btn"):
                go("form", channel="coupang")

        st.button("← 처음으로", on_click=reset)

    elif st.session_state.step == "form":
        section_heading(
            f"{'CJ 발주서' if st.session_state.job == 'cj' else '대량등록 파일'} · "
            f"{st.session_state.channel.upper()}",
            None,
        )

        if st.session_state.job == "cj" and st.session_state.channel == "coupang":
            render_coupang_cj()
        elif st.session_state.job == "cj" and st.session_state.channel == "naver":
            render_naver_cj()
        elif st.session_state.job == "bulk" and st.session_state.channel == "coupang":
            render_coupang_bulk()
        elif st.session_state.job == "bulk" and st.session_state.channel == "naver":
            render_naver_bulk()
        else:
            st.info("이 채널/작업 조합에 대한 폼이 아직 준비되지 않았습니다.")

        st.button("← 채널 선택으로", on_click=lambda: st.session_state.update({"step": "channel"}))


def main():
    init_session_state()

    # 인증 체크
    if not is_authenticated():
        render_login()
        return

    render_header()

    if st.session_state.show_settings:
        render_settings()
    else:
        render_main()


if __name__ == "__main__":
    main()
