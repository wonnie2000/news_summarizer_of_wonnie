"""
요약 품질 평가 모듈
- ROUGE Score 기반 자동 평가
- 프롬프트 버전별 성능 비교 및 시각화
"""

import matplotlib.pyplot as plt
import matplotlib
import platform

# 한글 폰트 설정 (운영체제별)
if platform.system() == "Darwin":      # macOS
    matplotlib.rcParams["font.family"] = "AppleGothic"
elif platform.system() == "Windows":
    matplotlib.rcParams["font.family"] = "Malgun Gothic"
matplotlib.rcParams["axes.unicode_minus"] = False

# rouge-score 라이브러리 확인
try:
    from rouge_score import rouge_scorer
    USE_ROUGE_LIB = True
except ImportError:
    USE_ROUGE_LIB = False
    print("⚠️  rouge-score 라이브러리가 설치되지 않았습니다.")
    print("   설치 명령어: pip3 install rouge-score")


def tokenize_korean(text):
    """
    한국어 텍스트를 간단히 토큰화 (공백 기준 + 조사 분리)
    rouge-score는 영어 기반이라 한국어에서는 공백 토큰화로 대체
    """
    if not text:
        return []
    return text.split()


def calculate_rouge(reference, hypothesis):
    """
    ROUGE 점수 계산

    Args:
        reference (str): 참조 요약 (사람이 작성한 정답)
        hypothesis (str): AI가 생성한 요약

    Returns:
        dict: {"rouge1": float, "rouge2": float, "rougeL": float}
    """
    if not reference or not hypothesis:
        return {"rouge1": 0.0, "rouge2": 0.0, "rougeL": 0.0}

    if USE_ROUGE_LIB:
        # rouge-score 라이브러리 사용
        scorer = rouge_scorer.RougeScorer(
            ["rouge1", "rouge2", "rougeL"],
            use_stemmer=False
        )
        scores = scorer.score(reference, hypothesis)
        return {
            "rouge1": scores["rouge1"].fmeasure,
            "rouge2": scores["rouge2"].fmeasure,
            "rougeL": scores["rougeL"].fmeasure,
        }
    else:
        # 라이브러리 없을 때 간단한 대체 구현
        return _simple_rouge(reference, hypothesis)


def _simple_rouge(reference, hypothesis):
    """
    rouge-score 라이브러리가 없을 때 사용하는 간단한 대체 구현
    """
    ref_tokens = tokenize_korean(reference)
    hyp_tokens = tokenize_korean(hypothesis)

    if not ref_tokens or not hyp_tokens:
        return {"rouge1": 0.0, "rouge2": 0.0, "rougeL": 0.0}

    # ROUGE-1: 단어 단위 일치
    common_1 = set(ref_tokens) & set(hyp_tokens)
    precision_1 = len(common_1) / len(set(hyp_tokens)) if hyp_tokens else 0
    recall_1 = len(common_1) / len(set(ref_tokens)) if ref_tokens else 0
    rouge1 = (2 * precision_1 * recall_1 / (precision_1 + recall_1)) if (precision_1 + recall_1) > 0 else 0

    # ROUGE-2: 2-gram 일치
    ref_bigrams = set(zip(ref_tokens[:-1], ref_tokens[1:]))
    hyp_bigrams = set(zip(hyp_tokens[:-1], hyp_tokens[1:]))
    common_2 = ref_bigrams & hyp_bigrams
    precision_2 = len(common_2) / len(hyp_bigrams) if hyp_bigrams else 0
    recall_2 = len(common_2) / len(ref_bigrams) if ref_bigrams else 0
    rouge2 = (2 * precision_2 * recall_2 / (precision_2 + recall_2)) if (precision_2 + recall_2) > 0 else 0

    # ROUGE-L: 최장 공통 부분 수열
    rougeL = _lcs_score(ref_tokens, hyp_tokens)

    return {"rouge1": rouge1, "rouge2": rouge2, "rougeL": rougeL}


def _lcs_score(ref, hyp):
    """LCS(최장 공통 부분 수열) 기반 ROUGE-L 점수"""
    m, n = len(ref), len(hyp)
    if m == 0 or n == 0:
        return 0.0

    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if ref[i-1] == hyp[j-1]:
                dp[i][j] = dp[i-1][j-1] + 1
            else:
                dp[i][j] = max(dp[i-1][j], dp[i][j-1])

    lcs_len = dp[m][n]
    precision = lcs_len / n
    recall = lcs_len / m
    return (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0


def evaluate_prompts(prompt_results):
    """
    여러 프롬프트 버전의 요약 결과를 종합 평가

    Args:
        prompt_results (dict): {
            "버전A": [{"reference": ..., "hypothesis": ...}, ...],
            "버전B": [...],
            ...
        }

    Returns:
        dict: {버전이름: {"rouge1": 평균, "rouge2": 평균, "rougeL": 평균}}
    """
    final_scores = {}

    for version_name, samples in prompt_results.items():
        total = {"rouge1": 0.0, "rouge2": 0.0, "rougeL": 0.0}

        for sample in samples:
            scores = calculate_rouge(sample["reference"], sample["hypothesis"])
            for k in total:
                total[k] += scores[k]

        n = len(samples)
        final_scores[version_name] = {
            "rouge1": total["rouge1"] / n if n > 0 else 0,
            "rouge2": total["rouge2"] / n if n > 0 else 0,
            "rougeL": total["rougeL"] / n if n > 0 else 0,
        }

    return final_scores


def visualize_scores(scores, save_path="rouge_comparison.png"):
    """
    프롬프트 버전별 ROUGE 점수 비교 그래프 생성

    Args:
        scores (dict): evaluate_prompts의 반환값
        save_path (str): 그래프 저장 경로
    """
    versions = list(scores.keys())
    rouge1_scores = [scores[v]["rouge1"] for v in versions]
    rouge2_scores = [scores[v]["rouge2"] for v in versions]
    rougeL_scores = [scores[v]["rougeL"] for v in versions]

    x = range(len(versions))
    width = 0.25

    fig, ax = plt.subplots(figsize=(10, 6))

    ax.bar([i - width for i in x], rouge1_scores, width, label="ROUGE-1", color="#4A90D9")
    ax.bar(x, rouge2_scores, width, label="ROUGE-2", color="#E67E22")
    ax.bar([i + width for i in x], rougeL_scores, width, label="ROUGE-L", color="#27AE60")

    ax.set_xlabel("프롬프트 버전", fontsize=12)
    ax.set_ylabel("ROUGE Score", fontsize=12)
    ax.set_title("프롬프트 버전별 ROUGE 점수 비교", fontsize=14, fontweight="bold")
    ax.set_xticks(list(x))
    ax.set_xticklabels(versions)
    ax.legend()
    ax.grid(axis="y", alpha=0.3)

    # 막대 위에 점수 표시
    for i, v in enumerate(versions):
        ax.text(i - width, rouge1_scores[i] + 0.01, f"{rouge1_scores[i]:.3f}",
                ha="center", fontsize=9)
        ax.text(i, rouge2_scores[i] + 0.01, f"{rouge2_scores[i]:.3f}",
                ha="center", fontsize=9)
        ax.text(i + width, rougeL_scores[i] + 0.01, f"{rougeL_scores[i]:.3f}",
                ha="center", fontsize=9)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"✅ 그래프 저장 완료: {save_path}")


# ==============================
# 테스트 코드 (직접 실행 시)
# ==============================
if __name__ == "__main__":

    print("=" * 50)
    print("  ROUGE 평가 모듈 테스트")
    print("=" * 50)

    # 샘플 데이터: 3개 프롬프트 버전 × 3개 기사
    sample_results = {
        "버전A (단순)": [
            {
                "reference": "정부는 오늘 새로운 경제 정책을 발표했다 물가 안정과 경기 부양이 목표이다",
                "hypothesis": "정부가 경제 정책을 발표하였다 물가와 경기를 다룬다"
            },
            {
                "reference": "한국은행이 기준금리를 동결하기로 결정했다 인플레이션 우려가 주된 이유다",
                "hypothesis": "한국은행은 금리를 유지한다고 발표했다"
            },
            {
                "reference": "삼성전자가 신형 스마트폰을 공개했다 카메라 성능이 크게 향상되었다",
                "hypothesis": "삼성에서 새 폰을 선보였다 카메라가 좋아졌다"
            },
        ],
        "버전B (5W1H)": [
            {
                "reference": "정부는 오늘 새로운 경제 정책을 발표했다 물가 안정과 경기 부양이 목표이다",
                "hypothesis": "정부는 오늘 새로운 경제 정책을 발표했으며 물가 안정과 경기 부양을 목표로 한다"
            },
            {
                "reference": "한국은행이 기준금리를 동결하기로 결정했다 인플레이션 우려가 주된 이유다",
                "hypothesis": "한국은행은 기준금리를 동결하기로 결정했으며 인플레이션 우려가 그 이유이다"
            },
            {
                "reference": "삼성전자가 신형 스마트폰을 공개했다 카메라 성능이 크게 향상되었다",
                "hypothesis": "삼성전자는 신형 스마트폰을 공개했으며 카메라 성능이 향상되었다"
            },
        ],
        "버전C (상세)": [
            {
                "reference": "정부는 오늘 새로운 경제 정책을 발표했다 물가 안정과 경기 부양이 목표이다",
                "hypothesis": "오늘 정부에서 경제 정책 발표가 있었다 주요 내용은 물가와 경기 관련 사항이다"
            },
            {
                "reference": "한국은행이 기준금리를 동결하기로 결정했다 인플레이션 우려가 주된 이유다",
                "hypothesis": "한국은행에서 기준금리 동결을 결정하였다 인플레이션이 우려된다"
            },
            {
                "reference": "삼성전자가 신형 스마트폰을 공개했다 카메라 성능이 크게 향상되었다",
                "hypothesis": "삼성전자에서 새로운 스마트폰을 공개했다 카메라가 향상되었다"
            },
        ],
    }

    # 1. 종합 평가 수행
    print("\n📊 프롬프트 버전별 평균 ROUGE 점수")
    print("-" * 50)
    scores = evaluate_prompts(sample_results)

    for version, score in scores.items():
        print(f"\n{version}")
        print(f"  ROUGE-1: {score['rouge1']:.4f}")
        print(f"  ROUGE-2: {score['rouge2']:.4f}")
        print(f"  ROUGE-L: {score['rougeL']:.4f}")

    # 2. 최적 프롬프트 선정
    best_version = max(scores, key=lambda v: scores[v]["rouge1"])
    print("\n" + "=" * 50)
    print(f"🏆 최적 프롬프트: {best_version}")
    print(f"   ROUGE-1: {scores[best_version]['rouge1']:.4f}")
    print("=" * 50)

    # 3. 시각화
    print("\n📈 비교 그래프 생성 중...")
    visualize_scores(scores, "rouge_comparison.png")

    print("\n테스트 완료!")
