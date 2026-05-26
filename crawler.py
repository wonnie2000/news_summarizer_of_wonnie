"""
뉴스 기사 크롤링 모듈 (개선 버전)
- requests + BeautifulSoup 기반
- 본문 추출 정확도 향상 (광고/추천기사 등 노이즈 제거 강화)
"""

import requests
from bs4 import BeautifulSoup
import re


def clean_text(text):
    """추출된 텍스트 정리"""
    if not text:
        return ""

    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"^\s+", "", text, flags=re.MULTILINE)

    # 강화된 노이즈 패턴 제거
    noise_patterns = [
        r"무단전재.*?재배포.*?금지",
        r"저작권자.*?무단.*?금지",
        r"\[.*?기자\]",
        r"\(.*?@.*?\)",
        r"▶.*",
        r"Copyright.*",
        r"Copyrights.*",
        r"ⓒ.*",
        r"©.*",
        r"포토뉴스.*",
        r"관련기사.*",
        r"많이 본 기사.*",
        r"이 기사를 추천합니다.*",
        r"좋아요\s*\d+",
        r"공감\s*\d+",
        r"댓글\s*\d+",
        r"#\S+",  # 해시태그
    ]
    for pattern in noise_patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    # 줄 단위로 필터링: 너무 짧거나 노이즈성 줄 제거
    lines = text.split("\n")
    filtered = []
    skip_keywords = [
        "구독", "팔로우", "좋아요", "공유", "댓글", "이메일", "전화",
        "기자페이지", "프로필", "응원합니다", "비추천", "추천",
        "더보기", "관련 기사", "이전 기사", "다음 기사",
        "광고", "AD", "sponsored",
    ]
    for line in lines:
        s = line.strip()
        # 빈 줄은 보존 (문단 구분용)
        if not s:
            filtered.append("")
            continue
        # 너무 짧은 줄(15자 미만)이고 노이즈 키워드 포함 시 제거
        if len(s) < 15 and any(kw in s for kw in skip_keywords):
            continue
        # 노이즈 키워드만 있는 줄 제거
        if any(s == kw or s.startswith(kw + " ") for kw in skip_keywords):
            continue
        filtered.append(s)

    text = "\n".join(filtered)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def crawl_naver(url, soup):
    """네이버 뉴스 전용 크롤링"""
    title = ""
    text = ""

    title_tag = soup.select_one("#title_area") or soup.select_one(".media_end_head_headline")
    if title_tag:
        title = title_tag.get_text(strip=True)

    body_tag = soup.select_one("#dic_area") or soup.select_one("#newsct_article")
    if body_tag:
        # 불필요 요소 제거 강화
        for tag in body_tag.select(
            "script, style, .ad, .photo_caption, span.end_photo_org, "
            ".vod_player_wrap, .vid_area, .img_desc, em.img_desc, "
            "div.vod_player_wrap, .reporter_area, .copyright"
        ):
            tag.decompose()
        text = body_tag.get_text(separator="\n")

    return title, text


def crawl_general(url, soup):
    """범용 뉴스 사이트 크롤링"""
    title = ""
    text = ""

    # 제목 추출
    og_title = soup.select_one('meta[property="og:title"]')
    if og_title and og_title.get("content"):
        title = og_title["content"].strip()

    if not title:
        h1 = soup.select_one("h1")
        if h1:
            title = h1.get_text(strip=True)

    if not title:
        title_tag = soup.select_one("title")
        if title_tag:
            title = title_tag.get_text(strip=True)

    # ── 본문 추출 ──
    article_tag = soup.select_one("article")

    if not article_tag:
        body_selectors = [
            "[class*='article-body']",
            "[class*='article_body']",
            "[class*='articleBody']",
            "[class*='story-body']",
            "[class*='news-body']",
            "[class*='news_body']",
            "[class*='content-body']",
            "[id*='articleBody']",
            "[id*='article-body']",
            ".article",
            ".post-content",
            ".entry-content",
        ]
        for selector in body_selectors:
            article_tag = soup.select_one(selector)
            if article_tag:
                break

    # 최후의 수단: 가장 긴 <p> 묶음을 가진 div
    if not article_tag:
        all_divs = soup.find_all("div")
        best_div = None
        best_length = 0
        for div in all_divs:
            p_tags = div.find_all("p", recursive=False)
            total_text = " ".join(p.get_text() for p in p_tags)
            if len(total_text) > best_length:
                best_length = len(total_text)
                best_div = div
        if best_div and best_length > 200:
            article_tag = best_div

    if article_tag:
        # 본문 내 불필요 요소 강화 제거
        for tag in article_tag.select(
            "script, style, nav, footer, header, aside, "
            ".ad, .ads, .advertisement, .banner, "
            ".comment, .comments, .reply, "
            ".sns, .share, .social, "
            ".related, .recommend, .more, "
            ".reporter, .author, .byline, "
            ".caption, .photo, .image-caption, "
            "[class*='ad-'], [class*='ads-'], [id*='ad-'], "
            "[class*='related'], [class*='recommend'], "
            "[class*='popular'], [class*='ranking']"
        ):
            tag.decompose()

        # <p> 태그가 있으면 <p>만 추출 (본문은 보통 <p>에 들어있음)
        p_tags = article_tag.find_all("p")
        if p_tags and len(p_tags) >= 2:
            paragraphs = []
            for p in p_tags:
                p_text = p.get_text(strip=True)
                # 너무 짧은 문단은 무시 (캡션, 광고 등)
                if len(p_text) >= 20:
                    paragraphs.append(p_text)
            text = "\n\n".join(paragraphs)
        else:
            text = article_tag.get_text(separator="\n")

    return title, text


def crawl_news(url):
    """메인 크롤링 함수"""
    if not url or not url.startswith(("http://", "https://")):
        return {
            "success": False,
            "error": "유효하지 않은 URL입니다. http:// 또는 https://로 시작하는 URL을 입력해주세요.",
            "url": url
        }

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        response.encoding = response.apparent_encoding

        soup = BeautifulSoup(response.text, "html.parser")

        if "naver.com" in url:
            title, text = crawl_naver(url, soup)
        else:
            title, text = crawl_general(url, soup)

        title = clean_text(title)
        text = clean_text(text)

        if len(text) < 100:
            return {
                "success": False,
                "error": f"본문 추출 실패: 추출된 텍스트가 너무 짧습니다. ({len(text)}자)",
                "url": url
            }

        return {
            "success": True,
            "title": title,
            "text": text,
            "url": url
        }

    except requests.exceptions.Timeout:
        return {"success": False, "error": "요청 시간 초과", "url": url}
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": "연결 실패", "url": url}
    except requests.exceptions.HTTPError as e:
        return {"success": False, "error": f"HTTP 에러: {e.response.status_code}", "url": url}
    except Exception as e:
        return {"success": False, "error": f"크롤링 오류: {str(e)}", "url": url}


# ==============================
# 테스트 코드
# ==============================
if __name__ == "__main__":
    print("=" * 50)
    print("  뉴스 크롤링 모듈 테스트 (개선 버전)")
    print("=" * 50)

    while True:
        u = input("\nURL 입력 (종료: q): ").strip()
        if u.lower() == "q":
            break
        result = crawl_news(u)
        if result["success"]:
            print(f"\n제목: {result['title']}")
            print(f"본문 ({len(result['text'])}자):")
            print(result["text"][:500])
        else:
            print(f"\n실패: {result['error']}")
