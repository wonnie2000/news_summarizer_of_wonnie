"""
요약 생성 모듈 (강화 버전)
- 문장 선택 단계에서 노이즈 추가 필터링
- 3가지 전략이 명확히 다른 결과를 생성
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


STOPWORDS = {
    "이", "그", "저", "것", "수", "등", "및", "또", "또한", "그리고",
    "하지만", "그러나", "그래서", "따라서", "그런데", "한편", "이번",
    "지난", "오늘", "어제", "내일", "있다", "없다", "되다", "하다",
    "이다", "였다", "했다", "이라고", "라고", "에서", "에게", "에는",
    "으로", "로서", "로써", "까지", "부터", "보다", "처럼", "같이",
    "위해", "통해", "대해", "관해", "있는", "없는", "이런", "저런",
    "한", "두", "세", "네", "다섯", "년", "월", "일", "시", "분",
}


def is_valid_sentence(s):
    """문장이 본문 내용으로 적합한지 판단"""
    if not s or len(s.strip()) < 20:
        return False

    s = s.strip()

    # 마침표/물음표/느낌표/한국어 어미로 끝나는지
    if not re.search(r"[.!?다요죠음다네군]$", s):
        # 인용문(따옴표로 끝나는 경우)도 허용
        if not re.search(r"[\"\"'']$", s):
            return False

    # 사진/캡션/기자 패턴
    noise_patterns = [
        r"^사진\s*[=:]",
        r"^\[사진\]",
        r"^그림\s*[=:]",
        r"^연합뉴스\s*$",
        r"제공\s*$",
        r"기자\s*$",
        r"@",
        r"^무단",
        r"^저작권",
        r"ⓒ",
        r"©",
        r"Copyright",
    ]
    for p in noise_patterns:
        if re.search(p, s, re.IGNORECASE):
            return False

    # 한글 비율이 낮으면 제외
    korean_chars = len(re.findall(r"[가-힣]", s))
    total_chars = len(re.sub(r"\s", "", s))
    if total_chars > 0 and korean_chars / total_chars < 0.4:
        return False

    return True


def split_sentences(text):
    """문장 분리 + 노이즈 문장 필터링"""
    if not text:
        return []

    text = re.sub(r"\n+", " ", text)
    raw_sentences = re.split(r"(?<=[.!?다요죠])\s+", text)

    cleaned = []
    for s in raw_sentences:
        s = s.strip()
        if is_valid_sentence(s):
            cleaned.append(s)
    return cleaned


def extract_keywords(sentences, top_n=10):
    """핵심 키워드 추출 (빈도 기반)"""
    word_count = Counter()
    for s in sentences:
        words = re.findall(r"[가-힣]{2,}", s)
        for w in words:
            if w in STOPWORDS:
                continue
            for josa in ["은", "는", "이", "가", "을", "를", "과", "와", "의", "에"]:
                if len(w) > 2 and w.endswith(josa):
                    w_stem = w[:-1]
                    if w_stem not in STOPWORDS:
                        word_count[w_stem] += 1
                    break
            else:
                word_count[w] += 1
    return [w for w, _ in word_count.most_common(top_n)]


# ============================================================
# 3가지 추출 전략
# ============================================================

def strategy_lead(sentences, n):
    """버전 A: Lead-N — 앞부분 N개 문장"""
    return sentences[:n] if len(sentences) >= n else sentences


def strategy_keyword(sentences, n):
    """버전 B: 키워드 빈도 기반"""
    if not sentences:
        return []

    keywords = extract_keywords(sentences, top_n=15)
    if not keywords:
        return sentences[:n]

    scored = []
    for i, s in enumerate(sentences):
        score = sum(1 for kw in keywords if kw in s)
        if i == 0:
            score += 2
        scored.append((i, score, s))

    scored.sort(key=lambda x: -x[1])
    top = scored[:n]
    top.sort(key=lambda x: x[0])
    return [s for _, _, s in top]


def strategy_comprehensive(sentences, n):
    """버전 C: 위치 + 키워드 + 길이 종합 점수"""
    if not sentences:
        return []

    keywords = extract_keywords(sentences, top_n=15)
    total = len(sentences)

    scored = []
    for i, s in enumerate(sentences):
        score = 0.0

        if i == 0:
            score += 3.0
        elif i == total - 1:
            score += 1.5
        elif i < total * 0.3:
            score += 1.0
        elif i > total * 0.7:
            score += 0.5

        if keywords:
            kw_count = sum(1 for kw in keywords if kw in s)
            score += kw_count * 0.7

        length = len(s)
        if 30 <= length <= 100:
            score += 1.0
        elif length > 150:
            score -= 0.5

        if '"' in s or '"' in s or "'" in s:
            score += 0.5

        scored.append((i, score, s))

    scored.sort(key=lambda x: -x[1])
    top = scored[:n]
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

    if summary_type == "한줄":
        n = 1
    elif summary_type == "3문장":
        n = 3
    else:
        n = 5

    sentences = split_sentences(text)

    if not sentences:
        return {
            "success": False,
            "error": "유효한 본문 문장을 찾을 수 없습니다.",
            "version": version,
            "summary_type": summary_type,
        }

    if version == "버전A_단순":
        picked = strategy_lead(sentences, n)
    elif version == "버전B_5W1H":
        picked = strategy_keyword(sentences, n)
    else:
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


if __name__ == "__main__":
    sample = """
    정부는 오늘 새로운 경제 정책을 발표했다. 이번 정책은 물가 안정과 경기 부양을
    동시에 달성하는 것을 목표로 한다. 기획재정부 관계자는 이번 정책이 기존 정책의
    한계를 보완한 것이라고 밝혔다. 정책의 핵심 내용은 중소기업 지원 확대와 가계
    부담 완화이다. 전문가들은 이번 정책의 실효성에 대해 엇갈린 반응을 보이고 있다.
    """

    print("\n=== 3개 버전 비교 ===\n")
    results = summarize_all_versions(sample, "3문장")
    for version, res in results.items():
        print(f"▶ {version}")
        print(f"  {res['summary']}\n")
