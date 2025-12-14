import datetime as dt
import io

import pandas as pd
import streamlit as st

from utils.coupang_processor import build_coupang_bulk
from utils.excel_utils import read_excel_with_password, render_password_input


def render_coupang_bulk():
    st.markdown("**쿠팡 로우데이터 + 파일접수 상세내역 업로드**")

    raw_file = st.file_uploader(
        "쿠팡 로우데이터 (.xlsx)", type=["xlsx"], accept_multiple_files=False, key="raw_coupang_bulk"
    )
    raw_password = None
    if raw_file:
        raw_password = render_password_input("raw_coupang", "로우데이터 파일 비밀번호")

    cj_file = st.file_uploader(
        "파일접수 상세내역 (.xlsx)", type=["xlsx"], accept_multiple_files=False, key="cj_bulk"
    )
    cj_password = None
    if cj_file:
        cj_password = render_password_input("cj_coupang_bulk", "파일접수 상세내역 파일 비밀번호")

    files_key = (raw_file.name if raw_file else None, cj_file.name if cj_file else None)
    if files_key != st.session_state.last_bulk_names:
        st.session_state.coupang_bulk_result = None
        st.session_state.last_bulk_names = files_key

    if raw_file:
        try:
            df_raw = read_excel_with_password(raw_file, raw_password)
            st.caption("로우데이터 미리보기 (최대 5행)")
            st.dataframe(df_raw.head(5), width="stretch")
        except Exception as e:
            st.error(f"로우데이터 파일을 읽는 중 오류가 발생했습니다: {e}")
            df_raw = None
    else:
        df_raw = None

    if cj_file:
        try:
            df_cj = read_excel_with_password(cj_file, cj_password)
            st.caption("파일접수 상세내역 미리보기 (최대 5행)")
            st.dataframe(df_cj.head(5), width="stretch")
        except Exception as e:
            st.error(f"파일접수 상세내역 파일을 읽는 중 오류가 발생했습니다: {e}")
            df_cj = None
    else:
        df_cj = None

    if df_raw is not None and df_cj is not None:
        if st.button("작업 실행", type="primary"):
            try:
                result_df = build_coupang_bulk(df_raw, df_cj)
                match_count = result_df["운송장번호"].fillna("").astype(str).str.strip().ne("").sum()
                total = len(result_df)
                if match_count == 0:
                    st.warning("주문번호 매칭 결과가 0건입니다. 두 파일의 주문번호/고객주문번호를 확인하세요.")
                    st.session_state.coupang_bulk_result = None
                    return

                buf = io.BytesIO()
                result_df.to_excel(buf, index=False)
                buf.seek(0)
                filename = f"쿠팡_대량등록_{dt.datetime.now():%y%m%d}.xlsx"
                st.session_state.coupang_bulk_result = {
                    "df": result_df,
                    "data": buf.getvalue(),
                    "name": filename,
                    "match": match_count,
                    "total": total,
                }
                st.success(f"작업 완료: {filename} (운송장 매칭 {match_count}/{total})")
            except Exception as e:
                st.error(f"처리 중 오류가 발생했습니다: {e}")

    result = st.session_state.get("coupang_bulk_result")
    if result:
        st.markdown("---")
        st.markdown("**작업 결과 미리보기 (상위 10행)**")
        st.dataframe(result["df"].head(10), width="stretch")
        match = result.get("match")
        total = result.get("total")
        if match is not None and total is not None:
            st.caption(f"운송장번호 매칭 결과: {match}/{total}")
        st.download_button(
            "다운로드: 쿠팡 대량등록",
            data=result["data"],
            file_name=result["name"],
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
        )
