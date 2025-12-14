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
다음 JSON 배열의 각 날짜 텍스트를 YYYY-MM-DD 형식으로 변환해주세요.
날짜 정보가 불확실하다고 판단될때는 인풋에 있는 날짜 정보를 참고해서 변환하세요. 
변환하는 날짜들은 비슷한 시점입니다.
10월 1일 또는 2일 이런 날짜는 10월 1일로 변환하세요.
9월 30일 또는 10월 1일 이런 날짜는 9월 30일로 변환하세요.
10월 2일 는 2025-10-02 이런식으로
명확한 날짜가 아닌경우는 변환하지 말고 그대로 다시 변환결과에 넣어줘.

입력: {dates_json}

출력은 반드시 "원본": "변환결과" 형태의 JSON 객체로만 답변하세요. 설명은 하지 마세요.
예시: {{"9월30일": "2025-09-30", "10/1": "2025-10-01", "최대한 빨리": "빠른배송"}}
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


def generate_cj_orders_by_date(intermediate_df: pd.DataFrame, defaults: dict[str, str]) -> dict:
    """Create CJ order files grouped by normalized date."""
    grouped = intermediate_df.groupby("도착희망날짜_정규화")

    results = {}

    for date, group in grouped:
        qty = pd.to_numeric(group["수량"], errors="coerce").fillna(0).astype(int)
        item_name = group["보내시는분"].fillna("OOO").astype(str) + "드림 " + group["옵션관리코드"].fillna("").astype(str)

        cj_df = pd.DataFrame(
            {
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
            }
        )

        buf = io.BytesIO()
        cj_df.to_excel(buf, index=False)
        buf.seek(0)

        results[date] = {"df": cj_df, "data": buf.getvalue(), "count": len(cj_df)}

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


def build_naver_bulk(raw_df: pd.DataFrame, cj_df: pd.DataFrame) -> pd.DataFrame:
    """Merge Naver raw data with CJ receipt details to create bulk upload file."""
    raw_df = clean_columns(raw_df).copy()
    cj_df = clean_columns(cj_df).copy()

    # Normalize order numbers for matching
    raw_df["__key"] = raw_df["상품주문번호"].apply(_normalize_order)
    key_col = "고객주문번호" if "고객주문번호" in cj_df.columns else "주문번호"
    cj_df["__key"] = cj_df[key_col].apply(_normalize_order)

    # Debug: Print sample keys for debugging
    print("\n[DEBUG] 네이버 대량등록 매칭 디버깅:")
    print(f"- 로우데이터 총 {len(raw_df)}건")
    print(f"- CJ 파일 총 {len(cj_df)}건")
    print(f"- CJ 파일에서 사용한 키 컬럼: {key_col}")
    print("\n로우데이터 상품주문번호 샘플 (정규화 전 -> 후):")
    for i in range(min(5, len(raw_df))):
        original = raw_df.iloc[i]["상품주문번호"]
        normalized = raw_df.iloc[i]["__key"]
        print(f"  {i+1}. '{original}' (타입: {type(original).__name__}) -> '{normalized}'")
    print("\nCJ 파일 고객주문번호 샘플 (정규화 전 -> 후):")
    for i in range(min(5, len(cj_df))):
        original = cj_df.iloc[i][key_col]
        normalized = cj_df.iloc[i]["__key"]
        print(f"  {i+1}. '{original}' (타입: {type(original).__name__}) -> '{normalized}'")

    # Merge
    merged = raw_df.merge(
        cj_df[["__key", "운송장번호"]],
        on="__key",
        how="left",
        suffixes=("", "_cj"),
    )

    # Debug: Check match results
    matched_count = merged["운송장번호"].notna().sum() if "운송장번호" in merged.columns else 0
    if "운송장번호_cj" in merged.columns:
        matched_count = merged["운송장번호_cj"].notna().sum()

    print(f"\n매칭 결과: {matched_count}/{len(merged)}건 매칭됨")

    # Show unmatched items
    if matched_count < len(merged):
        unmatched_mask = merged["운송장번호_cj"].isna() if "운송장번호_cj" in merged.columns else merged["운송장번호"].isna()
        unmatched = merged[unmatched_mask]["__key"].unique()
        print(f"\n매칭 안 된 주문번호 ({len(unmatched)}개):")
        for i, key in enumerate(unmatched[:10]):
            print(f"  {i+1}. '{key}'")
        if len(unmatched) > 10:
            print(f"  ... 외 {len(unmatched) - 10}개")

        # Check if these keys exist in CJ file
        cj_keys = set(cj_df["__key"].unique())
        print("\nCJ 파일에 있는 키 샘플 (최대 10개):")
        for i, key in enumerate(list(cj_keys)[:10]):
            print(f"  {i+1}. '{key}'")

    if "운송장번호_cj" in merged:
        merged["__송장"] = merged["운송장번호_cj"].fillna(merged.get("송장번호"))
    else:
        merged["__송장"] = merged.get("송장번호")
    merged["__송장"] = merged["__송장"].apply(_normalize_order)

    def pick(col, default=""):
        return merged[col] if col in merged.columns else default

    output_cols = get_naver_bulk_columns()
    data = {
        "상품주문번호": merged["__key"],
        "배송방법": pick("배송방법", "택배"),
        "택배사": pick("택배사", "CJ대한통운"),
        "송장번호": merged["__송장"],
    }

    output = pd.DataFrame(data)
    output = output[output_cols]
    return output


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
