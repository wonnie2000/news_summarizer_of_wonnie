"""
텍스트 전처리 모듈
- 크롤링된 텍스트를 AI에 보내기 전에 정리
- 정규화 → 문장 분리 → 청킹
"""

import re

# KSS 설치 여부 확인
try:
    import kss
    USE_KSS = True
except ImportError:
    USE_KSS = False
    print("⚠️  KSS가 설치되지 않았습니다. 기본 문장 분리를 사용합니다.")
    print("   설치 명령어: pip3 install kss")


def normalize(text):
    """
    텍스트 정규화
    - 특수 공백, 불필요한 문자, 연속 줄바꿈 등을 정리
    """
    if not text:
        return ""

    # 특수 공백 문자 → 일반 공백
    text = text.replace("\u3000", " ")   # 전각 공백
    text = text.replace("\xa0", " ")     # non-breaking space
    text = text.replace("\t", " ")       # 탭

    # 연속 줄바꿈 정리 (3개 이상 → 2개)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # 연속 공백 정리
    text = re.sub(r" {2,}", " ", text)

    # 각 줄 앞뒤 공백 제거
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)

    # 빈 줄만 있는 경우 제거
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def split_sentences(text):
    """
    텍스트를 문장 단위로 분리
    - KSS가 있으면 한국어 특화 분리 사용
    - 없으면 기본 정규표현식 기반 분리
    """
    if not text:
        return []

    if USE_KSS:
        # KSS 한국어 문장 분리
        sentences = kss.split_sentences(text)
    else:
        # 기본 문장 분리 (마침표, 물음표, 느낌표 기준)
        sentences = re.split(r'(?<=[.?!])\s+', text)

    # 빈 문장 제거 및 앞뒤 공백 정리
    sentences = [s.strip() for s in sentences if s.strip()]

    return sentences


def chunk_sentences(sentences, max_tokens=3000):
    """
    문장 리스트를 토큰 제한에 맞게 청킹
    - 한국어 기준 1글자 ≈ 1.5토큰으로 추정
    - 문장 경계를 존중하면서 분할
    """
    if not sentences:
        return []

    chunks = []
    current_chunk = []
    current_length = 0

    for sentence in sentences:
        # 한국어 토큰 수 추정 (글자수 × 1.5)
        estimated_tokens = int(len(sentence) * 1.5)

        # 현재 청크에 추가하면 제한 초과하는 경우
        if current_length + estimated_tokens > max_tokens and current_chunk:
            chunks.append(" ".join(current_chunk))
            current_chunk = []
            current_length = 0

        current_chunk.append(sentence)
        current_length += estimated_tokens

    # 마지막 청크 추가
    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks


def preprocess(text, max_tokens=3000):
    """
    전처리 메인 함수
    - 정규화 → 문장 분리 → 청킹을 한 번에 수행

    Args:
        text (str): 크롤링된 원문 텍스트
        max_tokens (int): 청크당 최대 토큰 수

    Returns:
        dict: {
            "normalized": 정규화된 텍스트,
            "sentences": 문장 리스트,
            "chunks": 청크 리스트,
            "num_sentences": 문장 수,
            "num_chunks": 청크 수
        }
    """
    # 1단계: 정규화
    normalized = normalize(text)

    # 2단계: 문장 분리
    sentences = split_sentences(normalized)

    # 3단계: 청킹
    chunks = chunk_sentences(sentences, max_tokens)

    return {
        "normalized": normalized,
        "sentences": sentences,
        "chunks": chunks,
        "num_sentences": len(sentences),
        "num_chunks": len(chunks)
    }


# ==============================
# 테스트 코드
# ==============================
if __name__ == "__main__":

    print("=" * 50)
    print("  전처리 모듈 테스트")
    print("=" * 50)

    # 테스트용 샘플 텍스트
    sample = """
    정부는   오늘 새로운 경제 정책을 발표했다.    이번 정책은
    물가 안정과 경기 부양을 동시에 달성하는 것을 목표로 한다.

    기획재정부 관계자는 "이번 정책은 기존 정책의 한계를 보완한 것"이라며
    "하반기 경제 회복에 기여할 것으로 기대한다"고 밝혔다.

    한편, 전문가들은 이번 정책의 실효성에 대해 엇갈린 반응을 보이고 있다.
    일부 전문가는 긍정적인 평가를 내놓았지만, 다른 전문가들은 재정 건전성에
    대한 우려를 표명했다.   한국은행은 이번 정책 발표에 대해 별도의 입장을
    내놓지 않았다.
    """

    print("\n[원문]")
    print(sample[:100] + "...")

    result = preprocess(sample)

    print(f"\n[정규화 결과]")
    print(result["normalized"][:100] + "...")

    print(f"\n[문장 분리 결과] ({result['num_sentences']}개 문장)")
    for i, s in enumerate(result["sentences"], 1):
        print(f"  {i}. {s}")

    print(f"\n[청킹 결과] ({result['num_chunks']}개 청크)")
    for i, c in enumerate(result["chunks"], 1):
        print(f"  청크 {i} ({len(c)}자): {c[:80]}...")

    print("\n" + "=" * 50)
    print("  테스트 완료")
    print("=" * 50)
