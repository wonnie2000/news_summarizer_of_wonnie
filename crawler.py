"""
뉴스 기사 크롤링 모듈 (강화 버전)
- 본문 외 노이즈(제목 중복, 사진 캡션, 기자 정보 등) 강력 제거
"""

import requests
from bs4 import BeautifulSoup
import re


# ==============================
# 노이즈 판별 함수
# ==============================

def is_noise_sentence(s):
    """
    한 문장이 노이즈인지 판단
    - 사진 캡션, 기자명, 광고 문구, 메뉴, 부가정보 등 걸러냄
    """
    if not s or len(s.strip()) < 15:
        return True

    s = s.strip()

    # 1. 사진/그림 캡션 패턴
    caption_patterns = [
        r"^사진\s*[=:]",
        r"^\[사진\]",
        r"^\(사진",
        r"^그림\s*[=:]",
        r"^\[그림\]",
        r"^이미지\s*[=:]",
        r"^\[이미지\]",
        r"^연합뉴스\s*$",
        r"^뉴스1\s*$",
        r"^뉴시스\s*$",
        r"^.*\s제공\s*$",
        r"^.*\s제공\.?\s*$",
        r"^촬영\s*[=:]",
    ]
    for p in caption_patterns:
        if re.search(p, s):
            return True

    # 2. 기자 정보 패턴
    reporter_patterns = [
        r"^[가-힣]{2,4}\s*기자",
        r"기자\s*[a-zA-Z0-9._%+-]+@",
        r"^[a-zA-Z0-9._%+-]+@",
        r"^[가-힣]{2,4}\s*\([a-zA-Z0-9._%+-]+@",
        r"^.{0,30}특파원\s*$",
        r"^.{0,30}통신원\s*$",
    ]
    for p in reporter_patterns:
        if re.search(p, s):
            return True

    # 3. 저작권/광고 문구
    copyright_patterns = [
        r"무단\s*전재",
        r"재배포\s*금지",
        r"저작권자",
        r"Copyright",
        r"ⓒ",
        r"©",
        r"AI 학습 및 활용 금지",
    ]
    for p in copyright_patterns:
        if re.search(p, s, re.IGNORECASE):
            return True

    # 4. UI/메뉴/SNS 관련
    ui_patterns = [
        r"^구독\s*하기",
        r"^팔로우",
        r"^좋아요",
        r"^공유\s*하기",
        r"^댓글",
        r"^더보기",
        r"^관련\s*기사",
        r"^많이\s*본\s*뉴스",
        r"^인기\s*기사",
        r"^추천\s*기사",
        r"^이\s*기사를",
        r"^프로필",
        r"^기자\s*페이지",
        r"^네이버",
        r"^카카오",
    ]
    for p in ui_patterns:
        if re.search(p, s):
            return True

    # 5. 너무 짧고 마침표가 없는 문장 (캡션 가능성 높음)
    if len(s) < 30 and not re.search(r"[.!?다요]$", s):
        # 단, 따옴표로 끝나면 인용문일 수 있으니 허용
        if not re.search(r"[\"\"'']$", s):
            return True

    # 6. 한글 비율이 너무 낮은 줄 (외국어, URL 등)
    korean_chars = len(re.findall(r"[가-힣]", s))
    total_chars = len(re.sub(r"\s", "", s))
    if total_chars > 0 and korean_chars / total_chars < 0.3:
        return True

    return False


def clean_text(text, title=""):
    """
    추출된 텍스트 정리 (강화 버전)
    - 제목 중복 제거
    - 문장 단위 노이즈 필터링
    """
    if not text:
        return ""

    # 기본 정리
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"^\s+", "", text, flags=re.MULTILINE)

    # 줄 단위로 분리
    lines = [line.strip() for line in text.split("\n")]

    # 제목과 동일하거나 비슷한 줄 제거
    title_clean = title.strip() if title else ""

    filtered = []
    for line in lines:
        if not line:
            continue
        # 제목과 중복되는 줄 스킵
        if title_clean and (line == title_clean or
                            (len(line) > 10 and line in title_clean) or
                            (len(title_clean) > 10 and title_clean in line)):
            continue
        # 노이즈 줄 스킵
        if is_noise_sentence(line):
            continue
        filtered.append(line)

    text = "\n".join(filtered)
    return text.strip()


# ==============================
# 사이트별 크롤러
# ==============================

def crawl_naver(url, soup):
    """네이버 뉴스 전용 크롤링"""
    title = ""
    text = ""

    title_tag = soup.select_one("#title_area") or soup.select_one(".media_end_head_headline")
    if title_tag:
        title = title_tag.get_text(strip=True)

    body_tag = soup.select_one("#dic_area") or soup.select_one("#newsct_article")
    if body_tag:
        # 사진/캡션/기자 영역 강력 제거
        for tag in body_tag.select(
            "script, style, "
            ".end_photo_org, span.end_photo_org, "
            ".vod_player_wrap, .vid_area, "
            "em.img_desc, .img_desc, "
            ".reporter_area, .copyright, "
            ".ab_photo, .end_photo_text, "
            "figure, figcaption, "
            ".artical-btm, "
            ".media_end_summary"
        ):
            tag.decompose()

        # <br>을 줄바꿈으로
        for br in body_tag.find_all("br"):
            br.replace_with("\n")

        text = body_tag.get_text(separator="\n")

    return title, text


def crawl_general(url, soup):
    """범용 뉴스 사이트 크롤링"""
    title = ""

    # 제목
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

    # 본문 영역 찾기
    article_tag = soup.select_one("article")
    if not article_tag:
        for selector in [
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
        ]:
            article_tag = soup.select_one(selector)
            if article_tag:
                break

    if not article_tag:
        # 최후의 수단
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

    text = ""
    if article_tag:
        # 본문 내 노이즈 요소 강력 제거
        for tag in article_tag.select(
            "script, style, nav, footer, header, aside, "
            "figure, figcaption, picture, "
            ".ad, .ads, .advertisement, .banner, "
            ".comment, .comments, .reply, "
            ".sns, .share, .social, "
            ".related, .recommend, .more, "
            ".reporter, .author, .byline, "
            ".caption, .photo, .image-caption, "
            ".photo-caption, .img-caption, "
            "[class*='ad-'], [class*='ads-'], [id*='ad-'], "
            "[class*='related'], [class*='recommend'], "
            "[class*='popular'], [class*='ranking'], "
            "[class*='caption'], [class*='credit']"
        ):
            tag.decompose()

        # <p> 태그가 충분히 있으면 <p>만 추출
        p_tags = article_tag.find_all("p")
        if p_tags and len(p_tags) >= 3:
            paragraphs = []
            for p in p_tags:
                p_text = p.get_text(strip=True)
                if len(p_text) >= 25:  # 너무 짧은 <p>는 캡션/광고일 가능성
                    paragraphs.append(p_text)
            text = "\n\n".join(paragraphs)
        else:
            # <br>을 줄바꿈으로
            for br in article_tag.find_all("br"):
                br.replace_with("\n")
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

        # 제목과 본문 정리
        title = title.strip() if title else ""
        text = clean_text(text, title)

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


if __name__ == "__main__":
    print("=" * 50)
    print("  뉴스 크롤링 모듈 테스트")
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
