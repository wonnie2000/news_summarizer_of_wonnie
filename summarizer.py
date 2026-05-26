"""
요약 생성 모듈 (개선 버전)
- 3개 프롬프트 버전이 명확히 다른 결과를 생성하도록 전략 차별화
- 버전 A: Lead-3 방식 (앞 문장 위주)
- 버전 B: 키워드 빈도 기반 (핵심 단어 포함 문장 우선)
- 버전 C: 위치 + 길이 + 키워드 종합 점수 기반
"""

import re
from collections import Counter


PROMPT_TEMPLATES = {
    "버전A_단순": {
        "한줄": "다음 뉴스 기사를 한 문장으로 요약해주세요.\n\n{text}",
        "3문장": "다음 뉴스 기사를 3문장으로 요약해주세요.\n\n{text}",
        "문단": "다음 뉴스 기사를 한 문단으로 요약해주세요.\n\n{text}",
    },
    "버전B_5W1H": {
        "한줄": (
            "당신은 객관적이고 정확한 뉴스 요약가입니다. "
            "다음 뉴스 기사를 한 문장으로 요약하되, 누가/무엇을/왜/어떻게 중 "
            "가장 중요한 정보를 포함하세요.\n\n{text}"
        ),
        "3문장": (
            "당신은 객관적이고 정확한 뉴스 요약가입니다. "
            "다음 뉴스 기사를 정확히 3문장으로 요약해주세요. "
            "5W1H 중 핵심 정보를 포함해야 합니다.\n\n{text}"
        ),
        "문단": (
            "당신은 객관적이고 정확한 뉴스 요약가입니다. "
            "다음 뉴스 기사를 한 문단으로 요약하되 5W1H를 빠짐없이 포함해주세요.\n\n{text}"
        ),
    },
    "버전C_상세": {
        "한줄": (
            "다음 뉴스 기사를 한국어로 요약해주세요.\n"
            "조건: 1문장, 50자 이내, 격식체, 핵심 사건과 주체 명시\n\n{text}"
        ),
        "3문장": (
            "다음 뉴스 기사를 한국어로 요약해주세요.\n"
            "조건: 3문장, 격식체, 1문장(핵심) / 2문장(배경) / 3문장(전망)\n\n{text}"
        ),
        "문단": (
            "다음 뉴스 기사를 한국어로 요약해주세요.\n"
            "조건: 4~5문장 한 문단, 격식체, 5W1H 포함, 시간순 정리\n\n{text}"
        ),
    },
}


# 한국어 불용어
STOPWORDS = {
    "이", "그", "저", "것", "수", "등", "및", "또", "또한", "그리고",
    "하지만", "그러나", "그래서", "따라서", "그런데", "한편", "이번",
    "지난", "오늘", "어제", "내일", "있다", "없다", "되다", "하다",
    "이다", "였다", "했다", "이라고", "라고", "에서", "에게", "에는",
    "으로", "로서", "로써", "까지", "부터", "보다", "처럼", "같이",
    "위해", "통해", "대해", "관해", "있는", "없는", "이런", "저런",
    "한", "두", "세", "네", "다섯", "년", "월", "일", "시", "분",
}


def split_sentences(text):
    """문장 분리"""
    if not text:
        return []
    # 줄바꿈을 일단 공백으로
    text = re.sub(r"\n+", " ", text)
    # 마침표/물음표/느낌표 기준 분리
    sentences = re.split(r"(?<=[.!?다요죠])\s+", text)
    # 정리
    cleaned = []
    for s in sentences:
        s = s.strip()
        # 너무 짧거나 노이즈성 문장 제외
        if len(s) < 15:
            continue
        if s.count(" ") < 2:
            continue
        cleaned.append(s)
    return cleaned


def extract_keywords(sentences, top_n=10):
    """문장들에서 핵심 키워드 추출 (단순 빈도 기반)"""
    word_count = Counter()
    for s in sentences:
        # 한글 단어만 추출 (2글자 이상)
        words = re.findall(r"[가-힣]{2,}", s)
        for w in words:
            if w in STOPWORDS:
                continue
            # 끝에 붙는 조사 단순 제거
            for josa in ["은", "는", "이", "가", "을", "를", "과", "와", "의", "에"]:
                if len(w) > 2 and w.endswith(josa):
                    w_stem = w[:-1]
                    word_count[w_stem] += 1
                    break
            else:
                word_count[w] += 1
    return [w for w, _ in word_count.most_common(top_n)]


# ============================================================
# 버전 A: 단순 (Lead-3 방식)
# - 기사 앞부분 N개 문장을 그대로 사용
# - 가장 단순한 방식, 베이스라인
# ============================================================
def strategy_lead(sentences, n):
    return sentences[:n] if len(sentences) >= n else sentences


# ============================================================
# 버전 B: 키워드 빈도 기반 (5W1H 핵심 정보 우선)
# - 핵심 키워드가 많이 포함된 문장을 점수순으로 선택
# - 뉴스의 핵심 정보 포함률이 높아짐
# ============================================================
def strategy_keyword(sentences, n):
    if not sentences:
        return []

    keywords = extract_keywords(sentences, top_n=15)
    if not keywords:
        return sentences[:n]

    scored = []
    for i, s in enumerate(sentences):
        score = sum(1 for kw in keywords if kw in s)
        # 첫 문장에 가산점 (뉴스 lead 문장이 핵심인 경우 많음)
        if i == 0:
            score += 2
        scored.append((i, score, s))

    # 점수순 정렬
    scored.sort(key=lambda x: -x[1])
    top = scored[:n]
    # 원래 순서대로 재정렬
    top.sort(key=lambda x: x[0])
    return [s for _, _, s in top]


# ============================================================
# 버전 C: 종합 점수 기반 (위치 + 키워드 + 길이)
# - 위치, 키워드 포함, 문장 길이를 종합적으로 평가
# - 가장 정교한 방식
# ============================================================
def strategy_comprehensive(sentences, n):
    if not sentences:
        return []

    keywords = extract_keywords(sentences, top_n=15)
    total = len(sentences)

    scored = []
    for i, s in enumerate(sentences):
        score = 0.0

        # 위치 점수: 앞쪽과 뒤쪽에 가중치 (뉴스는 lead와 conclusion이 중요)
        if i == 0:
            score += 3.0
        elif i == total - 1:
            score += 1.5
        elif i < total * 0.3:
            score += 1.0
        elif i > total * 0.7:
            score += 0.5

        # 키워드 점수
        if keywords:
            kw_count = sum(1 for kw in keywords if kw in s)
            score += kw_count * 0.7

        # 길이 점수: 너무 짧거나 긴 문장 페널티 (적정 길이 30~100자)
        length = len(s)
        if 30 <= length <= 100:
            score += 1.0
        elif length > 150:
            score -= 0.5

        # 인용 부호 가산점 (인용문은 핵심 정보 자주 포함)
        if '"' in s or '"' in s or "'" in s:
            score += 0.5

        scored.append((i, score, s))

    # 점수순 선택
    scored.sort(key=lambda x: -x[1])
    top = scored[:n]
    # 원래 순서로 재정렬
    top.sort(key=lambda x: x[0])
    return [s for _, _, s in top]


def summarize(text, version="버전B_5W1H", summary_type="3문장", **kwargs):
    """요약 생성 메인 함수"""
    if not text or len(text.strip()) < 50:
        return {
            "success": False,
            "error": "요약할 텍스트가 너무 짧습니다.",
            "version": version,
            "summary_type": summary_type,
        }

    # 요약 유형별 문장 수
    if summary_type == "한줄":
        n = 1
    elif summary_type == "3문장":
        n = 3
    else:  # 문단
        n = 5

    sentences = split_sentences(text)

    if not sentences:
        return {
            "success": False,
            "error": "분리 가능한 문장이 없습니다.",
            "version": version,
            "summary_type": summary_type,
        }

    # 버전별 전략 적용
    if version == "버전A_단순":
        picked = strategy_lead(sentences, n)
    elif version == "버전B_5W1H":
        picked = strategy_keyword(sentences, n)
    else:  # 버전C_상세
        picked = strategy_comprehensive(sentences, n)

    summary = " ".join(picked).strip()

    return {
        "success": True,
        "summary": summary,
        "version": version,
        "summary_type": summary_type,
        "input_length": len(text),
        "output_length": len(summary),
    }


def summarize_all_versions(text, summary_type="3문장", **kwargs):
    """3개 프롬프트 버전 모두로 요약 생성"""
    results = {}
    for version in PROMPT_TEMPLATES.keys():
        results[version] = summarize(text, version, summary_type)
    return results


# ==============================
# 테스트
# ==============================
if __name__ == "__main__":
    sample = """
    정부는 오늘 새로운 경제 정책을 발표했다. 이번 정책은 물가 안정과 경기 부양을
    동시에 달성하는 것을 목표로 한다. 기획재정부 관계자는 이번 정책이 기존 정책의
    한계를 보완한 것이라고 밝혔다. 정책의 핵심 내용은 중소기업 지원 확대와 가계
    부담 완화이다. 전문가들은 이번 정책의 실효성에 대해 엇갈린 반응을 보이고 있다.
    일부는 긍정적인 평가를 내놓았다. 다른 전문가들은 재정 건전성에 대한 우려를
    표명했다. 한국은행은 이번 정책 발표에 대해 별도의 입장을 내놓지 않았다.
    """

    print("\n=== 3개 버전 비교 (3문장 요약) ===\n")
    results = summarize_all_versions(sample, "3문장")
    for version, res in results.items():
        print(f"▶ {version}")
        print(f"  {res['summary']}\n")
