"""
AI 뉴스 요약 시스템 - 웹 데모 (최종 발표 버전)
- 메인 화면에 주요 뉴스 카드 자동 표시
- 카드 클릭만으로 즉시 요약
"""

import streamlit as st
from crawler import crawl_news
from preprocessor import preprocess
from summarizer import summarize, summarize_all_versions, PROMPT_TEMPLATES
from evaluator import calculate_rouge
from news_feed import fetch_naver_headlines, NAVER_SECTIONS


# ════════════════════════════════════════════════════
# 페이지 설정
# ════════════════════════════════════════════════════
st.set_page_config(
    page_title="AI 뉴스 요약 시스템",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ════════════════════════════════════════════════════
# 커스텀 CSS
# ════════════════════════════════════════════════════
st.markdown("""
<style>
.stApp {
    background: linear-gradient(180deg, #FAFBFC 0%, #F4F6FB 100%);
}

.main-title {
    font-size: 2.4rem;
    font-weight: 800;
    background: linear-gradient(120deg, #1E2761 0%, #3B6FD4 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 0.3rem;
    letter-spacing: -0.5px;
}

.main-subtitle {
    font-size: 1rem;
    color: #667085;
    margin-bottom: 2rem;
    font-weight: 400;
}

.section-label {
    font-size: 1.1rem;
    font-weight: 700;
    color: #1E2761;
    margin-bottom: 0.8rem;
    margin-top: 1rem;
    display: flex;
    align-items: center;
    gap: 0.4rem;
}

[data-testid="stMetric"] {
    background: white;
    padding: 1rem 1.2rem;
    border-radius: 10px;
    border: 1px solid #E4E7EC;
    box-shadow: 0 1px 2px rgba(0,0,0,0.03);
}

[data-testid="stMetricLabel"] {
    font-size: 0.85rem;
    color: #667085;
    font-weight: 500;
}

[data-testid="stMetricValue"] {
    font-size: 1.6rem;
    font-weight: 700;
    color: #1E2761;
}

.stButton button {
    border-radius: 10px;
    transition: all 0.2s ease;
}

.stButton button[kind="primary"] {
    background: linear-gradient(120deg, #3B6FD4 0%, #1E2761 100%);
    color: white;
    border: none;
    font-weight: 600;
    font-size: 1.05rem;
    padding: 0.7rem 2rem;
    box-shadow: 0 2px 6px rgba(59, 111, 212, 0.25);
}

.stButton button[kind="primary"]:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(59, 111, 212, 0.35);
}

/* 뉴스 카드 버튼 스타일 */
.stButton button[kind="secondary"] {
    background: white;
    color: #1E2761;
    border: 1px solid #E4E7EC;
    text-align: left;
    padding: 1rem 1.2rem;
    font-weight: 500;
    font-size: 0.92rem;
    line-height: 1.5;
    height: auto;
    min-height: 90px;
    white-space: normal;
    width: 100%;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}

.stButton button[kind="secondary"]:hover {
    border-color: #3B6FD4;
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(59, 111, 212, 0.15);
}

.stTextInput input, .stTextArea textarea {
    border-radius: 10px;
    border: 1px solid #D0D5DD;
    background: white;
}

[data-testid="stSidebar"] {
    background: white;
    border-right: 1px solid #E4E7EC;
}

[data-testid="stSidebar"] h2 {
    color: #1E2761;
    font-size: 1.1rem;
    font-weight: 700;
}

h3 {
    color: #1E2761 !important;
    font-weight: 700 !important;
    margin-top: 1.5rem !important;
}

.stAlert {
    border-radius: 10px;
    border: none;
}

.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
}

.stTabs [data-baseweb="tab"] {
    background: white;
    border-radius: 8px;
    padding: 0.5rem 1rem;
    border: 1px solid #E4E7EC;
}

.stTabs [aria-selected="true"] {
    background: #3B6FD4 !important;
    color: white !important;
}

hr {
    border-color: #E4E7EC;
}

.summary-box {
    background: linear-gradient(120deg, #F0F7FF 0%, #E8F0FE 100%);
    border-left: 4px solid #3B6FD4;
    padding: 1.2rem 1.5rem;
    border-radius: 10px;
    margin: 0.5rem 0;
    font-size: 1.02rem;
    line-height: 1.7;
    color: #1E2761;
}

.footer {
    text-align: center;
    color: #98A2B3;
    font-size: 0.85rem;
    margin-top: 3rem;
    padding-top: 1.5rem;
    border-top: 1px solid #E4E7EC;
}

/* 캐테고리 탭 스타일 */
.category-pill {
    display: inline-block;
    background: #F0F4FA;
    color: #3B6FD4;
    padding: 0.2rem 0.7rem;
    border-radius: 100px;
    font-size: 0.75rem;
    font-weight: 600;
    margin-bottom: 0.5rem;
}
</style>
""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════
# 세션 상태 초기화
# ════════════════════════════════════════════════════
if "selected_url" not in st.session_state:
    st.session_state.selected_url = ""
if "trigger_analysis" not in st.session_state:
    st.session_state.trigger_analysis = False


# ════════════════════════════════════════════════════
# 헤더
# ════════════════════════════════════════════════════
st.markdown('<div class="main-title">📰 AI 뉴스 기사 자동 요약 시스템</div>', unsafe_allow_html=True)
st.markdown('<div class="main-subtitle">클릭 한 번으로 핵심만 빠르게.</div>', unsafe_allow_html=True)


# ════════════════════════════════════════════════════
# 사이드바
# ════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## ⚙️ 설정")

    st.markdown("##### 📝 요약 옵션")
    summary_type = st.selectbox(
        "요약 유형",
        ["한줄", "3문장", "문단"],
        index=1,
        label_visibility="collapsed"
    )

    prompt_version = st.selectbox(
        "프롬프트 버전",
        list(PROMPT_TEMPLATES.keys()),
        index=1,
        format_func=lambda x: {
            "버전A_단순": "버전 A — 단순 추출",
            "버전B_5W1H": "버전 B — 5W1H 키워드",
            "버전C_상세": "버전 C — 종합 점수"
        }.get(x, x)
    )

    compare_mode = st.toggle(
        "🧪 3개 버전 비교",
        value=False,
        help="3개 프롬프트 버전을 동시 실행하여 결과 비교"
    )

    st.divider()

    st.markdown("##### 🔧 전처리 옵션")
    max_tokens = st.slider("청크 토큰 제한", 500, 3000, 3000, step=100)

    st.divider()

    st.markdown("##### ℹ️ 파이프라인")
    st.markdown("""
    <div style='font-size: 0.88rem; line-height: 1.8; color: #475467;'>
    1️⃣ &nbsp; 데이터 수집<br>
    2️⃣ &nbsp; 텍스트 전처리<br>
    3️⃣ &nbsp; 요약 생성<br>
    4️⃣ &nbsp; 품질 평가
    </div>
    """, unsafe_allow_html=True)


# ════════════════════════════════════════════════════
# 메인: 뉴스 피드 + 직접 URL 입력
# ════════════════════════════════════════════════════

# 카테고리 탭
st.markdown('<div class="section-label">🗞️ 오늘의 주요 뉴스</div>', unsafe_allow_html=True)

categories = list(NAVER_SECTIONS.keys())
tabs = st.tabs([f"#{c}" for c in categories])

# 캐시된 헤드라인 가져오기
@st.cache_data(ttl=600)  # 10분 캐시
def get_cached_headlines(section, limit=8):
    return fetch_naver_headlines(section, limit)


for tab, category in zip(tabs, categories):
    with tab:
        with st.spinner(f"📡 {category} 뉴스 수집 중..."):
            headlines = get_cached_headlines(category, limit=8)

        if not headlines:
            st.warning(f"⚠️ {category} 뉴스를 불러올 수 없습니다. 직접 URL을 입력해주세요.")
        else:
            # 2열 그리드로 카드 배치
            cols = st.columns(2)
            for i, article in enumerate(headlines):
                col = cols[i % 2]
                with col:
                    title = article["title"]
                    # 너무 길면 자르기
                    display_title = title if len(title) <= 80 else title[:77] + "..."

                    # 카드형 버튼
                    if st.button(
                        f"📰 {display_title}",
                        key=f"card_{category}_{i}",
                        use_container_width=True,
                        type="secondary",
                    ):
                        st.session_state.selected_url = article["url"]
                        st.session_state.trigger_analysis = True
                        st.rerun()


st.divider()

# 직접 URL 입력 (옵션)
with st.expander("✏️ 직접 URL 입력하기"):
    col_input, col_button = st.columns([5, 1])

    with col_input:
        manual_url = st.text_input(
            "뉴스 URL",
            placeholder="https://n.news.naver.com/article/...",
            label_visibility="collapsed",
            key="manual_url_input"
        )

    with col_button:
        manual_submit = st.button("🚀 분석", type="primary", use_container_width=True)

    if manual_submit and manual_url:
        st.session_state.selected_url = manual_url
        st.session_state.trigger_analysis = True
        st.rerun()

with st.expander("📋 참조 요약 입력 (ROUGE 평가용 · 선택)"):
    reference_summary = st.text_area(
        "정답 요약",
        placeholder="이 기사의 핵심을 직접 요약해서 입력하면 AI 요약과 ROUGE 점수로 비교합니다.",
        height=80,
        label_visibility="collapsed"
    )


# ════════════════════════════════════════════════════
# 분석 실행
# ════════════════════════════════════════════════════
if st.session_state.trigger_analysis and st.session_state.selected_url:

    url = st.session_state.selected_url

    st.divider()
    st.markdown(f"### 🔎 분석 대상")
    st.caption(url)

    # 1) 크롤링
    with st.spinner("📥 기사를 가져오는 중..."):
        result = crawl_news(url)

    if not result["success"]:
        st.error(f"❌ 크롤링 실패: {result['error']}")
    else:
        # 2) 전처리
        processed = preprocess(result["text"], max_tokens=max_tokens)

        # 통계 카드
        st.markdown("### 📊 분석 통계")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("원문 길이", f"{len(result['text']):,}자")
        c2.metric("문장 수", f"{processed['num_sentences']}개")
        c3.metric("청크 수", f"{processed['num_chunks']}개")
        c4.metric("추정 토큰", f"{int(len(result['text']) * 1.5):,}")

        # 제목
        st.markdown("### 📰 기사 제목")
        st.info(result["title"])

        # 3) 요약
        st.markdown("### 🤖 AI 요약 결과")
        input_text = " ".join(processed["chunks"])

        if compare_mode:
            with st.spinner("🧪 3개 프롬프트 버전 실행 중..."):
                all_results = summarize_all_versions(input_text, summary_type)

            version_labels = {
                "버전A_단순": ("버전 A", "단순 추출 방식", "#94A3B8"),
                "버전B_5W1H": ("버전 B", "5W1H 키워드 기반", "#3B6FD4"),
                "버전C_상세": ("버전 C", "종합 점수 기반", "#10B981"),
            }

            cols = st.columns(3)
            summaries = {}

            for i, (version, res) in enumerate(all_results.items()):
                label, desc, color = version_labels.get(version, (version, "", "#3B6FD4"))
                with cols[i]:
                    st.markdown(f"""
                    <div style='background: white; padding: 1rem; border-radius: 10px;
                                border: 1px solid #E4E7EC; margin-bottom: 0.5rem;'>
                        <div style='display: flex; align-items: center; gap: 8px;'>
                            <div style='width: 8px; height: 8px; background: {color}; border-radius: 50%;'></div>
                            <span style='font-weight: 700; color: #1E2761;'>{label}</span>
                        </div>
                        <div style='font-size: 0.8rem; color: #667085; margin-top: 0.3rem;'>{desc}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    if res["success"]:
                        st.markdown(
                            f'<div class="summary-box">{res["summary"]}</div>',
                            unsafe_allow_html=True
                        )
                        summaries[version] = res["summary"]
                        st.caption(f"📏 {res['output_length']}자")
                    else:
                        st.error(res["error"])

            if reference_summary and summaries:
                st.markdown("### 📊 ROUGE 점수 비교")
                score_data = []
                for version, summary in summaries.items():
                    scores = calculate_rouge(reference_summary, summary)
                    score_data.append({
                        "버전": version_labels.get(version, (version,))[0],
                        "ROUGE-1": f"{scores['rouge1']:.4f}",
                        "ROUGE-2": f"{scores['rouge2']:.4f}",
                        "ROUGE-L": f"{scores['rougeL']:.4f}",
                    })
                st.dataframe(score_data, use_container_width=True, hide_index=True)

                best_version = max(
                    summaries.keys(),
                    key=lambda v: calculate_rouge(reference_summary, summaries[v])["rouge1"]
                )
                best_label = version_labels.get(best_version, (best_version,))[0]
                st.success(f"🏆 ROUGE-1 기준 최고 점수: **{best_label}**")

        else:
            with st.spinner("🤖 요약 생성 중..."):
                res = summarize(input_text, prompt_version, summary_type)

            if res["success"]:
                left, right = st.columns(2)
                with left:
                    st.markdown("##### 📄 원문")
                    st.text_area(
                        "원문",
                        result["text"],
                        height=280,
                        disabled=True,
                        label_visibility="collapsed"
                    )
                with right:
                    st.markdown(f"##### ✨ AI 요약")
                    st.markdown(
                        f'<div class="summary-box">{res["summary"]}</div>',
                        unsafe_allow_html=True
                    )

                st.markdown("##### 📐 압축 통계")
                s1, s2, s3 = st.columns(3)
                s1.metric("원문 길이", f"{res['input_length']:,}자")
                s2.metric("요약 길이", f"{res['output_length']:,}자")
                compression = (1 - res["output_length"] / res["input_length"]) * 100
                s3.metric("압축률", f"{compression:.1f}%")

                if reference_summary:
                    st.markdown("### 📊 ROUGE 평가")
                    scores = calculate_rouge(reference_summary, res["summary"])
                    r1, r2, r3 = st.columns(3)
                    r1.metric("ROUGE-1", f"{scores['rouge1']:.4f}")
                    r2.metric("ROUGE-2", f"{scores['rouge2']:.4f}")
                    r3.metric("ROUGE-L", f"{scores['rougeL']:.4f}")
            else:
                st.error(f"❌ 요약 실패: {res['error']}")

        # 상세 정보
        with st.expander("🔍 상세 정보 보기"):
            tab1, tab2, tab3 = st.tabs(["📄 원문 전체", "✂️ 문장 분리", "📦 청킹 결과"])

            with tab1:
                st.text_area(
                    "전체 원문",
                    result["text"],
                    height=400,
                    disabled=True,
                    label_visibility="collapsed"
                )

            with tab2:
                st.caption(f"총 {processed['num_sentences']}개 문장")
                for i, s in enumerate(processed["sentences"], 1):
                    st.markdown(f"**{i}.** {s}")

            with tab3:
                st.caption(f"총 {processed['num_chunks']}개 청크")
                for i, chunk in enumerate(processed["chunks"], 1):
                    token_est = int(len(chunk) * 1.5)
                    st.markdown(f"**청크 {i}** · {len(chunk)}자 · 약 {token_est}토큰")
                    st.text(chunk[:300] + ("..." if len(chunk) > 300 else ""))


# ════════════════════════════════════════════════════
# 푸터
# ════════════════════════════════════════════════════
st.markdown("""
<div class="footer">
AI 뉴스 기사 자동 요약 시스템 · 졸업 프로젝트<br>
crawler · preprocessor · summarizer · evaluator · news_feed
</div>
""", unsafe_allow_html=True)
