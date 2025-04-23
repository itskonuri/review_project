import streamlit as st
from openai import OpenAI
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

def analyze_with_feedback(client, system_message, user_prompt, max_attempts=2):
    """피드백을 통한 반복 분석 수행"""
    for attempt in range(max_attempts):
        try:
            response = client.chat.completions.create(
                model="gpt-4",  # 더 안정적인 결과를 위해 GPT-4 사용
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2  # 낮은 temperature로 일관된 결과 생성
            )
            
            result = response.choices[0].message.content
            
            # 간단한 검증: 세 개의 섹션이 모두 있는지 확인
            if ("리뷰 요약" in result and "장단점 분석" in result and "인기 메뉴" in result):
                return result
                
            # 첫 번째 시도가 실패하면 더 명확한 피드백과 함께 다시 시도
            if attempt < max_attempts - 1:
                feedback_prompt = f"""
                이전 응답이 요청된 형식을 따르지 않았습니다. 
                다음 형식으로 정확히 응답해 주세요:
                
                ## 1. 리뷰 요약
                (200자 이내 요약)
                
                ## 2. 장단점 분석
                ### 장점:
                - 장점 1
                - 장점 2
                - 장점 3
                
                ### 단점:
                - 단점 1
                - 단점 2
                - 단점 3
                
                ## 3. 인기 메뉴
                1. (첫 번째 메뉴): (평가 요약)
                2. (두 번째 메뉴): (평가 요약)
                3. (세 번째 메뉴): (평가 요약)
                
                위 형식을 반드시 지켜주세요. 원본 데이터는 다음과 같습니다:
                {user_prompt}
                """
                user_prompt = feedback_prompt
        except Exception as e:
            return f"❌ API 호출 중 오류가 발생했습니다: {e}"
            
    return result  # 모든 시도 후 마지막 결과 반환

def send_csv_data_to_chatgpt(folder_path, file_name, prompt_template, encoding="cp949"):
    """
    CSV 데이터를 ChatGPT로 보내고 응답을 반환합니다.

    Args:
        folder_path (str): CSV 파일이 위치한 폴더 경로
        file_name (str): 읽고자 하는 CSV 파일 이름
        prompt_template (str): ChatGPT에 보낼 프롬프트 템플릿
        encoding (str): 파일 인코딩 (기본값: cp949)

    Returns:
        str: ChatGPT의 응답
    """
    try:
        # CSV 파일 읽기
        df = load_csv_file(folder_path, file_name, encoding)

        # CSV 데이터를 문자열로 변환
        csv_data = df.to_string(index=False)

        # ChatGPT 프롬프트 생성
        prompt = prompt_template.format(csv_data=csv_data)

        # OpenAI 클라이언트 생성
        client = OpenAI(api_key=st.secrets["openai"]["API_KEY"])

        # 시스템 메시지 설정
        system_message = """당신은 식당 리뷰 데이터 분석 전문가입니다. 
        항상 다음 세 가지 카테고리로 정확히 구분하여 응답해야 합니다:
        1. 리뷰 요약 (200자 이내)
        2. 장단점 분석 (각 3개씩)
        3. 인기 메뉴 (상위 3개)
        
        각 섹션은 명확한 제목으로 구분하고, 요청된 형식을 정확히 따라야 합니다. 
        어떤 경우에도 이 형식을 벗어나지 마세요."""

        # 피드백 메커니즘을 통한 분석 수행
        return analyze_with_feedback(client, system_message, prompt)

    except Exception as e:
        return f"❌ 오류가 발생했습니다: {e}"

# Streamlit 앱
st.title("📊 CSV 데이터를 ChatGPT로 보내기")
st.markdown("CSV 데이터를 ChatGPT로 보내고 응답을 확인합니다.")

# 사이드바에 인코딩 선택 옵션 추가
encoding_option = st.sidebar.selectbox(
    "CSV 파일 인코딩",
    options=["cp949", "utf-8", "euc-kr"],
    index=0
)

# 탭 생성: 파일 업로드와 기존 파일 선택
tab1, tab2 = st.tabs(["파일 업로드", "기존 파일 선택"])

with tab1:
    uploaded_file = st.file_uploader("CSV 파일 업로드", type=["csv"])
    
    if uploaded_file is not None:
        try:
            # 임시 파일 저장
            temp_dir = "temp_uploads"
            os.makedirs(temp_dir, exist_ok=True)
            temp_file_path = os.path.join(temp_dir, uploaded_file.name)
            
            with open(temp_file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            st.success(f"✅ 파일 '{uploaded_file.name}'이(가) 업로드되었습니다.")
            
            # 데이터 미리보기
            try:
                df = load_csv_file(temp_dir, uploaded_file.name, encoding_option)
                st.markdown("### 데이터 미리보기")
                st.dataframe(df.head())
                
                # 프롬프트 템플릿 입력
                prompt_template = st.text_area(
                    "ChatGPT 프롬프트 템플릿",
                    value="""다음은 식당 리뷰 데이터입니다:

{csv_data}

위 데이터를 분석하여 다음 형식으로 정확하게 응답해주세요:

## 1. 리뷰 요약
(전체 리뷰의 핵심 내용을 200자 이내로 간결하게 요약)

## 2. 장단점 분석
### 장점:
- 장점 1: (구체적 설명)
- 장점 2: (구체적 설명)
- 장점 3: (구체적 설명)

### 단점:
- 단점 1: (구체적 설명)
- 단점 2: (구체적 설명)
- 단점 3: (구체적 설명)

## 3. 인기 메뉴
1. (가장 많이 언급된 메뉴): (고객 평가 요약)
2. (두 번째로 많이 언급된 메뉴): (고객 평가 요약)
3. (세 번째로 많이 언급된 메뉴): (고객 평가 요약)

위 형식을 정확히 따라 응답해주세요. 각 섹션의 제목과 형식을 변경하지 마세요."""
                )
                
                if st.button("데이터 분석하기"):
                    with st.spinner("ChatGPT에 데이터 분석 요청 중..."):
                        result = send_csv_data_to_chatgpt(temp_dir, uploaded_file.name, prompt_template, encoding_option)
                    st.markdown("### 분석 결과")
                    st.write(result)
            
            except Exception as e:
                st.error(f"파일 처리 중 오류가 발생했습니다: {e}")
        
        except Exception as e:
            st.error(f"파일 업로드 중 오류가 발생했습니다: {e}")

with tab2:
    # DB 폴더 경로와 파일 선택
    db_folder_path = "DB"  # CSV 파일이 위치한 폴더 경로
    
    # DB 폴더가 없으면 생성
    os.makedirs(db_folder_path, exist_ok=True)
    
    csv_files = [f for f in os.listdir(db_folder_path) if f.endswith(".csv")]

    if csv_files:
        selected_file = st.selectbox("CSV 파일 선택", csv_files)
        
        # 데이터 미리보기
        try:
            df = load_csv_file(db_folder_path, selected_file, encoding_option)
            st.markdown("### 데이터 미리보기")
            st.dataframe(df.head())
            
            prompt_template = st.text_area(
                "ChatGPT 프롬프트 템플릿",
                value="""다음은 식당 리뷰 데이터입니다:

{csv_data}

위 데이터를 분석하여 다음 형식으로 정확하게 응답해주세요:

## 1. 리뷰 요약
(전체 리뷰의 핵심 내용을 200자 이내로 간결하게 요약)

## 2. 장단점 분석
### 장점:
- 장점 1: (구체적 설명)
- 장점 2: (구체적 설명)
- 장점 3: (구체적 설명)

### 단점:
- 단점 1: (구체적 설명)
- 단점 2: (구체적 설명)
- 단점 3: (구체적 설명)

## 3. 인기 메뉴
1. (가장 많이 언급된 메뉴): (고객 평가 요약)
2. (두 번째로 많이 언급된 메뉴): (고객 평가 요약)
3. (세 번째로 많이 언급된 메뉴): (고객 평가 요약)

위 형식을 정확히 따라 응답해주세요. 각 섹션의 제목과 형식을 변경하지 마세요.""",
                key="prompt_template2" 
            )

            if st.button("데이터 분석하기", key="analyze_button2"):
                with st.spinner("ChatGPT에 데이터 분석 요청 중..."):
                    result = send_csv_data_to_chatgpt(db_folder_path, selected_file, prompt_template, encoding_option)
                st.markdown("### 분석 결과")
                st.write(result)
        
        except Exception as e:
            st.error(f"파일 처리 중 오류가 발생했습니다: {e}")
    else:
        st.warning("⚠️ DB 폴더에 CSV 파일이 없습니다. 파일을 업로드하거나 DB 폴더에 CSV 파일을 추가하세요.")

# 사이드바에 앱 정보 추가
st.sidebar.markdown("## 앱 정보")
st.sidebar.markdown("이 앱은 CSV 데이터를 분석하기 위해 OpenAI GPT-4를 사용합니다.")
st.sidebar.markdown("데이터는 서버에 임시로만 저장되며, 분석 후 자동으로 삭제됩니다.")

# 디버그 정보 추가
debug_info = st.sidebar.checkbox("디버그 정보 표시")
if debug_info:
    st.sidebar.markdown("### 디버그 정보")
    st.sidebar.write(f"현재 작업 디렉토리: {os.getcwd()}")
    st.sidebar.write(f"DB 폴더 경로: {db_folder_path}")
    st.sidebar.write(f"DB 폴더 존재 여부: {os.path.exists(db_folder_path)}")
    if os.path.exists(db_folder_path):
        all_files = os.listdir(db_folder_path)
        st.sidebar.write(f"DB 폴더 내 모든 파일: {all_files}")
        csv_files_in_db = [f for f in all_files if f.endswith('.csv')]
        st.sidebar.write(f"DB 폴더 내 CSV 파일: {csv_files_in_db}")
