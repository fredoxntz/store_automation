import datetime as dt
import io

import pandas as pd
import streamlit as st

from utils.naver_processor import build_naver_bulk, clean_columns, _normalize_order
from utils.excel_utils import read_excel_with_password, render_password_input


def render_naver_bulk():
    st.markdown("**네이버 로우데이터 + 파일접수 상세내역 업로드**")

    raw_file = st.file_uploader(
        "네이버 로우데이터 (.xlsx)", type=["xlsx"], accept_multiple_files=False, key="raw_naver_bulk"
    )
    raw_password = None
    if raw_file:
        raw_password = render_password_input("raw_naver", "로우데이터 파일 비밀번호")

    cj_file = st.file_uploader(
        "파일접수 상세내역 (.xlsx)", type=["xlsx"], accept_multiple_files=False, key="cj_naver_bulk"
    )
    cj_password = None
    if cj_file:
        cj_password = render_password_input("cj_naver", "파일접수 상세내역 파일 비밀번호")

    files_key = (raw_file.name if raw_file else None, cj_file.name if cj_file else None)
    if files_key != st.session_state.last_naver_bulk_names:
        st.session_state.naver_bulk_result = None
        st.session_state.last_naver_bulk_names = files_key

    if raw_file:
        try:
            df_raw = read_excel_with_password(raw_file, raw_password, header=1)
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
                result_df, debug_info = build_naver_bulk(df_raw, df_cj)
                # 주문번호 매칭 결과는 debug_info에서 가져옴
                match_count = debug_info['matched_count']
                total = debug_info['total_count']

                # 송장번호가 실제로 채워진 건수 (운송장번호 데이터가 있는 경우)
                invoice_filled_count = result_df["송장번호"].fillna("").astype(str).str.strip().ne("").sum()

                # 디버그 정보 표시
                with st.expander("🔍 매칭 디버그 정보", expanded=(match_count == 0)):
                    st.markdown(f"**로우데이터:** {debug_info['raw_count']}건")
                    st.markdown(f"**CJ 파일:** {debug_info['cj_count']}건 (사용 컬럼: `{debug_info['key_col']}`)")
                    st.markdown(f"**주문번호 매칭:** {match_count}/{total}건")
                    st.markdown(f"**송장번호 채워짐:** {invoice_filled_count}/{total}건")

                    st.markdown("---")
                    st.markdown("**로우데이터 상품주문번호 샘플 (정규화 전 → 후)**")
                    for i, sample in enumerate(debug_info["raw_samples"]):
                        st.code(f"{i+1}. '{sample['original']}' ({sample['type']}) → '{sample['normalized']}'")

                    st.markdown("**CJ 파일 고객주문번호 샘플 (정규화 전 → 후)**")
                    has_invoice = debug_info.get("has_invoice_col", False)
                    if has_invoice:
                        st.caption("운송장번호 컬럼: ✅ 있음")
                        for i, sample in enumerate(debug_info["cj_samples"]):
                            invoice_info = f" | 운송장: '{sample.get('invoice', '')}'" if sample.get('invoice') else " | 운송장: (없음)"
                            st.code(f"{i+1}. '{sample['original']}' ({sample['type']}) → '{sample['normalized']}'{invoice_info}")
                    else:
                        st.caption("⚠️ 운송장번호 컬럼: 없음 (CJ 파일에 '운송장번호' 컬럼이 없습니다)")
                        for i, sample in enumerate(debug_info["cj_samples"]):
                            st.code(f"{i+1}. '{sample['original']}' ({sample['type']}) → '{sample['normalized']}'")

                    if "unmatched" in debug_info:
                        st.markdown("---")
                        st.markdown(f"**⚠️ 매칭 안 된 주문번호:** {debug_info['unmatched_count']}개")
                        for i, key in enumerate(debug_info["unmatched"]):
                            st.code(f"{i+1}. '{key}'")

                        st.markdown("**CJ 파일에 있는 키 샘플 (최대 10개)**")
                        for i, key in enumerate(debug_info["cj_keys_sample"]):
                            st.code(f"{i+1}. '{key}'")

                if match_count == 0:
                    st.warning("주문번호 매칭 결과가 0건입니다. 위의 디버그 정보를 확인하세요.")
                    st.session_state.naver_bulk_result = None
                    return

                if invoice_filled_count == 0:
                    st.warning(f"⚠️ 주문번호는 {match_count}건 매칭되었으나, CJ 파일에 운송장번호 데이터가 없습니다. CJ 파일을 확인하세요.")

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
                st.success(f"작업 완료: {filename} (주문번호 매칭 {match_count}/{total}, 송장번호 {invoice_filled_count}건)")
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
