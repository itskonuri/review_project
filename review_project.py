import streamlit as st
import requests
from bs4 import BeautifulSoup
from PIL import Image
import openai
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from urllib.parse import quote

# 🍚 페이지 설정
st.set_page_config(page_title="밥알천재", layout="wide", page_icon="🍚")

# 🍚 디자인 사양에 맞춘 스타일
st.markdown("""
<style>
/* 전체 텍스트: Gmarket Sans */
.stApp, body {
  font-family: 'Gmarket Sans', sans-serif !important;
  background: linear-gradient(180deg, #FFFFFF 0%, #F2F2F2 100%);
}

/* 중앙 타이틀: 55px, 앞뒤 이모지 */
.centered-title {
  text-align: center;
  font-weight: 500;
  font-size: 55px;
  line-height: 56px;
  color: #585858;
  margin: 40px 0 30px;
}

/* 설명 문구: 20px Bold */
.description {
  text-align: center;
  font-weight: 700;
  font-size: 20px;
  line-height: 24px;
  color: #767676;
  margin-bottom: 30px;
}

/* 검색창 컨테이너 */
.search-container {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin: 0 5% 30px;
}

/* 검색창 래퍼: 흰 배경, 그림자, 둥근 모서리 */
div.stTextInput > div > div {
  position: relative;
  background-color: #FFFFFF !important;
  box-shadow: 0 0 20px rgba(0,0,0,0.1) !important;
  border-radius: 16px !important;
}

/* 입력창 크기 */
div.stTextInput > div > div > input {
  width: 695px !important;
  height: 56px !important;
  padding: 0 60px 0 20px !important;
  border: none !important;
  font-size: 18px !important;
  color: #767676 !important;
}

/* 플레이스홀더 */
::placeholder {
  color: #767676 !important;
  opacity: 1 !important;
}

/* 검색창 내 아이콘: 📸 · 🎙️ */
div.stTextInput > div > div::after {
  content: "📸 🎙️";
  position: absolute;
  top: 50%;
  right: 15px;
  transform: translateY(-50%);
  font-size: 20px;
  cursor: pointer;
}

/* 검색 버튼: 약 2cm(75px) × 56px */
div.stButton > button {
  width: 75px !important;
  height: 56px !important;
  background: #D9D9D9 !important;
  border: none !important;
  border-radius: 16px !important;
  font-size: 24px !important;
  line-height: 56px !important;
  padding: 0 !important;
}
</style>
""", unsafe_allow_html=True)

# 🍚 로고 + 타이틀
logo = Image.open("ba_logo.png")
col_logo, _ = st.columns([1, 5])
with col_logo:
    st.image(logo, width=100)

# 타이틀
st.markdown(
    "<div class='centered-title'>🍚 밥 알 천 재 🥢</div>",
    unsafe_allow_html=True
)

# 설명 문구
st.markdown(
    "<div class='description'>🍽️ 어떤 맛집이 궁금하신가요?</div>",
    unsafe_allow_html=True
)

# 🔍 검색창 + 버튼
with st.container():
    st.markdown("<div class='search-container'>", unsafe_allow_html=True)
    c1, c2 = st.columns([5, 1])
    with c1:
        search_input = st.text_input(
            "", placeholder="식당 이름을 입력하세요", label_visibility="collapsed"
        )
    with c2:
        search_clicked = st.button("🔍 검색")
    st.markdown("</div>", unsafe_allow_html=True)



# 🔐 OpenAI API 키 설정
if "OPENAI_API_KEY" in st.secrets:
    openai.api_key = st.secrets["OPENAI_API_KEY"]
else:
    openai.api_key = st.text_input("🔑 OpenAI API Key를 입력해 주세요", type="password")

# 크롤링 함수 정의
def crawl_naver_reviews(restaurant_name, max_posts=10):
    headers = {"User-Agent": "Mozilla/5.0"}
    query = quote(f"{restaurant_name} 맛집 site:blog.naver.com")
    url = f"https://www.google.com/search?q={query}"
    resp = requests.get(url, headers=headers)
    soup = BeautifulSoup(resp.text, "html.parser")
    cards = soup.select("div.tF2Cxc")[:max_posts]
    reviews = []
    for card in cards:
        link = card.select_one("a")["href"]
        try:
            page = requests.get(link, headers=headers, timeout=5)
            psoup = BeautifulSoup(page.text, "html.parser")
            content = psoup.find(id="postViewArea") or psoup.find("div", {"class": "se-main-container"})
            text = content.get_text(separator="\n").strip()[:1500]
            date_tag = psoup.find("span", {"class": "se_publishDate"}) or psoup.find("span", {"class": "post-date"})
            date_str = date_tag.get_text().strip() if date_tag else ""
            try:
                dt = datetime.strptime(date_str, "%Y.%m.%d.")
            except:
                dt = None
            reviews.append({"text": text, "date": dt})
        except:
            continue
    return reviews

# AI 헬퍼 함수 정의
def call_openai_system(user_prompt: str) -> str:
    resp = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "당신은 친절한 음식 리뷰 요약 도우미입니다."},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.7,
        max_tokens=500,
    )
    return resp.choices[0].message.content.strip()

def generate_summary(texts: list[str]) -> str:
    prompt = f"다음 리뷰들을 보고 3문장 이내로 식당의 핵심 후기를 요약해줘:\n\n" + "\n\n".join(texts)
    return call_openai_system(prompt)

def generate_pros_cons(texts: list[str]) -> str:
    prompt = f"다음 리뷰들을 보고 장점 5가지, 단점 5가지를 마크다운 리스트 형식으로 알려줘:\n\n" + "\n\n".join(texts)
    return call_openai_system(prompt)

def generate_popular_menu(texts: list[str]) -> str:
    prompt = f"다음 리뷰들을 보고 언급된 인기 메뉴와 가격을 최대 5개까지 '- 메뉴: 가격' 형식의 마크다운 리스트로 정리해줘:\n\n" + "\n\n".join(texts)
    return call_openai_system(prompt)

# 검색 클릭 시 처리 및 출력
if search_clicked:
    if not search_input:
        st.warning("❗ 식당 이름을 입력해 주세요.")
    else:
        st.markdown("---")
        st.markdown(f"### 🔎 '{search_input}' 리뷰 분석 결과")

        reviews = crawl_naver_reviews(search_input, max_posts=8)
        texts = [r["text"] for r in reviews if r["text"]]

        summary = generate_summary(texts) if texts else "리뷰가 부족해 요약할 수 없습니다."
        pros_cons = generate_pros_cons(texts) if texts else "리뷰가 부족해 장단점 분석이 어렵습니다."
        popular_menu = generate_popular_menu(texts) if texts else "리뷰가 부족해 메뉴 정보를 뽑을 수 없습니다."

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown("#### 1️⃣ 리뷰 요약")
            st.write(summary)
        with col2:
            st.markdown("#### 2️⃣ 장단점")
            st.markdown(pros_cons)
        with col3:
            st.markdown("#### 3️⃣ 인기 메뉴 & 가격")
            st.markdown(popular_menu)
        with col4:
            st.markdown("#### 4️⃣ 리뷰 최신도")
            dates = [r["date"] for r in reviews if r["date"]]
            if dates:
                df = pd.DataFrame({"date": dates})
                df["월"] = df["date"].dt.to_period("M").astype(str)
                counts = df["월"].value_counts().sort_index()
                fig, ax = plt.subplots(figsize=(4,3))
                ax.bar(counts.index, counts.values)
                ax.set_xticklabels(counts.index, rotation=45, ha="right")
                ax.set_xlabel("년-월")
                ax.set_ylabel("리뷰 개수")
                st.pyplot(fig)
            else:
                st.write("리뷰 날짜 정보를 찾을 수 없습니다.")
