import feedparser
import requests
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client
import os
import urllib.parse

load_dotenv()

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

KEYWORDS = {
    "자사": ["드림에이지", "DRIMAGE", "아키텍트", "알케론", "arkheron"],
    "경쟁사": ["포트나이트", "리그오브레전드", "롤", "이터널리턴", "배틀그라운드", "PUBG", "발로란트", "Valorant"],
    "업계": ["모바일게임", "콘솔게임", "스팀", "STEAM", "신작", "게임사", "서비스종료", "PC게임", "사전예약", "런칭"]
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def make_google_news_url(keyword):
    encoded = urllib.parse.quote(keyword)
    return f"https://news.google.com/rss/search?q={encoded}&hl=ko&gl=KR&ceid=KR:ko"

SOURCES = [
    {"name": "Google News - 드림에이지", "url": make_google_news_url("드림에이지")},
    {"name": "Google News - 아키텍트게임", "url": make_google_news_url("아키텍트 게임")},
    {"name": "Google News - 알케론", "url": make_google_news_url("알케론")},
    {"name": "Google News - 포트나이트", "url": make_google_news_url("포트나이트")},
    {"name": "Google News - 이터널리턴", "url": make_google_news_url("이터널리턴")},
    {"name": "Google News - 배틀그라운드", "url": make_google_news_url("배틀그라운드")},
    {"name": "Google News - 발로란트", "url": make_google_news_url("발로란트")},
    {"name": "Google News - 모바일게임", "url": make_google_news_url("모바일게임 신작")},
    {"name": "Google News - 게임업계", "url": make_google_news_url("게임사 신작")},

    {"name": "네이버 - 드림에이지", "url": "https://search.naver.com/rss.naver?where=news&query=%EB%93%9C%EB%A6%BC%EC%97%90%EC%9D%B4%EC%A7%80"},
    {"name": "네이버 - 아키텍트게임", "url": "https://search.naver.com/rss.naver?where=news&query=%EC%95%84%ED%82%A4%ED%85%8D%ED%8A%B8+%EA%B2%8C%EC%9E%84"},
    {"name": "네이버 - 알케론", "url": "https://search.naver.com/rss.naver?where=news&query=%EC%95%8C%EC%BC%80%EB%A1%A0"},
    {"name": "네이버 - 포트나이트", "url": "https://search.naver.com/rss.naver?where=news&query=%ED%8F%AC%ED%8A%B8%EB%82%98%EC%9D%B4%ED%8A%B8"},
    {"name": "네이버 - 이터널리턴", "url": "https://search.naver.com/rss.naver?where=news&query=%EC%9D%B4%ED%84%B0%EB%84%90%EB%A6%AC%ED%84%B4"},
    {"name": "네이버 - 배틀그라운드", "url": "https://search.naver.com/rss.naver?where=news&query=%EB%B0%B0%ED%8B%80%EA%B7%B8%EB%9D%BC%EC%9A%B4%EB%93%9C"},
    {"name": "네이버 - 발로란트", "url": "https://search.naver.com/rss.naver?where=news&query=%EB%B0%9C%EB%A1%9C%EB%9E%80%ED%8A%B8"},
    {"name": "네이버 - 모바일게임신작", "url": "https://search.naver.com/rss.naver?where=news&query=%EB%AA%A8%EB%B0%94%EC%9D%BC%EA%B2%8C%EC%9E%84+%EC%8B%A0%EC%9E%91"},
    {"name": "네이버 - 게임업계", "url": "https://search.naver.com/rss.naver?where=news&query=%EA%B2%8C%EC%9E%84%EC%82%AC+%EC%8B%A0%EC%9E%91"},
    {"name": "인벤", "url": "https://www.inven.co.kr/rss/news.php"},
    {"name": "루리웹", "url": "https://bbs.ruliweb.com/news/rss"},
]


def search_naver_news(keyword, client_id, client_secret, display=10):
    url = "https://openapi.naver.com/v1/search/news.json"
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret
    }
    params = {"query": keyword, "display": display, "sort": "date"}
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        items = response.json().get("items", [])
        return items
    except Exception as e:
        print(f"  ⚠️ 네이버 요청 실패: {e}")
        return []


GAME_KEYWORDS = [
    "게임", "게이머", "게임사", "플레이", "출시", "업데이트", "패치", "서버",
    "캐릭터", "아이템", "스킬", "퀘스트", "pvp", "pve", "rpg", "fps", "moba",
    "mmorpg", "모바일게임", "스팀", "콘솔", "pc방", "e스포츠", "esports",
    "대회", "시즌", "배틀", "테스트", "베타", "알파", "얼리액세스", "정식출시",
    "서비스종료", "섭종", "신작", "런칭", "게임쇼", "지스타", "gdc", "tgs",
    "개발사", "퍼블리셔", "스튜디오", "드림에이지", "알케론", "아키텍트",
    "포트나이트", "발로란트", "배틀그라운드", "pubg", "valorant", "fortnite",
    "이터널리턴", "리그오브레전드", "lol", "롤", "스팀", "steam",
    "닌텐도", "플레이스테이션", "xbox", "블리자드", "넥슨", "엔씨소프트",
    "넷마블", "크래프톤", "카카오게임즈", "위메이드", "컴투스", "게임빌",
    "인벤", "루리웹", "gaming", "game"
]

def is_game_related(title, summary=""):
    text = (title + " " + (summary or "")).lower()
    return any(kw.lower() in text for kw in GAME_KEYWORDS)

def get_category(title, summary=""):
    text = (title + " " + (summary or "")).lower()
    for category, keywords in KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text:
                return category, [kw]
    return "업계", []

def get_tags(title, summary=""):
    text = (title + " " + (summary or "")).lower()
    found = []
    for keywords in KEYWORDS.values():
        for kw in keywords:
            if kw.lower() in text:
                found.append(kw)
    return found

def parse_feed(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        feed = feedparser.parse(response.content)
        return feed.entries
    except Exception as e:
        print(f"  ⚠️ 요청 실패: {e}")
        return []

def crawl():
    print(f"\n🚀 크롤링 시작: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    total, saved, skipped = 0, 0, 0

    for source in SOURCES:
        print(f"\n📡 {source['name']} 수집 중...")
        entries = parse_feed(source["url"])
        print(f"  → {len(entries)}개 발견")

        for entry in entries[:10]:
            total += 1
            title = entry.get("title", "")
            url = entry.get("link", "")
            summary = entry.get("summary", "")
            published = None

            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                try:
                    published = datetime(*entry.published_parsed[:6]).isoformat()
                except:
                    pass

            category, _ = get_category(title, summary)
            tags = get_tags(title, summary)

            try:
                supabase.table("news").insert({
                    "title": title,
                    "url": url,
                    "summary": summary[:500] if summary else None,
                    "source": source["name"],
                    "category": category,
                    "tags": tags,
                    "published_at": published,
                }).execute()
                saved += 1
                print(f"  ✅ [{category}] {title[:40]}...")
            except Exception as e:
                if "duplicate" in str(e).lower() or "unique" in str(e).lower():
                    skipped += 1
                else:
                    print(f"  ❌ 저장 실패: {e}")


    # 네이버 뉴스 API
    naver_id = os.getenv("NAVER_CLIENT_ID")
    naver_secret = os.getenv("NAVER_CLIENT_SECRET")
    naver_keywords = {
        "자사": ["드림에이지", "아키텍트 게임", "알케론"],
        "경쟁사": ["포트나이트", "이터널리턴", "배틀그라운드", "발로란트"],
        "업계": ["모바일게임 신작", "게임사 신작", "서비스종료 게임", "PC게임 런칭", "게임 사전예약"]
    }
    for category, keywords in naver_keywords.items():
        for keyword in keywords:
            print(f"\n📡 네이버 - {keyword} 수집 중...")
            items = search_naver_news(keyword, naver_id, naver_secret)
            print(f"  → {len(items)}개 발견")
            for item in items:
                total += 1
                import re
                title = re.sub('<[^>]+>', '', item.get("title", ""))
                url = item.get("link", "")
                summary = re.sub('<[^>]+>', '', item.get("description", ""))
                published = item.get("pubDate", None)
                tags = get_tags(title, summary)
                try:
                    supabase.table("news").insert({
                        "title": title,
                        "url": url,
                        "summary": summary[:500] if summary else None,
                        "source": f"네이버 - {keyword}",
                        "category": category,
                        "tags": tags,
                        "published_at": published,
                    }).execute()
                    saved += 1
                    print(f"  ✅ [{category}] {title[:40]}...")
                except Exception as e:
                    if "duplicate" in str(e).lower() or "unique" in str(e).lower():
                        skipped += 1
                    else:
                        print(f"  ❌ 저장 실패: {e}")


    # 네이버 블로그 API
    naver_blog_keywords = {
        "자사": ["드림에이지", "아키텍트 게임", "알케론"],
        "경쟁사": ["포트나이트", "리그오브레전드", "이터널리턴", "배틀그라운드", "발로란트"],
        "업계": ["모바일게임 신작", "게임 출시"]
    }
    for category, keywords in naver_blog_keywords.items():
        for keyword in keywords:
            print(f"\n📡 네이버 블로그 - {keyword} 수집 중...")
            url = "https://openapi.naver.com/v1/search/blog.json"
            headers = {"X-Naver-Client-Id": naver_id, "X-Naver-Client-Secret": naver_secret}
            params = {"query": keyword, "display": 10, "sort": "date"}
            try:
                import re
                response = requests.get(url, headers=headers, params=params, timeout=10)
                items = response.json().get("items", [])
                print(f"  → {len(items)}개 발견")
                for item in items:
                    total += 1
                    title = re.sub('<[^>]+>', '', item.get("title", ""))
                    link = item.get("link", "")
                    description = re.sub('<[^>]+>', '', item.get("description", ""))
                    published = item.get("postdate", None)
                    tags = get_tags(title, description)
                    try:
                        supabase.table("news").insert({
                            "title": title,
                            "url": link,
                            "summary": description[:500] if description else None,
                            "source": f"네이버블로그 - {keyword}",
                            "category": category,
                            "tags": tags,
                            "published_at": published,
                        }).execute()
                        saved += 1
                        print(f"  ✅ [{category}] {title[:40]}...")
                    except Exception as e:
                        if "duplicate" in str(e).lower() or "unique" in str(e).lower():
                            skipped += 1
                        else:
                            print(f"  ❌ 저장 실패: {e}")
            except Exception as e:
                print(f"  ⚠️ 블로그 요청 실패: {e}")

    print(f"\n✨ 완료! 총 {total}개 수집 / {saved}개 저장 / {skipped}개 중복 스킵")

if __name__ == "__main__":
    crawl()

