import datetime as dt
import io

import pandas as pd
import streamlit as st

from utils.coupang_processor import build_coupang_cj, get_sender_defaults
from utils.excel_utils import read_excel_with_password, render_password_input


def render_coupang_cj():
    st.markdown("**쿠팡 로우데이터 업로드**")
    uploaded = st.file_uploader(
        "쿠팡 로우데이터 엑셀 파일 (.xlsx)", type=["xlsx"], accept_multiple_files=False
    )

    password = None
    if uploaded:
        password = render_password_input("coupang_cj", "파일 비밀번호")

    if uploaded and uploaded.name != st.session_state.last_uploaded_name:
        st.session_state.coupang_cj_result = None
        st.session_state.last_uploaded_name = uploaded.name

    if uploaded:
        try:
            df = read_excel_with_password(uploaded, password)
            st.caption("업로드 파일 미리보기 (최대 5행)")
            st.dataframe(df.head(5), width="stretch")
        except Exception as e:
            st.error(f"파일을 읽는 중 오류가 발생했습니다: {e}")
            df = None
    else:
        df = None

    if df is not None:

        if st.button("작업 실행", type="primary"):
            try:
                defaults = get_sender_defaults()
                sorted_df = df.sort_values("업체상품코드").reset_index(drop=True)
                result_df = build_coupang_cj(sorted_df, defaults)
                buf = io.BytesIO()
                result_df.to_excel(buf, index=False)
                buf.seek(0)
                filename = f"쿠팡_CJ발주서_{dt.datetime.now():%y%m%d}.xlsx"
                st.session_state.coupang_cj_result = {
                    "df": result_df,
                    "data": buf.getvalue(),
                    "name": filename,
                }
                st.success(f"작업 완료: {filename}")
            except Exception as e:
                st.error(f"처리 중 오류가 발생했습니다: {e}")

    result = st.session_state.get("coupang_cj_result")
    if result:
        st.markdown("---")
        st.markdown("**작업 결과 미리보기 (상위 10행)**")
        st.dataframe(result["df"].head(10), width="stretch")
        st.download_button(
            "다운로드: 쿠팡 CJ 발주서",
            data=result["data"],
            file_name=result["name"],
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
        )
