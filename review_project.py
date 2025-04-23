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

# 외부 CSS 적용 함수
def load_local_css(file_name):
    with open(file_name, encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# 적용
load_local_css("style.css")

# 🍚 로고 + 타이틀
col_logo, _ = st.columns([1, 5])
with col_logo:
    logo = Image.open("ba_logo.png")
    st.image(logo, width=100)

st.markdown("<div class='centered-title'>🍚 밥 알 천 재 🥢</div>", unsafe_allow_html=True)
st.markdown("<div class='description'>🍽️ 어떤 맛집이 궁금하신가요?</div>", unsafe_allow_html=True)

# 🔍 검색창
with st.container():
    st.markdown("<div class='search-container'>", unsafe_allow_html=True)
    c1, c2 = st.columns([5, 1])
    with c1:
        search_input = st.text_input("", placeholder="식당 이름을 입력하세요", label_visibility="collapsed")
    with c2:
        search_clicked = st.button("🔍 검색")
    st.markdown("</div>", unsafe_allow_html=True)

if "openai" in st.secrets:
    openai.api_key = st.secrets["openai"]["API_KEY"]
else:
    openai.api_key = st.text_input("🔑 OpenAI API Key를 입력해 주세요", type="password")

# 🔎 리뷰 크롤링
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
            dt = datetime.strptime(date_str, "%Y.%m.%d.") if date_str else None
            reviews.append({"text": text, "date": dt})
        except:
            continue
    return reviews

# 🧠 AI 처리
def call_openai_system(prompt: str) -> str:
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "당신은 친절한 음식 리뷰 요약 도우미입니다."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=500,
    )
    return response.choices[0].message.content.strip()

def generate_summary(texts): 
    return call_openai_system(f"다음 리뷰들을 보고 3문장 이내로 식당의 핵심 후기를 요약해줘:\n\n" + "\n\n".join(texts))

def generate_pros_cons(texts): 
    return call_openai_system(f"다음 리뷰들을 보고 장점 5가지, 단점 5가지를 마크다운 리스트 형식으로 알려줘:\n\n" + "\n\n".join(texts))

def generate_popular_menu(texts): 
    return call_openai_system(f"다음 리뷰들을 보고 언급된 인기 메뉴와 가격을 최대 5개까지 '- 메뉴: 가격' 형식의 마크다운 리스트로 정리해줘:\n\n" + "\n\n".join(texts))

# 📊 검색 결과 출력
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
