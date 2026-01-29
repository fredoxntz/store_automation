import io
import json
import re
from typing import Any, Callable

import pandas as pd


def clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Strip whitespace from column names."""
    return df.rename(columns=lambda c: str(c).strip())


def _normalize_order(value):
    """Normalize order number for matching - remove all spaces and convert to string."""
    if pd.isna(value):
        return ""
    if isinstance(value, float):
        return str(int(value))
    if isinstance(value, int):
        return str(value)
    s = str(value).strip()
    # Remove all whitespace characters (spaces, tabs, newlines, etc.)
    s = "".join(s.split())
    if s.endswith(".0") and s.replace(".", "", 1).isdigit():
        try:
            return str(int(float(s)))
        except Exception:
            return s
    return s


def parse_naver_option(option_str: str) -> dict:
    """Parse 옵션정보 field into structured values."""
    result = {
        "보내시는분": "",
        "도착희망날짜_원본": "",
        "과일선물옵션": "",
        "크리스탈보자기": "",
    }

    if pd.isna(option_str):
        return result

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
    """Use OpenAI Responses API to normalize a batch of date strings."""
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)

        dates_json = json.dumps(date_list, ensure_ascii=False)

        prompt = f"""
다음 JSON 배열의 각 날짜 텍스트를 MM/DD 형식으로 변환해주세요.
날짜 정보가 불확실하다고 판단될때는 문자열 그대로 반환해주세요.
9월 30일 또는 10월 1일 이런 날짜는 문자열 그대로 반환하시오.
10월 8일 수요일처럼 요일정보가 있는 경우 10/8처럼 요일 정보를 제거하고 날짜만 남기시오.
2025-09-30 데이터 타입도 9/30 이런식으로 변경하시오.
26년 2월 30일 이런식으로 오는 데이터 타입도 2/30 이런식으로 변경해야해.
10월 2일 는 10/02 이런식으로.
명확한 날짜가 아닌경우는 변환하지 말고 그대로 다시 변환결과에 넣어줘.

결국 날짜 데이터를 변환할때 내가 원하는 최종 날짜 변환 형태는 MM/DD야. 꼭 이렇게 변환해서 결과를 만들어주길 원해.

입력: {dates_json}

출력은 반드시 "원본": "변환결과" 형태의 JSON 객체로만 답변하세요. 설명은 하지 마세요.
예시: {{"9월30일": "09/30", "10/1": "10/01", "최대한 빨리": "최대한 빨리", "10월 2일": "10/2", 10월 8일 수요일 : "10/8}}
"""

        response = client.responses.create(
            model="gpt-4.1-nano-2025-04-14",
            input=prompt,
            max_output_tokens=1000,
        )

        result_text = (response.output_text or "").strip()

        if not result_text:
            return {date: "오류: 빈 응답" for date in date_list}

        if result_text.startswith("```"):
            parts = result_text.split("```")
            if len(parts) >= 2:
                result_text = parts[1]
            result_text = result_text.replace("json", "").strip()

        json_match = re.search(r"\{.*\}", result_text, re.DOTALL)
        if json_match:
            result_text = json_match.group(0).strip()
        else:
            return {date: "오류: JSON 출력 아님" for date in date_list}

        try:
            return json.loads(result_text)
        except Exception:
            return {date: f"오류: JSON 파싱 실패: {result_text}" for date in date_list}

    except Exception as e:
        return {date: f"오류: {str(e)}" for date in date_list}


def create_naver_intermediate_table(df: pd.DataFrame, api_key: str | None = None) -> pd.DataFrame:
    """Build intermediate table from raw Naver export."""
    parsed_options = df["옵션정보"].apply(parse_naver_option)
    parsed_df = pd.DataFrame(parsed_options.tolist())

    intermediate = pd.DataFrame(
        {
            "상품주문번호": df["상품주문번호"],
            "수취인명": df["수취인명"],
            "수취인연락처1": df["수취인연락처1"],
            "통합배송지": df["통합배송지"],
            "배송메세지": df["배송메세지"],
            "수량": df["수량"],
            "옵션관리코드": df["옵션관리코드"],
            "보내시는분": parsed_df["보내시는분"],
            "도착희망날짜_원본": parsed_df["도착희망날짜_원본"],
            "도착희망날짜_정규화": "",
            "과일선물옵션": parsed_df["과일선물옵션"],
        }
    )

    return intermediate


def normalize_dates_batch(
    intermediate_df: pd.DataFrame,
    api_key: str,
    progress_callback: Callable[[int, int], Any] | None = None,
    debug_callback: Callable[[str, Any], Any] | None = None,
) -> pd.DataFrame:
    """Normalize arrival date values in batches using AI."""
    result_df = intermediate_df.copy()

    unique_dates = result_df["도착희망날짜_원본"].dropna().unique().tolist()

    if not unique_dates:
        return result_df

    if debug_callback:
        debug_callback("info", f"📊 추출된 유니크 날짜: {len(unique_dates)}개")
        debug_callback("unique_dates", unique_dates[:10])

    date_mapping = {}
    batch_size = 50
    total_batches = (len(unique_dates) + batch_size - 1) // batch_size

    for batch_idx in range(total_batches):
        start_idx = batch_idx * batch_size
        end_idx = min((batch_idx + 1) * batch_size, len(unique_dates))
        batch = unique_dates[start_idx:end_idx]

        if debug_callback:
            debug_callback("batch_start", f"배치 {batch_idx + 1}/{total_batches} - {len(batch)}개 날짜 처리 중...")

        batch_mapping = normalize_dates_batch_with_ai(api_key, batch)

        if debug_callback:
            debug_callback("batch_result", {"batch_idx": batch_idx + 1, "mapping": batch_mapping})

        date_mapping.update(batch_mapping)

        if progress_callback:
            progress_callback(batch_idx + 1, total_batches)

    result_df["도착희망날짜_정규화"] = result_df["도착희망날짜_원본"].map(date_mapping).fillna("")

    return result_df


def _is_valid_date(date_str: str) -> bool:
    """Check if a string is a valid MM/DD format date."""
    if pd.isna(date_str) or not date_str:
        return False
    date_str = str(date_str).strip()
    # MM/DD 또는 M/D 또는 MM/D 또는 M/DD 형식인지 확인
    pattern = r'^\d{1,2}/\d{1,2}$'
    return bool(re.match(pattern, date_str))


def _create_sort_key(row):
    """Create a sort key for ordering: invalid dates first, then by date, then by option code."""
    date_str = str(row["도착희망날짜_정규화"]).strip()
    option_code = str(row["옵션관리코드"]).strip()

    # 날짜가 유효하지 않으면 (0, date_str, option_code)로 정렬 -> 가장 위로
    if not _is_valid_date(date_str):
        return (0, date_str, option_code)

    # 날짜가 유효하면 (1, 월, 일, option_code)로 정렬
    try:
        parts = date_str.split('/')
        month = int(parts[0])
        day = int(parts[1])
        return (1, month, day, option_code)
    except:
        # 파싱 실패시 날짜 불분명으로 처리
        return (0, date_str, option_code)


def generate_cj_orders_by_date(intermediate_df: pd.DataFrame, defaults: dict[str, str]) -> dict:
    """Create a single CJ order file with all dates, sorted by date validity, then date, then option code."""
    import datetime as dt

    # 품목명에 날짜 추가: 보내시는분 + "드림 " + 옵션관리코드 + " " + 날짜
    qty = pd.to_numeric(intermediate_df["수량"], errors="coerce").fillna(0).astype(int)

    item_name = (
        intermediate_df["보내시는분"].fillna("OOO").astype(str)
        + "드림 "
        + intermediate_df["옵션관리코드"].fillna("").astype(str)
        + " "
        + intermediate_df["도착희망날짜_정규화"].fillna("").astype(str)
    )

    cj_df = pd.DataFrame(
        {
            "보내는분성명": defaults["name"],
            "보내는분전화번호": defaults["phone"],
            "보내는분주소(전체,분할)": defaults["address"],
            "운임구분": "신용",
            "박스타입": "극소",
            "기본운임": qty * 2200,
            "고객주문번호": intermediate_df["상품주문번호"],
            "품목명": item_name,
            "수량": qty,
            "수취인이름": intermediate_df["수취인명"],
            "수취인전화번호": intermediate_df["수취인연락처1"],
            "수취인 주소": intermediate_df["통합배송지"],
            "배송메세지": intermediate_df["배송메세지"],
            "도착희망날짜_정규화": intermediate_df["도착희망날짜_정규화"],  # 정렬용
            "옵션관리코드": intermediate_df["옵션관리코드"],  # 정렬용
        }
    )

    # 정렬: 1) 날짜 불분명한 것 위로, 2) 날짜순, 3) 옵션관리코드순
    cj_df['__sort_key'] = cj_df.apply(_create_sort_key, axis=1)
    cj_df = cj_df.sort_values('__sort_key').reset_index(drop=True)

    # 정렬에 사용한 임시 컬럼 제거
    cj_df = cj_df.drop(columns=['__sort_key', '도착희망날짜_정규화', '옵션관리코드'])

    buf = io.BytesIO()
    cj_df.to_excel(buf, index=False)
    buf.seek(0)

    # 파일명에 오늘 날짜 포함
    today = dt.datetime.now().strftime("%y%m%d")
    filename = f"네이버_CJ발주서_{today}.xlsx"

    results = {
        "single": {
            "df": cj_df,
            "data": buf.getvalue(),
            "count": len(cj_df),
            "filename": filename
        }
    }

    return results


def get_naver_bulk_columns() -> list[str]:
    """Column order for Naver bulk upload."""
    from pathlib import Path

    example_path = Path("output/example/naver/네이버 대량등록.xlsx")
    fallback = ["상품주문번호", "배송방법", "택배사", "송장번호"]
    if example_path.exists():
        try:
            cols = list(pd.read_excel(example_path, nrows=0).columns)
            if cols:
                return cols
        except Exception:
            pass
    return fallback


def build_naver_bulk(raw_df: pd.DataFrame, cj_df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Merge Naver raw data with CJ receipt details to create bulk upload file.

    Returns:
        tuple: (output_df, debug_info)
    """
    raw_df = clean_columns(raw_df).copy()
    cj_df = clean_columns(cj_df).copy()

    # Normalize order numbers for matching
    raw_df["__key"] = raw_df["상품주문번호"].apply(_normalize_order)
    key_col = "고객주문번호" if "고객주문번호" in cj_df.columns else "주문번호"
    cj_df["__key"] = cj_df[key_col].apply(_normalize_order)

    # Collect debug info
    debug_info = {
        "raw_count": len(raw_df),
        "cj_count": len(cj_df),
        "key_col": key_col,
        "raw_samples": [],
        "cj_samples": [],
    }

    for i in range(min(5, len(raw_df))):
        original = raw_df.iloc[i]["상품주문번호"]
        normalized = raw_df.iloc[i]["__key"]
        debug_info["raw_samples"].append({
            "original": str(original),
            "type": type(original).__name__,
            "normalized": normalized
        })

    for i in range(min(5, len(cj_df))):
        original = cj_df.iloc[i][key_col]
        normalized = cj_df.iloc[i]["__key"]
        invoice = cj_df.iloc[i].get("운송장번호", "")
        debug_info["cj_samples"].append({
            "original": str(original),
            "type": type(original).__name__,
            "normalized": normalized,
            "invoice": str(invoice) if pd.notna(invoice) else ""
        })

    # CJ 파일에 운송장번호 컬럼이 있는지 확인
    debug_info["has_invoice_col"] = "운송장번호" in cj_df.columns

    # Merge - 운송장번호 컬럼이 있으면 포함, 없으면 __key만 사용
    merge_cols = ["__key"]
    if "운송장번호" in cj_df.columns:
        merge_cols.append("운송장번호")

    merged = raw_df.merge(
        cj_df[merge_cols],
        on="__key",
        how="left",
        suffixes=("", "_cj"),
    )

    # Debug: Check match results
    matched_count = merged["운송장번호"].notna().sum() if "운송장번호" in merged.columns else 0
    if "운송장번호_cj" in merged.columns:
        matched_count = merged["운송장번호_cj"].notna().sum()

    debug_info["matched_count"] = matched_count
    debug_info["total_count"] = len(merged)

    # Show unmatched items
    if matched_count < len(merged):
        unmatched_mask = merged["운송장번호_cj"].isna() if "운송장번호_cj" in merged.columns else merged["운송장번호"].isna()
        unmatched = merged[unmatched_mask]["__key"].unique().tolist()
        debug_info["unmatched"] = unmatched[:10]
        debug_info["unmatched_count"] = len(unmatched)

        # Check if these keys exist in CJ file
        cj_keys = set(cj_df["__key"].unique())
        debug_info["cj_keys_sample"] = list(cj_keys)[:10]

    # 송장번호 처리: CJ 파일에서 가져온 운송장번호 사용
    if "운송장번호_cj" in merged:
        merged["__송장"] = merged["운송장번호_cj"]
    elif "운송장번호" in merged:
        merged["__송장"] = merged["운송장번호"]
    elif "송장번호" in merged:
        merged["__송장"] = merged["송장번호"]
    else:
        merged["__송장"] = ""

    # 송장번호 정규화 (NaN을 빈 문자열로, 숫자를 문자열로 변환)
    merged["__송장"] = merged["__송장"].apply(_normalize_order)

    def pick(col, default=""):
        """컬럼이 없거나 값이 비어있으면 default 반환"""
        if col not in merged.columns:
            return default
        # 컬럼은 있지만 모든 값이 비어있으면 default 반환
        col_data = merged[col].fillna("")
        if col_data.astype(str).str.strip().eq("").all():
            return default
        return merged[col]

    output_cols = get_naver_bulk_columns()
    data = {
        "상품주문번호": merged["__key"],
        "배송방법": pick("배송방법", "택배"),
        "택배사": "CJ 대한통운",  # 항상 CJ 대한통운으로 설정
        "송장번호": merged["__송장"],
    }

    output = pd.DataFrame(data)
    output = output[output_cols]

    # 상품주문번호 중복 제거 (첫 번째 행만 유지)
    output = output.drop_duplicates(subset=['상품주문번호'], keep='first')

    return output, debug_info


def build_naver_cj(df: pd.DataFrame, defaults: dict[str, str]) -> pd.DataFrame:
    """Transform Naver raw data into CJ order format."""
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

    qty = pd.to_numeric(df["수량"], errors="coerce").fillna(0).astype(int)
    item_name = "OOO드림 " + df["옵션관리코드"].fillna("").astype(str)
    order_no = df["상품주문번호"].apply(_normalize_order)

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
