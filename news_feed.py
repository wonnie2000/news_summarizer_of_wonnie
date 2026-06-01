"""
뉴스 피드 모듈
- 네이버 뉴스에서 주요 기사 헤드라인과 URL을 자동 수집
- 카테고리별 분류 제공
"""

import requests
from bs4 import BeautifulSoup
import re


# 네이버 뉴스 섹션 코드
NAVER_SECTIONS = {
    "정치": "100",
    "경제": "101",
    "사회": "102",
    "생활/문화": "103",
    "IT/과학": "105",
    "세계": "104",
}


def fetch_naver_headlines(section_name="정치", limit=8):
    """
    네이버 뉴스의 특정 섹션에서 헤드라인 목록을 가져옴

    Args:
        section_name (str): 섹션 이름 (정치/경제/사회/생활문화/IT과학/세계)
        limit (int): 가져올 기사 수

    Returns:
        list: [{"title": 제목, "url": URL, "press": 언론사}, ...]
    """
    section_id = NAVER_SECTIONS.get(section_name, "100")
    url = f"https://news.naver.com/section/{section_id}"

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        response.encoding = response.apparent_encoding

        soup = BeautifulSoup(response.text, "html.parser")

        articles = []
        seen_urls = set()

        # 네이버 뉴스 섹션 페이지의 기사 링크 추출
        # 여러 선택자를 시도해서 안정성 확보
        selectors = [
            "a.sa_text_title",                       # 헤드라인 기사
            "a[href*='n.news.naver.com/mnews/article']",
            "a[href*='n.news.naver.com/article']",
        ]

        candidates = []
        for selector in selectors:
            candidates.extend(soup.select(selector))

        for link in candidates:
            href = link.get("href", "")
            if not href:
                continue

            # 절대경로 변환
            if href.startswith("/"):
                href = "https://news.naver.com" + href
            elif not href.startswith("http"):
                continue

            # 실제 기사 URL만 (article 포함)
            if "article" not in href:
                continue

            # 중복 제거
            if href in seen_urls:
                continue
            seen_urls.add(href)

            # 제목 추출
            title = link.get_text(strip=True)
            if not title or len(title) < 10:
                continue

            # 언론사 추출 시도
            press = ""
            parent = link.find_parent()
            if parent:
                press_tag = parent.select_one(".sa_text_press, .press_name, .info_press")
                if press_tag:
                    press = press_tag.get_text(strip=True)

            articles.append({
                "title": title,
                "url": href,
                "press": press,
            })

            if len(articles) >= limit:
                break

        return articles

    except Exception as e:
        print(f"피드 수집 실패: {e}")
        return []


def fetch_all_sections(limit_per_section=4):
    """
    모든 섹션의 헤드라인을 한 번에 가져옴

    Returns:
        dict: {섹션이름: [기사 리스트]}
    """
    result = {}
    for section_name in NAVER_SECTIONS.keys():
        result[section_name] = fetch_naver_headlines(section_name, limit_per_section)
    return result


if __name__ == "__main__":
    print("=" * 50)
    print("  뉴스 피드 모듈 테스트")
    print("=" * 50)

    for section in ["정치", "경제", "IT/과학"]:
        print(f"\n▶ {section}")
        articles = fetch_naver_headlines(section, limit=5)
        for i, a in enumerate(articles, 1):
            print(f"  {i}. {a['title']}")
            print(f"     {a['url']}")
            if a['press']:
                print(f"     [{a['press']}]")
