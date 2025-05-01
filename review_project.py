import json
import re
import streamlit as st
import pandas as pd
import openai
import os
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import pandas as pd
from datetime import datetime, timedelta
import time

# Load API key securely
load_dotenv()
# client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
openai.api_key = os.getenv("OPENAI_API_KEY")


# 앱 제목
st.title("음식점 리뷰 요약 서비스 🍽️")

# 파일 업로드
url=st.text_input('리뷰를 분석할 식당의 리뷰URL을 입력하세요')

if st.button('시작'):
    if url:
        chrome_options=Options() #Options 객체 설정. 이거 안하면 실행 안됨.
        chrome_options.add_argument("--headless") #창 열지 않음
        chrome_options.add_argument("--no-sandbox") #샌드박스 모드는 브라우저 프로세스를 격리하여 보안을 강화하는 기능. chrome실행에 필요
        chrome_options.add_argument("--disable-dev-shm-usage")  #가상환경에서 실행시 메모리부족으로 chrome에서 실행이 실패, 충돌할 수 있어 내 컴퓨터 디스크에 임시파일을 저장하여 공유하는 방식
        chrome_options.add_argument("--disable-gpu")    #gpu가속 비활성화. 헤드리스모드 실행할 때 발생할 수 있는 문제 해결
        chrome_options.add_argument("--window-size=1920,1080")  #chrome창 크기 설정
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
#사용자 에이전트 설정. 사이트 마다 다름. 위는 chrome의 사용자 에이전트.Mozilla/[버전] ([운영 체제 및 하드웨어 정보]) [렌더링 엔진] ([엔진 정보]) [브라우저 정보]

        driver=webdriver.Chrome(options=chrome_options)     #chrome브라우저 실행. driver이 있어야 브라우저 제어, 실행 가능.


        driver.get(url)

        WebDriverWait(driver,10).until(
            EC.presence_of_element_located((By.ID,"entryIframe"))
        )
#WebDriverWait(driver,10)은 주어진 시간동안 조건이 충족될 떄까지 브라우저 기다림.
#presence_of_element_located는 EC(expected conditions)에서 제공하는 조건 중 하나. 특정 요소가 DOM(document object model)에 존재하는지 확인
#요소가 존재하면 True 반환. 그렇지 않으면 TimeoutException발생.
#iframe은 html문서 안에 다른 html문서를 삽입할 수 있는 요소. 광고배너나 외부콘텐츠.
#iframe을 다루려면 프레임 전환 필요.  iframe내부의 요소에 접근하려면 먼저 해당 iframe으로 전환
        driver.switch_to.frame("entryIframe")

        try:
            latest_button=WebDriverWait(driver,10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR,"a.ScBz5"))#튜플이어야함. 이 함수가 받는 두 인자.
            )   #특정 요소가 클릭 가능하면 True반환. 아니면 TimeoutException.
                #until: WebDriverWait클레스에서 사용되는 메서드. until메서드와 함께쓰면 클릭가능할때까지 기다렸다가 클릭 가능해지면 해당 요소 값을 저장.
            latest_button.click()
            print("최신순 버튼 클릭 완료")
            time.sleep(2)
        except Exception as e:
            print(f"최신순 버튼 클릭 중 오류 발생 : {e}")
        except TimeoutException:
            print("시간 초과. 최신순버튼")

        for i in range(50):
            try:
                more_button=WebDriverWait(driver,10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR,"a.fvwqf"))
                )
        
                driver.execute_script("arguments[0].click();", more_button)
                #driver.execute_script메서드를 사용하여 javascript 코드 실행
                print('click!')
                time.sleep(2)
            except NoSuchElementException:
                print("더 이상 더보기 버튼 없음")
                break
            except TimeoutException:
                print("시간 초과")
                break

        def format_date(raw_date):
# 
#  날짜 포맷 변환
#  초기 형식: 'yy.mm.dd.요일'
# 형식 변환: 'yy-mm'

# 해당연도인 경우: 'mm.dd.요일'
# 
#        
            current_year=25 #연도가 없는 경우 현재 연도
            try:
                if'.' in raw_date:
                    parts=raw_date.split('.')   #날짜를 '.'기준으로 분리
                    if len(parts)==3:   #'mm.dd.요일'
                        month=parts[0]
                        formatted_date=datetime.strptime(f"{current_year}.{month}","%y.%m").strftime("%y-%m")
                    elif len(parts)==4:     #'yy.mm.dd.요일'
                        year,month=parts[:2]
                        formatted_date=datetime.strptime(f"{year}.{month}","%y.%m").strftime("%y-%m")
                
                    return formatted_date
                print(f"잘못된 날짜: {raw_date}")
                return None
            except Exception as e:
                print(f"날짜 변환 실패({raw_date}): {e}")
                return None

        reviews=[]
        try:
            review_elements=WebDriverWait(driver,30).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR,"div.pui__vn15t2"))
            )   #리뷰 수집
            date_elements=driver.find_elements(By.CSS_SELECTOR,"time[aria-hidden='true']")
        #날짜 수집
            for review_element,date_element in zip(review_elements,date_elements):
                review_text= review_element.text.strip()
                review_date = date_element.text.strip()
        #텍스트 추출.
                if review_text and review_date:  #리뷰와 날짜 모두 값이 있을 때
                    formatted_date= format_date(review_date)    #format_data함수
                    if formatted_date:
                        reviews.append({"Review":review_text.replace("더보기","").strip(),"Date":formatted_date})
        except Exception as e:
            print(f"리뷰 수집 중 오류 발생: {e}")
        print(f"총 {len(reviews)}개의 리뷰를 수집했습니다.")

        recent_date_limit=datetime.now()-timedelta(days=8*30)
#8개월 전 날짜
        filtered_reviews=[
            review for review in reviews if datetime.strptime(review["Date"],"%y-%m")>=recent_date_limit
        ]
#8개월 전 날짜 이후 리뷰들 리스트에 저장

        reviews_by_month={}
        for review in filtered_reviews:
            review_date=datetime.strptime(review["Date"],"%y-%m")
            month=review_date.strftime("%y-%m")
            if month not in reviews_by_month:
                reviews_by_month[month]=[]
            reviews_by_month[month].append(review)
#월별로 분류

        final_reviews=[]
        while len(final_reviews) < 100:
            if len(reviews_by_month) <30:
                final_reviews=filtered_reviews
                break
            for month,month_reviews in reviews_by_month.items():
                if month_reviews and len(final_reviews)<30:
                    final_reviews.append(month_reviews.pop(0))
                if len(final_reviews) >= 100:
                    break
    
        filename=driver.find_element(By.CSS_SELECTOR,"span.GHAhO").text.strip()
        df=pd.DataFrame(reviews)
        df.to_csv(f"{filename}.csv",index=False,encoding="utf-8-sig")
        print(f"{filename}에 리뷰 저장 완료!")

# 파일 읽기
    with open(f"{filename}.csv", 'r', encoding="utf-8") as file:
        reviews = file.read()

# # GPT에게 리뷰 정리 요청
#     response = openai.chat.completions.create(
#     engine="gpt-3.5-turbo",
#     prompt=f"다음 리뷰를 읽고 식당의 3가지 장단점과 인기 있는 메뉴를 정리해줘:\n\n{reviews}",
#     )

# # 결과 표시
#     st.write(response.choices[0].text.strip())

### 프롬프트 설정
    prompt = f"""
    다음 리뷰를 분석해서 아래 JSON 형식으로 출력해줘.

    - advantages, disadvantages는 각각 3개의 **구체적인 문장**으로 작성해줘.
    - popular_menu는 리뷰에 가장많이 언급된 인기 메뉴 3가지를 뽑아줘.
    - rating은 0.0에서 5.0 사이로 정수 또는 소수점 첫째 자리까지 표현해줘.
    - rating은 **긍정 리뷰 비율**, **리뷰 수**, **감정의 강도**, **문맥의 전체 분위기**를 기준으로 판단해줘.
    - 단, 별점 추정 시 "너무 낙관적으로 판단하지 말고", **엄격하고 신중하게** 평가해줘.
    - JSON 형식만 출력하고 다른 설명은 하지 마.

    출력 형식:
    {{
    "advantages": ["문장1", "문장2", "문장3"],
    "disadvantages": ["문장1", "문장2", "문장3"],
    "popular_menu": ["메뉴1", "메뉴2", "메뉴3"],
    "rating": 4.3
    }}

    리뷰:
    {reviews}
    """

    completion = openai.chat.completions.create(
    model="gpt-4o",
    temperature=0.1,
    messages=[
        {"role": "system", "content": "당신은 숙련된 텍스트 분석가입니다."},
        {"role": "user", "content": prompt},
    ],
    )

    st.markdown(f"### 📍 분석 대상: **{filename}**")
    st.markdown(f"[🔗 리뷰 페이지 바로가기]({url})")

    # 응답에서 JSON 추출
    st.write("응답:", completion.choices[0].message.content.strip())
    response_text = completion.choices[0].message.content.strip()

    json_match = re.search(r"\{.*\}", response_text, re.DOTALL)

    if json_match:
        try:
            json_str = json_match.group()
            data = json.loads(json_str)
            # 성공적으로 파싱된 경우 변수로 분리
            advantages = data.get("advantages", [])
            disadvantages = data.get("disadvantages", [])
            popular_menu = data.get("popular_menu", [])
            rating = data.get("rating", None)
        except json.JSONDecodeError:
            st.error("⚠️ JSON 파싱 실패: 구조가 잘못되었을 수 있습니다.")
            advantages = disadvantages = popular_menu = []
            rating = None
    else:
        st.error("❌ GPT 응답에서 JSON 형식을 찾지 못했습니다.")
        advantages = disadvantages = popular_menu = []
        rating = None

    st.subheader("✅ 장점")
    st.write(advantages)

    st.subheader("⚠️ 단점")
    st.write(disadvantages)

    st.subheader("🍽️ 인기 메뉴")
    st.write(popular_menu)

    st.subheader("⭐ 별점")
    st.write(f"{rating} / 5.0" if rating else "별점 정보 없음")