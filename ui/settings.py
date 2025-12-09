import streamlit as st

from utils.ai_helper import test_openai_api
from utils.config import get_openai_api_key, save_openai_api_key


def render_settings():
    """Render settings panel for API key and chat test."""
    st.markdown("### ⚙️ 설정")
    st.caption("OpenAI API 키를 설정하여 챗봇 기능을 사용할 수 있습니다.")

    st.markdown("---")

    current_api_key = get_openai_api_key()

    if current_api_key:
        masked_key = (
            current_api_key[:8] + "*" * (len(current_api_key) - 12) + current_api_key[-4:]
            if len(current_api_key) > 12
            else "****"
        )
        st.info(f"현재 저장된 API 키: `{masked_key}`")
    else:
        st.warning("저장된 API 키가 없습니다.")

    st.markdown("#### OpenAI API 키 입력")

    with st.form("api_key_form"):
        new_api_key = st.text_input(
            "API 키",
            value="",
            type="password",
            placeholder="sk-...",
            help="OpenAI API 키를 입력하세요. API 키는 암호화되어 로컬에 저장됩니다.",
        )

        col1, col2 = st.columns([1, 4])
        with col1:
            submit = st.form_submit_button("저장", type="primary", use_container_width=True)
        with col2:
            clear = st.form_submit_button("삭제", use_container_width=True)

        if submit:
            if new_api_key.strip():
                if save_openai_api_key(new_api_key.strip()):
                    st.success("✅ API 키가 성공적으로 저장되었습니다!")
                    st.rerun()
            else:
                st.error("API 키를 입력해주세요.")

        if clear:
            if save_openai_api_key(""):
                st.success("✅ API 키가 삭제되었습니다.")
                st.rerun()

    st.markdown("---")
    st.markdown("#### 🤖 API 연동 테스트")

    if current_api_key:
        st.caption("저장된 API 키로 간단한 채팅을 테스트해보세요.")

        if st.session_state.chat_history:
            st.markdown("**채팅 기록:**")
            for chat in st.session_state.chat_history:
                if chat["role"] == "user":
                    st.markdown(f"**👤 You:** {chat['content']}")
                else:
                    st.markdown(f"**🤖 AI:** {chat['content']}")
            st.markdown("---")

        with st.form(key="chat_form", clear_on_submit=True):
            col1, col2 = st.columns([5, 1])
            with col1:
                user_input = st.text_input("메시지", placeholder="메시지를 입력하세요...", label_visibility="collapsed")
            with col2:
                submit = st.form_submit_button("전송", use_container_width=True, type="primary")

            if submit and user_input.strip():
                st.session_state.chat_history.append({"role": "user", "content": user_input.strip()})

                with st.spinner("응답 생성 중..."):
                    result = test_openai_api(current_api_key, user_input.strip())

                if result["success"]:
                    st.session_state.chat_history.append({"role": "assistant", "content": result["message"]})
                else:
                    st.session_state.chat_history.append({"role": "assistant", "content": f"❌ {result['message']}"})

                st.rerun()

        if st.session_state.chat_history:
            if st.button("🗑️ 채팅 기록 지우기", use_container_width=False):
                st.session_state.chat_history = []
                st.rerun()
    else:
        st.info("API 키를 먼저 저장해주세요.")

    st.markdown("---")
    st.markdown("#### API 키 발급 안내")
    st.markdown(
        """
    1. [OpenAI 플랫폼](https://platform.openai.com/api-keys)에 로그인
    2. API Keys 메뉴에서 'Create new secret key' 클릭
    3. 생성된 키를 복사하여 위에 입력
    """
    )

    st.markdown("---")
    if st.button("← 메인으로 돌아가기", use_container_width=False):
        st.session_state.show_settings = False
        st.rerun()
