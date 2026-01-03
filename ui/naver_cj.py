import pandas as pd
import streamlit as st

from utils.config import get_openai_api_key
from utils.coupang_processor import get_sender_defaults
from utils.naver_processor import (
    create_naver_intermediate_table,
    generate_cj_orders_by_date,
    normalize_dates_batch,
)
from utils.excel_utils import read_excel_with_password, render_password_input


def render_naver_cj():
    """네이버 CJ 발주서 생성 워크플로우 (중간 테이블 포함)"""
    api_key = get_openai_api_key()
    if not api_key:
        st.warning("⚠️ OpenAI API 키가 필요합니다. 설정 페이지에서 API 키를 등록해주세요.")
        return

    steps = ["1️⃣ 파일 업로드", "2️⃣ 데이터 검수", "3️⃣ CJ 발주서 생성"]
    current_step = st.session_state.naver_workflow_step

    if current_step == "upload":
        step_idx = 0
    elif current_step == "review":
        step_idx = 1
    else:
        step_idx = 2

    st.markdown(f"**진행 단계:** {' → '.join([f'**{s}**' if i == step_idx else s for i, s in enumerate(steps)])}")
    st.markdown("---")

    if current_step == "upload":
        st.markdown("### 1️⃣ 네이버 로우데이터 업로드")
        st.caption("네이버 엑셀 파일은 첫 행에 안내문이 있으므로 자동으로 처리됩니다.")

        uploaded = st.file_uploader(
            "네이버 로우데이터 엑셀 파일 (.xlsx)",
            type=["xlsx"],
            accept_multiple_files=False,
            key="naver_cj_uploader",
        )

        password = None
        if uploaded:
            password = render_password_input("naver_cj", "파일 비밀번호")

        if uploaded:
            try:
                df = read_excel_with_password(uploaded, password, header=1)
                st.session_state.naver_raw_data = df

                st.caption(f"✅ 파일 로드 완료: {len(df)}개 주문")
                st.dataframe(df.head(5), width="stretch")
            except Exception as e:
                st.error(f"파일을 읽는 중 오류가 발생했습니다: {e}")
                df = None
        else:
            df = None

        if df is not None:

            if st.button("다음 단계: 데이터 파싱 및 검수", type="primary"):
                with st.spinner("옵션정보 파싱 중..."):
                    intermediate = create_naver_intermediate_table(df, api_key)
                    st.session_state.naver_intermediate_table = intermediate
                    st.session_state.naver_workflow_step = "review"
                    st.rerun()

    elif current_step == "review":
        st.markdown("### 2️⃣ 데이터 검수 및 수정")
        st.caption("AI가 날짜를 정규화합니다. 검수 후 필요 시 수정하세요.")

        intermediate = st.session_state.naver_intermediate_table

        if intermediate["도착희망날짜_정규화"].iloc[0] == "":
            if st.button("🤖 AI로 날짜 자동 변환", type="primary"):
                progress_bar = st.progress(0)
                status_text = st.empty()
                debug_container = st.expander("🔍 상세 로그 (디버깅)", expanded=True)

                def update_progress(current, total):
                    progress = current / total
                    progress_bar.progress(progress)
                    status_text.text(f"날짜 변환 중... (배치 {current}/{total})")

                def debug_log(log_type, data):
                    if log_type == "info":
                        with debug_container:
                            st.info(data)
                    elif log_type == "unique_dates":
                        with debug_container:
                            st.write("**📋 유니크 날짜 샘플 (처음 10개):**")
                            st.write(data)
                    elif log_type == "batch_start":
                        with debug_container:
                            st.write(f"⏳ {data}")
                    elif log_type == "batch_result":
                        with debug_container:
                            st.write(f"**✅ 배치 {data['batch_idx']} 결과:**")
                            st.json(data["mapping"])

                with st.spinner("AI로 날짜 정규화 중..."):
                    intermediate = normalize_dates_batch(intermediate, api_key, update_progress, debug_log)
                    st.session_state.naver_intermediate_table = intermediate
                    if "naver_intermediate_editor" in st.session_state:
                        del st.session_state.naver_intermediate_editor

                progress_bar.empty()
                status_text.empty()
                st.success("✅ 날짜 변환 완료!")
                st.rerun()
        else:
            st.success("✅ 날짜 변환 완료")

        st.markdown("**중간 테이블 (수정 가능)**")
        st.caption("날짜가 잘못 변환된 경우 직접 수정할 수 있습니다. (YYYY-MM-DD 형식)")

        with st.form("naver_cj_review_form"):
            edited_df = st.data_editor(
                intermediate,
                use_container_width=True,
                num_rows="fixed",
                disabled=[
                    "상품주문번호",
                    "수취인명",
                    "수취인연락처1",
                    "통합배송지",
                    "배송메세지",
                    "수량",
                    "옵션관리코드",
                    "도착희망날짜_원본",
                ],
                key="naver_intermediate_editor",
            )
            next_clicked = st.form_submit_button("다음 단계: CJ 발주서 생성 →", type="primary")

        st.markdown("---")
        st.markdown("**📊 날짜별 주문 통계**")
        date_counts = st.session_state.naver_intermediate_table["도착희망날짜_정규화"].value_counts().sort_index()
        date_counts_df = date_counts.reset_index()
        date_counts_df.columns = ["날짜", "주문 수"]
        st.dataframe(date_counts_df, width="stretch")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("← 처음부터 다시"):
                st.session_state.naver_workflow_step = "upload"
                st.session_state.naver_intermediate_table = None
                st.session_state.naver_raw_data = None
                if "naver_intermediate_editor" in st.session_state:
                    del st.session_state.naver_intermediate_editor
                st.rerun()
        with col2:
            if next_clicked:
                st.session_state.naver_intermediate_table = edited_df
                st.session_state.naver_workflow_step = "generate"
                st.rerun()

    elif current_step == "generate":
        st.markdown("### 3️⃣ CJ 발주서 생성")

        intermediate = st.session_state.naver_intermediate_table

        if st.button("📦 CJ 발주서 생성", type="primary"):
            with st.spinner("CJ 발주서 생성 중..."):
                defaults = get_sender_defaults()
                results = generate_cj_orders_by_date(intermediate, defaults)
                st.session_state.naver_cj_result = results
                result = results.get("single")
                if result:
                    st.success(f"✅ CJ 발주서 생성 완료! (총 {result['count']}건)")

        results = st.session_state.get("naver_cj_result")
        if results:
            st.markdown("---")
            st.markdown("**📥 다운로드**")

            # 단일 파일로 변경
            result = results.get("single")
            if result:
                st.caption(f"✅ 총 {result['count']}건의 발주서가 생성되었습니다.")
                st.dataframe(result["df"].head(20), width="stretch")
                st.download_button(
                    "다운로드: 네이버 CJ 발주서",
                    data=result["data"],
                    file_name=result["filename"],
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary",
                )

        st.markdown("---")
        if st.button("← 처음부터 다시"):
            st.session_state.naver_workflow_step = "upload"
            st.session_state.naver_intermediate_table = None
            st.session_state.naver_raw_data = None
            st.session_state.naver_cj_result = None
            st.rerun()
