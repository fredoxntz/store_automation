import io
import pandas as pd
import streamlit as st


def read_excel_with_password(file, password=None, **kwargs):
    """
    비밀번호로 보호된 엑셀 파일을 읽습니다.

    Args:
        file: 업로드된 파일 객체 또는 파일 경로
        password: 엑셀 파일 비밀번호 (선택사항)
        **kwargs: pd.read_excel에 전달할 추가 인자 (예: header=1)

    Returns:
        pandas.DataFrame: 엑셀 데이터
    """
    if password:
        try:
            import msoffcrypto

            # 파일 객체를 BytesIO로 변환
            file.seek(0)
            encrypted = io.BytesIO(file.read())
            decrypted = io.BytesIO()

            # 비밀번호로 파일 복호화
            office_file = msoffcrypto.OfficeFile(encrypted)
            office_file.load_key(password=password)
            office_file.decrypt(decrypted)

            # 복호화된 파일을 pandas로 읽기
            decrypted.seek(0)
            return pd.read_excel(decrypted, **kwargs)

        except ImportError:
            st.error("비밀번호 보호된 파일을 읽으려면 msoffcrypto-tool 라이브러리가 필요합니다.")
            st.code("pip install msoffcrypto-tool", language="bash")
            raise
        except Exception as e:
            st.error(f"파일 복호화 중 오류가 발생했습니다: {str(e)}")
            st.info("비밀번호가 올바른지 확인해주세요.")
            raise
    else:
        # 비밀번호가 없으면 일반적인 방법으로 읽기
        file.seek(0)
        return pd.read_excel(file, **kwargs)


def render_password_input(key_prefix, label="파일 비밀번호 (선택사항)"):
    """
    비밀번호 입력 필드를 렌더링합니다.

    Args:
        key_prefix: Streamlit 위젯의 고유 키 접두사
        label: 입력 필드 레이블

    Returns:
        str: 입력된 비밀번호 (없으면 None)
    """
    with st.expander("🔒 파일에 비밀번호가 걸려있나요?"):
        password = st.text_input(
            label,
            type="password",
            key=f"{key_prefix}_password",
            help="엑셀 파일에 비밀번호가 설정되어 있다면 입력하세요.",
        )
        return password if password else None
