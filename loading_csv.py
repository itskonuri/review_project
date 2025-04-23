import pandas as pd
import os

def load_csv_file(folder_path, file_name, encoding="cp949"):
    """
    특정 폴더에서 지정된 CSV 파일을 읽어 데이터프레임으로 반환합니다.

    Args:
        folder_path (str): CSV 파일이 위치한 폴더 경로
        file_name (str): 읽고자 하는 CSV 파일 이름
        encoding (str): 파일 인코딩 (기본값: cp949)

    Returns:
        pd.DataFrame: 읽은 CSV 파일의 데이터프레임
    """
    file_path = os.path.join(folder_path, file_name)

    if os.path.exists(file_path):
        try:
            # CSV 파일 읽기
            df = pd.read_csv(file_path, encoding=encoding, engine="python")
            return df
        except Exception as e:
            raise ValueError(f"❌ 파일 '{file_name}'을 읽는 중 오류가 발생했습니다: {e}")
    else:
        raise FileNotFoundError(f"❌ 파일 '{file_name}'이(가) '{folder_path}' 폴더에 존재하지 않습니다.")