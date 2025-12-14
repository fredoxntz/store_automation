import streamlit as st
from utils.auth import login


LOGIN_STYLE = """
<style>
/* Streamlit 기본 여백 제거 */
[data-testid="stAppViewContainer"] > .main {
    padding-top: 2rem;
}

.login-title {
    font-size: 36px;
    font-weight: 800;
    color: #1e293b;
    text-align: center;
    margin-bottom: 8px;
    letter-spacing: -0.03em;
}

.login-version {
    font-size: 14px;
    color: #94a3b8;
    text-align: center;
    margin-bottom: 48px;
    font-weight: 500;
}

.login-icon {
    font-size: 64px;
    text-align: center;
    margin-bottom: 24px;
}

/* 로그인 폼 스타일 */
.login-form {
    max-width: 400px;
    margin: 0 auto;
}

.login-form input {
    width: 100%;
    padding: 14px 18px;
    border: 2px solid #e2e8f0;
    border-radius: 14px;
    font-size: 15px;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    background: white;
    color: #1e293b;
}

.login-form input:focus {
    outline: none;
    border-color: #a8dadc;
    box-shadow: 0 0 0 4px rgba(168, 218, 220, 0.15);
}

.login-form label {
    font-size: 14px;
    font-weight: 600;
    color: #475569;
}

/* 로그인 버튼 */
.stButton button[kind="primary"] {
    width: 100%;
    padding: 16px;
    background: linear-gradient(135deg, #a8dadc 0%, #89cff0 100%);
    color: #1e293b;
    font-size: 16px;
    font-weight: 700;
    border: none;
    border-radius: 14px;
    box-shadow: 0 4px 20px rgba(168, 218, 220, 0.3);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.stButton button[kind="primary"]:hover {
    background: linear-gradient(135deg, #89cff0 0%, #6eb5d0 100%);
    transform: translateY(-2px);
    box-shadow: 0 6px 30px rgba(168, 218, 220, 0.4);
}

/* 에러 메시지 */
.element-container div[data-testid="stAlert"] {
    border-radius: 12px;
}
</style>
"""


def render_login():
    """간결한 로그인 페이지를 렌더링합니다."""
    st.markdown(LOGIN_STYLE, unsafe_allow_html=True)

    # 로고/아이콘
    st.markdown('<div class="login-icon">📦</div>', unsafe_allow_html=True)

    # 제목
    st.markdown('<div class="login-title">송장 자동화 프로그램 v1.0</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-version">CJ 발주서 · 대량등록 파일 자동 생성</div>', unsafe_allow_html=True)

    # 중앙 정렬 폼
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown('<div class="login-form">', unsafe_allow_html=True)

        with st.form("login_form", clear_on_submit=False):
            username = st.text_input(
                "아이디",
                placeholder="아이디를 입력하세요",
                key="login_username",
            )

            password = st.text_input(
                "비밀번호",
                type="password",
                placeholder="비밀번호를 입력하세요",
                key="login_password",
            )

            st.markdown("<br>", unsafe_allow_html=True)

            submitted = st.form_submit_button("로그인", type="primary", use_container_width=True)

            if submitted:
                if not username or not password:
                    st.error("아이디와 비밀번호를 입력해주세요.")
                elif login(username, password):
                    st.success("로그인 성공!")
                    st.rerun()
                else:
                    st.error("아이디 또는 비밀번호가 올바르지 않습니다.")

        st.markdown('</div>', unsafe_allow_html=True)
