import bcrypt


# TODO: 아래 해시값을 실제 비밀번호 해시로 교체하세요
# Python 코드로 생성한 bcrypt 해시값을 여기에 붙여넣으세요
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD_HASH = "$2b$10$emgXmGfG7tX7uZPGyn.2/O4ynLI9qd2w1O8XY4Aj9d8WiZjrpf5vS"


def verify_password(username: str, password: str) -> bool:
    """
    사용자 인증을 검증합니다.

    Args:
        username: 사용자 아이디
        password: 평문 비밀번호

    Returns:
        인증 성공 여부
    """
    if username != ADMIN_USERNAME:
        return False

    try:
        password_bytes = password.encode('utf-8')
        hash_bytes = ADMIN_PASSWORD_HASH.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hash_bytes)
    except Exception:
        return False


def is_authenticated() -> bool:
    """
    현재 세션이 인증되었는지 확인합니다.

    Returns:
        인증 여부
    """
    import streamlit as st
    return st.session_state.get("authenticated", False)


def login(username: str, password: str) -> bool:
    """
    로그인을 시도합니다.

    Args:
        username: 사용자 아이디
        password: 평문 비밀번호

    Returns:
        로그인 성공 여부
    """
    import streamlit as st

    if verify_password(username, password):
        st.session_state.authenticated = True
        st.session_state.username = username
        return True
    return False


def logout():
    """로그아웃을 수행합니다."""
    import streamlit as st

    st.session_state.authenticated = False
    if "username" in st.session_state:
        del st.session_state.username
