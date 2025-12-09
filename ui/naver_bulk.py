import datetime as dt
import io

import pandas as pd
import streamlit as st

from utils.naver_processor import build_naver_bulk


def render_naver_bulk():
    st.markdown("**네이버 로우데이터 + 파일접수 상세내역 업로드**")

    raw_file = st.file_uploader(
        "네이버 로우데이터 (.xlsx)", type=["xlsx"], accept_multiple_files=False, key="raw_naver_bulk"
    )
    cj_file = st.file_uploader(
        "파일접수 상세내역 (.xlsx)", type=["xlsx"], accept_multiple_files=False, key="cj_naver_bulk"
    )

    files_key = (raw_file.name if raw_file else None, cj_file.name if cj_file else None)
    if files_key != st.session_state.last_naver_bulk_names:
        st.session_state.naver_bulk_result = None
        st.session_state.last_naver_bulk_names = files_key

    if raw_file:
        df_raw = pd.read_excel(raw_file, header=1)
        st.caption("로우데이터 미리보기 (최대 5행)")
        st.dataframe(df_raw.head(5), width="stretch")
    else:
        df_raw = None

    if cj_file:
        df_cj = pd.read_excel(cj_file)
        st.caption("파일접수 상세내역 미리보기 (최대 5행)")
        st.dataframe(df_cj.head(5), width="stretch")
    else:
        df_cj = None

    if df_raw is not None and df_cj is not None:
        if st.button("작업 실행", type="primary"):
            try:
                result_df = build_naver_bulk(df_raw, df_cj)
                match_count = result_df["송장번호"].fillna("").astype(str).str.strip().ne("").sum()
                total = len(result_df)
                if match_count == 0:
                    st.warning("주문번호 매칭 결과가 0건입니다. 두 파일의 주문번호/고객주문번호를 확인하세요.")
                    st.session_state.naver_bulk_result = None
                    return

                buf = io.BytesIO()
                result_df.to_excel(buf, index=False)
                buf.seek(0)
                filename = f"네이버_대량등록_{dt.datetime.now():%y%m%d}.xlsx"
                st.session_state.naver_bulk_result = {
                    "df": result_df,
                    "data": buf.getvalue(),
                    "name": filename,
                    "match": match_count,
                    "total": total,
                }
                st.success(f"작업 완료: {filename} (운송장 매칭 {match_count}/{total})")
            except Exception as e:
                st.error(f"처리 중 오류가 발생했습니다: {e}")

    result = st.session_state.get("naver_bulk_result")
    if result:
        st.markdown("---")
        st.markdown("**작업 결과 미리보기 (상위 10행)**")
        st.dataframe(result["df"].head(10), width="stretch")
        match = result.get("match")
        total = result.get("total")
        if match is not None and total is not None:
            st.caption(f"운송장번호 매칭 결과: {match}/{total}")
        st.download_button(
            "다운로드: 네이버 대량등록",
            data=result["data"],
            file_name=result["name"],
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
        )
