from pathlib import Path

import pandas as pd


def get_sender_defaults() -> dict[str, str]:
    """Sender defaults read from example CJ file if available."""
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


def get_coupang_bulk_columns() -> list[str]:
    """Column order for Coupang bulk upload."""
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
    """Trim whitespace in column names to avoid merge mismatches."""
    return df.rename(columns=lambda c: str(c).strip())


def _normalize_order(value):
    if pd.isna(value):
        return ""
    if isinstance(value, float):
        return str(int(value))
    if isinstance(value, int):
        return str(value)
    s = str(value).strip()
    if s.endswith(".0") and s.replace(".", "", 1).isdigit():
        try:
            return str(int(float(s)))
        except Exception:
            return s
    return s


def build_coupang_cj(df: pd.DataFrame, defaults: dict[str, str]) -> pd.DataFrame:
    """Transform Coupang raw data into CJ order format."""
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

    qty = pd.to_numeric(df["구매수(수량)"], errors="coerce").fillna(0).astype(int)
    item_name = df["구매자"].fillna("").astype(str) + "드림 " + df["업체상품코드"].fillna("").astype(str)
    order_no = df["주문번호"].apply(_normalize_order)

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


def build_coupang_bulk(raw_df: pd.DataFrame, cj_df: pd.DataFrame) -> pd.DataFrame:
    """Merge Coupang raw data with CJ receipt details to prepare bulk upload."""
    raw_df = clean_columns(raw_df)
    cj_df = clean_columns(cj_df)

    raw_df = raw_df.copy()
    cj_df = cj_df.copy()

    raw_df["__key"] = raw_df["주문번호"].apply(_normalize_order)
    key_col = "고객주문번호" if "고객주문번호" in cj_df.columns else "주문번호"
    cj_df["__key"] = cj_df[key_col].apply(_normalize_order)

    merged = raw_df.merge(
        cj_df[["__key", "운송장번호", "집화예정일자"]],
        on="__key",
        how="left",
        suffixes=("", "_cj"),
    )

    if "운송장번호_cj" in merged:
        merged["__운송장번호"] = merged["운송장번호_cj"].fillna(merged.get("운송장번호"))
    else:
        merged["__운송장번호"] = merged.get("운송장번호")
    merged["__운송장번호"] = merged["__운송장번호"].apply(_normalize_order)

    def pick(col, default=""):
        return merged[col] if col in merged.columns else default

    output_cols = get_coupang_bulk_columns()

    data = {
        "번호": pick("번호"),
        "묶음배송번호": pick("묶음배송번호"),
        "주문번호": pick("주문번호").apply(_normalize_order),
        "택배사": "CJ대한통운",
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
    output = output[output_cols]
    return output
