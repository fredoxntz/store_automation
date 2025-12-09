import streamlit as st

from ui.coupang_bulk import render_coupang_bulk
from ui.coupang_cj import render_coupang_cj
from ui.naver_cj import render_naver_cj
from ui.naver_bulk import render_naver_bulk
from ui.settings import render_settings


st.set_page_config(page_title="송장 자동화", page_icon="📦", layout="wide")

STYLE = """
<style>
:root {
    --bg: #eef2f8;
    --text: #1f2d3d;
}
body { background: radial-gradient(circle at 20% 20%, #f7f9ff, var(--bg)); color: var(--text); }
.card { border-radius: 18px; padding: 18px 20px; background: white;
        box-shadow: 0 10px 30px rgba(0,0,0,0.06);
        transition: transform .15s ease, box-shadow .15s ease; }
.card:hover { transform: translateY(-4px); box-shadow: 0 14px 36px rgba(0,0,0,0.12); }
.choice { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px; }

button[kind] {
    background: #f2f4f8;
    border: 1px solid #dfe4ed;
    color: var(--text);
    border-radius: 12px;
    box-shadow: 0 10px 24px rgba(0, 0, 0, 0.06);
    transition: all 0.15s ease;
}
button[kind]:hover {
    background: #ffffff;
    border-color: #cbd4e2;
    transform: translateY(-1px);
    box-shadow: 0 12px 26px rgba(0, 0, 0, 0.08);
}
button:focus { outline: none !important; box-shadow: 0 0 0 3px rgba(66, 99, 235, 0.2); }

button[aria-label="🚚 CJ 발주서 만들기"],
button[aria-label="📑 대량등록 파일 만들기"] {
    max-width: 280px;
    width: 100%;
}

button[aria-label="🟢 네이버"] {
    background: #d8f3dc;
    border-color: #b7e4c7;
    color: #2b7a0b;
    max-width: 240px;
    width: 100%;
}
button[aria-label="🟢 네이버"]:hover {
    background: #e8f7ee;
    border-color: #a3d9b2;
    color: #246908;
}
button[aria-label="🟠 쿠팡"] {
    background: #dbeafe;
    border-color: #b6d4ff;
    color: #1f4b99;
    max-width: 240px;
    width: 100%;
}
button[aria-label="🟠 쿠팡"]:hover {
    background: #eef4ff;
    border-color: #a3c5ff;
    color: #153f85;
}

.settings-btn button {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 8px !important;
    font-size: 24px !important;
    transition: all 0.2s ease !important;
    color: #6b7280 !important;
}
.settings-btn button:hover {
    background: transparent !important;
    transform: rotate(90deg) scale(1.1) !important;
    color: #1f2937 !important;
    box-shadow: none !important;
}
.settings-btn button:active {
    transform: rotate(90deg) scale(0.95) !important;
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

    col1, col2 = st.columns([10, 1])
    with col1:
        st.title("📦 송장 자동화")
    with col2:
        st.write("")
        st.markdown('<div class="settings-btn">', unsafe_allow_html=True)
        if st.button("⚙️", help="설정", key="settings_btn"):
            st.session_state.show_settings = True
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    st.caption("CJ 발주서 · 대량등록 파일 자동 생성")


def render_main():
    if st.session_state.step == "landing":
        section_heading("무엇을 하시겠어요?")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🚚 CJ 발주서 만들기", use_container_width=True, type="secondary"):
                go("channel", job="cj")

        with col2:
            if st.button("📑 대량등록 파일 만들기", use_container_width=True, type="secondary"):
                go("channel", job="bulk")

    elif st.session_state.step == "channel":
        section_heading(
            "채널을 선택하세요",
            f"선택 작업: {'CJ 발주서' if st.session_state.job == 'cj' else '대량등록 파일'}",
        )

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🟢 네이버", use_container_width=True, type="secondary"):
                go("form", channel="naver")

        with col2:
            if st.button("🟠 쿠팡", use_container_width=True, type="secondary"):
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
    render_header()

    if st.session_state.show_settings:
        render_settings()
    else:
        render_main()


if __name__ == "__main__":
    main()
