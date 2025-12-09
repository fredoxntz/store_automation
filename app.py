import io
import json
import datetime as dt
from pathlib import Path

import pandas as pd
import streamlit as st


st.set_page_config(page_title="송장 자동화", page_icon="📦", layout="wide")

# 설정 파일 경로
CONFIG_FILE = Path("config.json")


def load_config():
    """설정 파일에서 설정을 로드합니다."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_config(config: dict):
    """설정을 파일에 저장합니다."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"설정 저장 중 오류가 발생했습니다: {e}")
        return False


def get_openai_api_key():
    """저장된 OpenAI API 키를 반환합니다."""
    config = load_config()
    return config.get("openai_api_key", "")


def save_openai_api_key(api_key: str):
    """OpenAI API 키를 저장합니다."""
    config = load_config()
    config["openai_api_key"] = api_key
    return save_config(config)


def test_openai_api(api_key: str, message: str):
    """OpenAI API를 테스트합니다. (Responses API)"""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)

        response = client.responses.create(
            model="gpt-5.1-2025-11-13",
            input=[
                {"role": "system", "content": "You are a helpful assistant. Please respond in Korean."},
                {"role": "user", "content": message}
            ],
            max_output_tokens=500
        )

        return {"success": True, "message": response.output_text}

    except Exception as e:
        return {"success": False, "message": f"API 오류: {str(e)}"}

def parse_naver_option(option_str: str) -> dict:
    """네이버 옵션정보를 파싱합니다."""
    result = {
        "보내시는분": "",
        "도착희망날짜_원본": "",
        "과일선물옵션": "",
        "크리스탈보자기": ""
    }

    if pd.isna(option_str):
        return result

    # " / "로 분리
    parts = str(option_str).split(" / ")

    for part in parts:
        if ":" in part:
            key, value = part.split(":", 1)
            key = key.strip()
            value = value.strip()

            if "보내시는 분" in key:
                result["보내시는분"] = value
            elif "도착 희망 날짜" in key or "도착희망날짜" in key:
                result["도착희망날짜_원본"] = value
            elif "과일 선물 옵션" in key or "과일선물옵션" in key:
                result["과일선물옵션"] = value
            elif "크리스탈 보자기" in key:
                result["크리스탈보자기"] = value

    return result


def normalize_dates_batch_with_ai(api_key: str, date_list: list) -> dict:
    """AI를 사용하여 날짜 배열을 일괄 정규화합니다. (Responses API 기반, 오류 안전 처리 포함)"""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)

        dates_json = json.dumps(date_list, ensure_ascii=False)

        prompt = f"""
다음 JSON 배열의 각 날짜 텍스트를 YYYY-MM-DD 형식으로 변환해주세요.
"최대한 빨리", "빠른배송" 등 날짜가 아닌 경우 "빠른배송"으로 변환하세요.
날짜 정보가 불확실하다고 판단될때는 인풋에 있는 날짜 정보를 참고해서 변환하세요. 
변환하는 날짜들은 비슷한 시점입니다.

입력: {dates_json}

출력은 반드시 "원본": "변환결과" 형태의 JSON 객체로만 답변하세요. 설명은 하지 마세요.
예시: {{"9월30일": "2024-09-30", "10/1": "2024-10-01", "최대한 빨리": "빠른배송"}}
"""

        response = client.responses.create(
            model="gpt-5.1-2025-11-13",
            input=prompt,
            max_output_tokens=1000,
        )

        result_text = (response.output_text or "").strip()

        # 1) 출력이 비었으면 에러 처리
        if not result_text:
            return {date: "오류: 빈 응답" for date in date_list}

        # 2) 코드블록 제거
        if result_text.startswith("```"):
            parts = result_text.split("```")
            if len(parts) >= 2:
                result_text = parts[1]
            result_text = result_text.replace("json", "").strip()

        # 3) JSON만 추출 (앞뒤 텍스트 제거)
        #    → { ... } 만 찾아서 parse
        import re
        json_match = re.search(r"\{.*\}", result_text, re.DOTALL)
        if json_match:
            result_text = json_match.group(0).strip()
        else:
            return {date: "오류: JSON 출력 아님" for date in date_list}

        # 4) JSON 파싱
        try:
            return json.loads(result_text)
        except Exception:
            return {date: f"오류: JSON 파싱 실패: {result_text}" for date in date_list}

    except Exception as e:
        return {date: f"오류: {str(e)}" for date in date_list}


def create_naver_intermediate_table(df: pd.DataFrame, api_key: str) -> pd.DataFrame:
    """네이버 로우데이터로부터 중간 테이블을 생성합니다."""
    # 옵션정보 파싱
    parsed_options = df["옵션정보"].apply(parse_naver_option)
    parsed_df = pd.DataFrame(parsed_options.tolist())

    # 중간 테이블 생성
    intermediate = pd.DataFrame({
        "상품주문번호": df["상품주문번호"],
        "수취인명": df["수취인명"],
        "수취인연락처1": df["수취인연락처1"],
        "통합배송지": df["통합배송지"],
        "배송메세지": df["배송메세지"],
        "수량": df["수량"],
        "옵션관리코드": df["옵션관리코드"],
        "보내시는분": parsed_df["보내시는분"],
        "도착희망날짜_원본": parsed_df["도착희망날짜_원본"],
        "도착희망날짜_정규화": "",  # AI로 채울 예정
        "과일선물옵션": parsed_df["과일선물옵션"],
    })

    return intermediate


def normalize_dates_batch(intermediate_df: pd.DataFrame, api_key: str, progress_callback=None, debug_callback=None) -> pd.DataFrame:
    """중간 테이블의 날짜를 일괄 정규화합니다. (배치 처리)"""
    result_df = intermediate_df.copy()

    # 유니크한 날짜 문자열만 추출
    unique_dates = result_df["도착희망날짜_원본"].dropna().unique().tolist()

    if not unique_dates:
        return result_df

    # 디버그: 유니크 값 개수 표시
    if debug_callback:
        debug_callback("info", f"📊 추출된 유니크 날짜: {len(unique_dates)}개")
        debug_callback("unique_dates", unique_dates[:10])  # 처음 10개만 표시

    # 날짜 변환 결과 캐시
    date_mapping = {}

    # 100개씩 배치로 나누기
    batch_size = 30
    total_batches = (len(unique_dates) + batch_size - 1) // batch_size

    for batch_idx in range(total_batches):
        start_idx = batch_idx * batch_size
        end_idx = min((batch_idx + 1) * batch_size, len(unique_dates))
        batch = unique_dates[start_idx:end_idx]

        # 디버그: 배치 정보 표시
        if debug_callback:
            debug_callback("batch_start", f"배치 {batch_idx + 1}/{total_batches} - {len(batch)}개 날짜 처리 중...")

        # 배치 단위로 AI 호출 (딕셔너리 반환)
        batch_mapping = normalize_dates_batch_with_ai(api_key, batch)

        # 디버그: AI 응답 표시
        if debug_callback:
            debug_callback("batch_result", {"batch_idx": batch_idx + 1, "mapping": batch_mapping})

        # 결과를 전체 매핑에 병합
        date_mapping.update(batch_mapping)

        if progress_callback:
            progress_callback(batch_idx + 1, total_batches)

    # 매핑 적용
    result_df["도착희망날짜_정규화"] = result_df["도착희망날짜_원본"].map(date_mapping).fillna("")

    return result_df


def generate_cj_orders_by_date(intermediate_df: pd.DataFrame, defaults: dict[str, str]) -> dict:
    """날짜별로 CJ 발주서를 생성합니다."""
    # 날짜별로 그룹화
    grouped = intermediate_df.groupby("도착희망날짜_정규화")

    results = {}

    for date, group in grouped:
        # CJ 발주서 형식으로 변환
        qty = pd.to_numeric(group["수량"], errors="coerce").fillna(0).astype(int)
        item_name = group["보내시는분"].fillna("OOO").astype(str) + "드림 " + group["옵션관리코드"].fillna("").astype(str)

        cj_df = pd.DataFrame({
            "보내는분성명": defaults["name"],
            "보내는분전화번호": defaults["phone"],
            "보내는분주소(전체,분할)": defaults["address"],
            "운임구분": "신용",
            "박스타입": "극소",
            "기본운임": qty * 2200,
            "고객주문번호": group["상품주문번호"],
            "품목명": item_name,
            "수량": qty,
            "수취인이름": group["수취인명"],
            "수취인전화번호": group["수취인연락처1"],
            "수취인 주소": group["통합배송지"],
            "배송메세지": group["배송메세지"],
        })

        # 엑셀 파일로 변환
        buf = io.BytesIO()
        cj_df.to_excel(buf, index=False)
        buf.seek(0)

        results[date] = {
            "df": cj_df,
            "data": buf.getvalue(),
            "count": len(cj_df)
        }

    return results


# Lightweight custom styling for a clean, card-like UI
st.markdown(
    """
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

    /* Base button styling */
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

    /* Landing buttons (grey base, hover to white) */
    button[aria-label="🚚 CJ 발주서 만들기"],
    button[aria-label="📑 대량등록 파일 만들기"] {
        max-width: 280px;
        width: 100%;
    }

    /* Channel buttons: pastel per brand */
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

    /* Settings icon button - clean and minimal */
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
    """,
    unsafe_allow_html=True,
)

# 타이틀과 설정 버튼
col1, col2 = st.columns([10, 1])
with col1:
    st.title("📦 송장 자동화")
with col2:
    st.write("")  # 여백 추가
    st.markdown('<div class="settings-btn">', unsafe_allow_html=True)
    if st.button("⚙️", help="설정", key="settings_btn"):
        st.session_state.show_settings = True
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

st.caption("CJ 발주서 · 대량등록 파일 자동 생성")

if "step" not in st.session_state:
    st.session_state.step = "landing"
if "job" not in st.session_state:
    st.session_state.job = None
if "channel" not in st.session_state:
    st.session_state.channel = None
if "coupang_cj_result" not in st.session_state:
    st.session_state.coupang_cj_result = None
if "coupang_bulk_result" not in st.session_state:
    st.session_state.coupang_bulk_result = None
if "last_uploaded_name" not in st.session_state:
    st.session_state.last_uploaded_name = None
if "last_bulk_names" not in st.session_state:
    st.session_state.last_bulk_names = (None, None)
if "show_settings" not in st.session_state:
    st.session_state.show_settings = False
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "naver_cj_result" not in st.session_state:
    st.session_state.naver_cj_result = None
if "last_naver_uploaded_name" not in st.session_state:
    st.session_state.last_naver_uploaded_name = None
if "naver_intermediate_table" not in st.session_state:
    st.session_state.naver_intermediate_table = None
if "naver_raw_data" not in st.session_state:
    st.session_state.naver_raw_data = None
if "naver_workflow_step" not in st.session_state:
    st.session_state.naver_workflow_step = "upload"  # upload -> parse -> review -> generate


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


def get_sender_defaults():
    """Sender defaults read from example CJ 발주서 if available, else fall back values."""
    example_path = Path("output/example/coupang/쿠팡 CJ 발주서.xlsx")
    defaults = {
        "name": "과일선물은 청과옥",
        "phone": "010-8238-0368",
        "address": "서울특별시 서초구 서초대로15길 13-4 (방배동) 102호",
    }
    if example_path.exists():
        try:
            sample = pd.read_excel(example_path)
            defaults["name"] = str(sample.loc[0, "보내는분성명"])
            defaults["phone"] = str(sample.loc[0, "보내는분전화번호"])
            defaults["address"] = str(sample.loc[0, "보내는분주소(전체,분할)"])
        except Exception:
            pass
    return defaults


def get_coupang_bulk_columns():
    """Column order for 쿠팡 대량등록, prefer reading from example file."""
    example_path = Path("output/example/coupang/쿠팡 대량등록.xlsx")
    fallback = [
        "번호",
        "묶음배송번호",
        "주문번호",
        "택배사",
        "운송장번호",
        "분리배송 Y/N",
        "분리배송 출고예정일",
        "주문시 출고예정일",
        "출고일(발송일)",
        "주문일",
        "등록상품명",
        "등록옵션명",
        "노출상품명(옵션명)",
        "노출상품ID",
        "옵션ID",
        "최초등록옵션명",
        "업체상품코드",
        "바코드",
        "결제액",
        "배송비구분",
        "배송비",
        "도서산간 추가배송비",
        "구매수(수량)",
        "옵션판매가(판매단가)",
        "구매자",
        "구매자전화번호",
        "수취인이름",
        "수취인전화번호",
        "우편번호",
        "수취인 주소",
        "배송메세지",
        "상품별 추가메시지",
        "주문자 추가메시지",
        "배송완료일",
        "구매확정일자",
        "개인통관번호(PCCC)",
        "통관용구매자전화번호",
        "기타",
        "결제위치",
    ]
    if example_path.exists():
        try:
            cols = list(pd.read_excel(example_path, nrows=0).columns)
            if cols:
                return cols
        except Exception:
            pass
    return fallback


def clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Strip whitespace from column names to avoid merge mismatches."""
    return df.rename(columns=lambda c: str(c).strip())


def build_coupang_cj(df: pd.DataFrame, defaults: dict[str, str]) -> pd.DataFrame:
    """Transform Coupang raw data into CJ 발주서 format."""
    required_cols = [
        "수취인이름",
        "수취인전화번호",
        "수취인 주소",
        "배송메세지",
        "구매수(수량)",
        "구매자",
        "업체상품코드",
        "주문번호",
    ]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"누락된 필수 컬럼: {', '.join(missing)}")

    def normalize_order(x):
        if pd.isna(x):
            return ""
        if isinstance(x, float):
            return str(int(x))
        if isinstance(x, int):
            return str(x)
        s = str(x).strip()
        if s.endswith(".0") and s.replace(".", "", 1).isdigit():
            try:
                return str(int(float(s)))
            except Exception:
                return s
        return s

    qty = pd.to_numeric(df["구매수(수량)"], errors="coerce").fillna(0).astype(int)
    item_name = (
        df["구매자"].fillna("").astype(str)
        + "드림 "
        + df["업체상품코드"].fillna("").astype(str)
    )
    order_no = df["주문번호"].apply(normalize_order)

    output = pd.DataFrame(
        {
            "보내는분성명": defaults["name"],
            "보내는분전화번호": defaults["phone"],
            "보내는분주소(전체,분할)": defaults["address"],
            "운임구분": "신용",
            "박스타입": "극소",
            "기본운임": qty * 2200,
            "고객주문번호": order_no,
            "품목명": item_name,
            "수량": qty,
            "수취인이름": df["수취인이름"],
            "수취인전화번호": df["수취인전화번호"],
            "수취인 주소": df["수취인 주소"],
            "배송메세지": df["배송메세지"],
        }
    )
    return output


def build_naver_cj(df: pd.DataFrame, defaults: dict[str, str]) -> pd.DataFrame:
    """Transform Naver raw data into CJ 발주서 format."""
    required_cols = [
        "수취인명",
        "수취인연락처1",
        "통합배송지",
        "배송메세지",
        "수량",
        "옵션관리코드",
        "상품주문번호",
    ]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"누락된 필수 컬럼: {', '.join(missing)}")

    def normalize_order(x):
        if pd.isna(x):
            return ""
        if isinstance(x, float):
            return str(int(x))
        if isinstance(x, int):
            return str(x)
        s = str(x).strip()
        if s.endswith(".0") and s.replace(".", "", 1).isdigit():
            try:
                return str(int(float(s)))
            except Exception:
                return s
        return s

    qty = pd.to_numeric(df["수량"], errors="coerce").fillna(0).astype(int)
    # 네이버는 "OOO드림 {옵션관리코드}" 형식
    item_name = "OOO드림 " + df["옵션관리코드"].fillna("").astype(str)
    order_no = df["상품주문번호"].apply(normalize_order)

    output = pd.DataFrame(
        {
            "보내는분성명": defaults["name"],
            "보내는분전화번호": defaults["phone"],
            "보내는분주소(전체,분할)": defaults["address"],
            "운임구분": "신용",
            "박스타입": "극소",
            "기본운임": qty * 2200,
            "고객주문번호": order_no,
            "품목명": item_name,
            "수량": qty,
            "수취인이름": df["수취인명"],
            "수취인전화번호": df["수취인연락처1"],
            "수취인 주소": df["통합배송지"],
            "배송메세지": df["배송메세지"],
        }
    )
    return output


def render_coupang_cj():
    st.markdown("**쿠팡 로우데이터 업로드**")
    uploaded = st.file_uploader(
        "쿠팡 로우데이터 엑셀 파일 (.xlsx)", type=["xlsx"], accept_multiple_files=False
    )

    # Reset previous result if new file uploaded
    if uploaded and uploaded.name != st.session_state.last_uploaded_name:
        st.session_state.coupang_cj_result = None
        st.session_state.last_uploaded_name = uploaded.name

    if uploaded:
        df = pd.read_excel(uploaded)
        st.caption("업로드 파일 미리보기 (최대 5행)")
        st.dataframe(df.head(5), width="stretch")

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


def render_naver_cj():
    """네이버 CJ 발주서 생성 워크플로우 (중간 테이블 포함)"""

    # API 키 확인
    api_key = get_openai_api_key()
    if not api_key:
        st.warning("⚠️ OpenAI API 키가 필요합니다. 설정 페이지에서 API 키를 등록해주세요.")
        return

    # 워크플로우 상태 표시
    steps = ["1️⃣ 파일 업로드", "2️⃣ 데이터 검수", "3️⃣ CJ 발주서 생성"]
    current_step = st.session_state.naver_workflow_step

    if current_step == "upload":
        step_idx = 0
    elif current_step == "review":
        step_idx = 1
    else:  # generate
        step_idx = 2

    st.markdown(f"**진행 단계:** {' → '.join([f'**{s}**' if i == step_idx else s for i, s in enumerate(steps)])}")
    st.markdown("---")

    # STEP 1: 파일 업로드
    if current_step == "upload":
        st.markdown("### 1️⃣ 네이버 로우데이터 업로드")
        st.caption("네이버 엑셀 파일은 첫 행에 안내문이 있으므로 자동으로 처리됩니다.")

        uploaded = st.file_uploader(
            "네이버 로우데이터 엑셀 파일 (.xlsx)",
            type=["xlsx"],
            accept_multiple_files=False,
            key="naver_cj_uploader"
        )

        if uploaded:
            # 네이버는 header=1로 읽어야 함 (첫 행이 안내문)
            df = pd.read_excel(uploaded, header=1)
            st.session_state.naver_raw_data = df

            st.caption(f"✅ 파일 로드 완료: {len(df)}개 주문")
            st.dataframe(df.head(5), width="stretch")

            if st.button("다음 단계: 데이터 파싱 및 검수", type="primary"):
                with st.spinner("옵션정보 파싱 중..."):
                    # 중간 테이블 생성
                    intermediate = create_naver_intermediate_table(df, api_key)
                    st.session_state.naver_intermediate_table = intermediate
                    st.session_state.naver_workflow_step = "review"
                    st.rerun()

    # STEP 2: 데이터 검수
    elif current_step == "review":
        st.markdown("### 2️⃣ 데이터 검수 및 수정")
        st.caption("AI가 날짜를 정규화합니다. 검수 후 필요 시 수정하세요.")

        intermediate = st.session_state.naver_intermediate_table

        # AI 날짜 정규화 버튼
        if intermediate["도착희망날짜_정규화"].iloc[0] == "":
            if st.button("🤖 AI로 날짜 자동 변환", type="primary"):
                progress_bar = st.progress(0)
                status_text = st.empty()
                debug_container = st.expander("🔍 상세 로그 (디버깅)", expanded=True)

                debug_logs = []

                def update_progress(current, total):
                    progress = current / total
                    progress_bar.progress(progress)
                    status_text.text(f"날짜 변환 중... (배치 {current}/{total})")

                def debug_log(log_type, data):
                    if log_type == "info":
                        debug_logs.append(("info", data))
                        with debug_container:
                            st.info(data)
                    elif log_type == "unique_dates":
                        debug_logs.append(("unique", data))
                        with debug_container:
                            st.write("**📋 유니크 날짜 샘플 (처음 10개):**")
                            st.write(data)
                    elif log_type == "batch_start":
                        debug_logs.append(("batch_start", data))
                        with debug_container:
                            st.write(f"⏳ {data}")
                    elif log_type == "batch_result":
                        debug_logs.append(("result", data))
                        with debug_container:
                            st.write(f"**✅ 배치 {data['batch_idx']} 결과:**")
                            st.json(data["mapping"])

                with st.spinner("AI로 날짜 정규화 중..."):
                    intermediate = normalize_dates_batch(intermediate, api_key, update_progress, debug_log)
                    st.session_state.naver_intermediate_table = intermediate

                progress_bar.empty()
                status_text.empty()
                st.success("✅ 날짜 변환 완료!")
                st.rerun()
        else:
            st.success("✅ 날짜 변환 완료")

        # 데이터 편집기
        st.markdown("**중간 테이블 (수정 가능)**")
        st.caption("날짜가 잘못 변환된 경우 직접 수정할 수 있습니다. (YYYY-MM-DD 형식)")

        edited_df = st.data_editor(
            intermediate,
            use_container_width=True,
            num_rows="fixed",
            disabled=["상품주문번호", "수취인명", "수취인연락처1", "통합배송지", "배송메세지", "수량", "옵션관리코드", "도착희망날짜_원본"],
            key="naver_intermediate_editor"
        )

        st.session_state.naver_intermediate_table = edited_df

        # 날짜별 통계
        st.markdown("---")
        st.markdown("**📊 날짜별 주문 통계**")
        date_counts = edited_df["도착희망날짜_정규화"].value_counts().sort_index()
        date_counts_df = date_counts.reset_index()
        date_counts_df.columns = ["날짜", "주문 수"]
        st.dataframe(date_counts_df, width="stretch")

        # 버튼
        col1, col2 = st.columns(2)
        with col1:
            if st.button("← 처음부터 다시"):
                st.session_state.naver_workflow_step = "upload"
                st.session_state.naver_intermediate_table = None
                st.session_state.naver_raw_data = None
                st.rerun()
        with col2:
            if st.button("다음 단계: CJ 발주서 생성 →", type="primary"):
                st.session_state.naver_workflow_step = "generate"
                st.rerun()

    # STEP 3: CJ 발주서 생성
    elif current_step == "generate":
        st.markdown("### 3️⃣ 날짜별 CJ 발주서 생성")

        intermediate = st.session_state.naver_intermediate_table

        if st.button("📦 CJ 발주서 생성", type="primary"):
            with st.spinner("CJ 발주서 생성 중..."):
                defaults = get_sender_defaults()
                results = generate_cj_orders_by_date(intermediate, defaults)
                st.session_state.naver_cj_result = results
                st.success(f"✅ {len(results)}개 날짜별 발주서 생성 완료!")

        # 결과 표시 및 다운로드
        results = st.session_state.get("naver_cj_result")
        if results:
            st.markdown("---")
            st.markdown("**📥 다운로드**")

            for date, result in sorted(results.items()):
                with st.expander(f"📅 {date} ({result['count']}건)"):
                    st.dataframe(result["df"].head(10), width="stretch")
                    st.download_button(
                        f"다운로드: {date}",
                        data=result["data"],
                        file_name=f"네이버_CJ발주서_{date}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"download_{date}"
                    )

        # 처음부터 다시 버튼
        st.markdown("---")
        if st.button("← 처음부터 다시"):
            st.session_state.naver_workflow_step = "upload"
            st.session_state.naver_intermediate_table = None
            st.session_state.naver_raw_data = None
            st.session_state.naver_cj_result = None
            st.rerun()


def build_coupang_bulk(raw_df: pd.DataFrame, cj_df: pd.DataFrame) -> pd.DataFrame:
    """Merge Coupang raw data with CJ 접수 상세내역 to produce bulk upload."""

    raw_df = clean_columns(raw_df)
    cj_df = clean_columns(cj_df)

    def normalize_number(x):
        if pd.isna(x):
            return ""
        if isinstance(x, float):
            return str(int(x))
        if isinstance(x, int):
            return str(x)
        s = str(x).strip()
        if s.endswith(".0") and s.replace(".", "", 1).isdigit():
            try:
                return str(int(float(s)))
            except Exception:
                return s
        return s

    raw_df = raw_df.copy()
    cj_df = cj_df.copy()

    raw_df["__key"] = raw_df["주문번호"].apply(normalize_number)
    key_col = "고객주문번호" if "고객주문번호" in cj_df.columns else "주문번호"
    cj_df["__key"] = cj_df[key_col].apply(normalize_number)

    merged = raw_df.merge(
        cj_df[["__key", "운송장번호", "집화예정일자"]],
        on="__key",
        how="left",
        suffixes=("", "_cj"),
    )

    # 최종 운송장번호: CJ 파일 값 우선, 없으면 로우데이터 값
    if "운송장번호_cj" in merged:
        merged["__운송장번호"] = merged["운송장번호_cj"].fillna(merged.get("운송장번호"))
    else:
        merged["__운송장번호"] = merged.get("운송장번호")
    merged["__운송장번호"] = merged["__운송장번호"].apply(normalize_number)

    def pick(col, default=""):
        return merged[col] if col in merged.columns else default

    output_cols = get_coupang_bulk_columns()

    # Map values: mostly raw, plus CJ 운송장번호, 출고일(발송일)=집화예정일자, 택배사 기본값
    data = {
        "번호": pick("번호"),
        "묶음배송번호": pick("묶음배송번호"),
        "주문번호": pick("주문번호").apply(normalize_number),
        "택배사": "CJ대한통운",
        # CJ 접수 상세내역의 운송장번호를 우선 사용 (정규화 포함)
        "운송장번호": merged["__운송장번호"],
        "분리배송 Y/N": pick("분리배송 Y/N"),
        "분리배송 출고예정일": pick("분리배송 출고예정일"),
        "주문시 출고예정일": pick("주문시 출고예정일"),
        "출고일(발송일)": pick("집화예정일자"),
        "주문일": pick("주문일"),
        "등록상품명": pick("등록상품명"),
        "등록옵션명": pick("등록옵션명"),
        "노출상품명(옵션명)": pick("노출상품명(옵션명)"),
        "노출상품ID": pick("노출상품ID"),
        "옵션ID": pick("옵션ID"),
        "최초등록옵션명": pick("최초등록옵션명") if "최초등록옵션명" in merged else pick("최초등록등록상품명/옵션명"),
        "업체상품코드": pick("업체상품코드"),
        "바코드": pick("바코드"),
        "결제액": pick("결제액"),
        "배송비구분": pick("배송비구분"),
        "배송비": pick("배송비"),
        "도서산간 추가배송비": pick("도서산간 추가배송비"),
        "구매수(수량)": pick("구매수(수량)"),
        "옵션판매가(판매단가)": pick("옵션판매가(판매단가)"),
        "구매자": pick("구매자"),
        "구매자전화번호": pick("구매자전화번호"),
        "수취인이름": pick("수취인이름"),
        "수취인전화번호": pick("수취인전화번호"),
        "우편번호": pick("우편번호"),
        "수취인 주소": pick("수취인 주소"),
        "배송메세지": pick("배송메세지"),
        "상품별 추가메시지": pick("상품별 추가메시지"),
        "주문자 추가메시지": pick("주문자 추가메시지"),
        "배송완료일": pick("배송완료일"),
        "구매확정일자": pick("구매확정일자"),
        "개인통관번호(PCCC)": pick("개인통관번호(PCCC)"),
        "통관용구매자전화번호": pick("통관용수취인전화번호") if "통관용수취인전화번호" in merged else pick("통관용구매자전화번호"),
        "기타": pick("기타"),
        "결제위치": pick("결제위치"),
    }

    output = pd.DataFrame(data)
    # Ensure column order
    output = output[output_cols]
    return output


def render_coupang_bulk():
    st.markdown("**쿠팡 로우데이터 + 파일접수 상세내역 업로드**")

    raw_file = st.file_uploader(
        "쿠팡 로우데이터 (.xlsx)", type=["xlsx"], accept_multiple_files=False, key="raw_coupang_bulk"
    )
    cj_file = st.file_uploader(
        "파일접수 상세내역 (.xlsx)", type=["xlsx"], accept_multiple_files=False, key="cj_bulk"
    )

    # Reset cached result if new uploads
    files_key = (
        raw_file.name if raw_file else None,
        cj_file.name if cj_file else None,
    )
    if files_key != st.session_state.last_bulk_names:
        st.session_state.coupang_bulk_result = None
        st.session_state.last_bulk_names = files_key

    if raw_file:
        df_raw = pd.read_excel(raw_file)
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
                result_df = build_coupang_bulk(df_raw, df_cj)
                match_count = (
                    result_df["운송장번호"].fillna("").astype(str).str.strip().ne("").sum()
                )
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


def render_settings():
    """설정 페이지를 렌더링합니다."""
    st.markdown("### ⚙️ 설정")
    st.caption("OpenAI API 키를 설정하여 챗봇 기능을 사용할 수 있습니다.")

    st.markdown("---")

    # 현재 저장된 API 키 로드
    current_api_key = get_openai_api_key()

    # API 키 표시 (마스킹)
    if current_api_key:
        masked_key = current_api_key[:8] + "*" * (len(current_api_key) - 12) + current_api_key[-4:] if len(current_api_key) > 12 else "****"
        st.info(f"현재 저장된 API 키: `{masked_key}`")
    else:
        st.warning("저장된 API 키가 없습니다.")

    st.markdown("#### OpenAI API 키 입력")

    # API 키 입력 폼
    with st.form("api_key_form"):
        new_api_key = st.text_input(
            "API 키",
            value="",
            type="password",
            placeholder="sk-...",
            help="OpenAI API 키를 입력하세요. API 키는 암호화되어 로컬에 저장됩니다."
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

    # API 키가 저장되어 있는지 확인
    if current_api_key:
        st.caption("저장된 API 키로 간단한 채팅을 테스트해보세요.")

        # 채팅 테스트 컨테이너
        with st.container():
            # 채팅 히스토리 표시
            if st.session_state.chat_history:
                st.markdown("**채팅 기록:**")
                for chat in st.session_state.chat_history:
                    if chat["role"] == "user":
                        st.markdown(f"**👤 You:** {chat['content']}")
                    else:
                        st.markdown(f"**🤖 AI:** {chat['content']}")
                st.markdown("---")

            # 채팅 입력 폼
            with st.form(key="chat_form", clear_on_submit=True):
                col1, col2 = st.columns([5, 1])
                with col1:
                    user_input = st.text_input("메시지", placeholder="메시지를 입력하세요...", label_visibility="collapsed")
                with col2:
                    submit = st.form_submit_button("전송", use_container_width=True, type="primary")

                if submit and user_input.strip():
                    # 사용자 메시지 추가
                    st.session_state.chat_history.append({"role": "user", "content": user_input.strip()})

                    # API 호출
                    with st.spinner("응답 생성 중..."):
                        result = test_openai_api(current_api_key, user_input.strip())

                    if result["success"]:
                        # AI 응답 추가
                        st.session_state.chat_history.append({"role": "assistant", "content": result["message"]})
                    else:
                        # 에러 메시지 추가
                        st.session_state.chat_history.append({"role": "assistant", "content": f"❌ {result['message']}"})

                    st.rerun()

            # 채팅 히스토리 초기화 버튼
            if st.session_state.chat_history:
                if st.button("🗑️ 채팅 기록 지우기", use_container_width=False):
                    st.session_state.chat_history = []
                    st.rerun()
    else:
        st.info("API 키를 먼저 저장해주세요.")

    st.markdown("---")
    st.markdown("#### API 키 발급 안내")
    st.markdown("""
    1. [OpenAI 플랫폼](https://platform.openai.com/api-keys)에 로그인
    2. API Keys 메뉴에서 'Create new secret key' 클릭
    3. 생성된 키를 복사하여 위에 입력
    """)

    st.markdown("---")
    if st.button("← 메인으로 돌아가기", use_container_width=False):
        st.session_state.show_settings = False
        st.rerun()


# 설정 페이지와 메인 페이지 분기
if st.session_state.show_settings:
    render_settings()
else:
    # 메인 페이지 렌더링
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
        else:
            st.info("이 채널/작업 조합에 대한 폼이 아직 준비되지 않았습니다.")

        st.button("← 채널 선택으로", on_click=lambda: st.session_state.update({"step": "channel"}))
