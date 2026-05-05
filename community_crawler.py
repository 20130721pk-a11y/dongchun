import requests
from bs4 import BeautifulSoup
import os
import json
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime
import time

load_dotenv()

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

KEYWORDS = ["알케론", "arkheron", "Arkheron", "포트나이트", "이터널리턴", "배틀그라운드", "발로란트", "리그오브레전드"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


GAME_KEYWORDS = [
    "게임", "게이머", "게임사", "플레이", "출시", "업데이트", "패치", "서버",
    "캐릭터", "아이템", "스킬", "pvp", "pve", "rpg", "fps", "moba",
    "mmorpg", "모바일게임", "스팀", "콘솔", "pc방", "e스포츠", "esports",
    "대회", "시즌", "배틀", "테스트", "베타", "신작", "런칭", "섭종",
    "드림에이지", "알케론", "아키텍트", "포트나이트", "발로란트",
    "배틀그라운드", "pubg", "valorant", "fortnite", "이터널리턴",
    "리그오브레전드", "lol", "steam", "gaming", "game", "gameplay"
]

def is_game_related(title, summary=""):
    text = (title + " " + (summary or "")).lower()
    return any(kw.lower() in text for kw in GAME_KEYWORDS)

def analyze_sentiment(title, content=""):
    try:
        text = f"제목: {title}\n내용: {content[:300] if content else ''}"
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "Content-Type": "application/json",
                "x-api-key": os.getenv("ANTHROPIC_API_KEY", ""),
                "anthropic-version": "2023-06-01"
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 150,
                "messages": [{
                    "role": "user",
                    "content": f"다음 게임 커뮤니티 게시글의 감성을 분석하세요.\n{text}\n\n반드시 아래 JSON만 응답:\n{{\"sentiment\": \"긍정\" or \"부정\" or \"중립\", \"reason\": \"한줄이유\"}}"
                }]
            },
            timeout=15
        )
        result = response.json()
        parsed = json.loads(result["content"][0]["text"])
        return parsed.get("sentiment", "중립"), parsed.get("reason", "")
    except:
        return "중립", ""

def save_post(title, content, url, community, views, comments, keyword, posted_at):
    sentiment, reason = analyze_sentiment(title, content)
    try:
        supabase.table("community_posts").insert({
            "title": title,
            "content": content[:1000] if content else None,
            "url": url,
            "community": community,
            "views": views,
            "comments": comments,
            "sentiment": sentiment,
            "sentiment_reason": reason,
            "keyword": keyword,
            "posted_at": posted_at,
        }).execute()
        return True, sentiment
    except Exception as e:
        if "duplicate" in str(e).lower() or "unique" in str(e).lower():
            return False, None
        print(f"  ❌ 저장 실패: {e}")
        return False, None

def crawl_inven(keyword):
    print(f"\n📡 인벤 - {keyword} 수집 중...")
    results = []
    try:
        encoded = requests.utils.quote(keyword)
        url = f"https://www.inven.co.kr/search/webzine/top/{encoded}"
        response = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        links = soup.find_all('a', href=True)
        seen = set()
        for a in links:
            href = a.get('href', '')
            title = a.get_text(strip=True)
            if (keyword in title or keyword.lower() in title.lower()) and len(title) > 5 and href not in seen:
                if 'inven.co.kr' in href:
                    seen.add(href)
                    results.append({'title': title[:100], 'url': href, 'posted_at': None, 'views': 0, 'comments': 0})
            if len(results) >= 100:
                break
    except Exception as e:
        print(f"  ⚠️ 인벤 실패: {e}")
    return results

def crawl_ruliweb(keyword):
    print(f"\n📡 루리웹 - {keyword} 수집 중...")
    results = []
    try:
        url = f"https://bbs.ruliweb.com/search?q={requests.utils.quote(keyword)}"
        response = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        links = soup.find_all('a', href=True)
        seen = set()
        for a in links:
            href = a.get('href', '')
            title = a.get_text(strip=True)
            if ('read' in href or '/news/' in href) and title and len(title) > 5 and href not in seen:
                if keyword.lower() in title.lower():
                    seen.add(href)
                    from datetime import datetime as dt
                try:
                    posted_at = dt.now().isoformat()
                except:
                    posted_at = None
                results.append({'title': title[:100], 'url': href, 'posted_at': posted_at, 'views': 0, 'comments': 0})
            if len(results) >= 100:
                break
    except Exception as e:
        print(f"  ⚠️ 루리웹 실패: {e}")
    return results

def crawl_dcinside(keyword):
    print(f"\n📡 디시인사이드 - {keyword} 수집 중...")
    results = []
    try:
        # 알케론은 마이너갤 직접, 나머지는 검색
        if keyword.lower() in ['알케론', 'arkheron']:
            urls_to_crawl = [f"https://gall.dcinside.com/mgallery/board/lists/?id=arkheron&page={page}" for page in range(1, 4)]
            for url in urls_to_crawl:
                from bs4 import BeautifulSoup
                response = requests.get(url, headers=HEADERS, timeout=10)
                soup = BeautifulSoup(response.text, 'html.parser')
                items = soup.select('tr.ub-content')
                if not items:
                    items = soup.select('tbody tr')
                for item in items:
                    title_tag = item.select_one('td.gall_tit a')
                    if not title_tag:
                        continue
                    title = title_tag.get_text(strip=True)
                    href = title_tag.get('href', '')
                    if not href.startswith('http'):
                        href = 'https://gall.dcinside.com' + href
                    view_tag = item.select_one('td.gall_count')
                    views = int(view_tag.get_text(strip=True).replace(',', '').replace('-', '0') or 0) if view_tag else 0
                    comment_tag = item.select_one('td.gall_comment')
                    comments = int(comment_tag.get_text(strip=True).replace(',', '').replace('-', '0') or 0) if comment_tag else 0
                    date_tag = item.select_one('td.gall_date')
                    posted_at_raw = date_tag.get('title', date_tag.get_text(strip=True)) if date_tag else None
                    try:
                        if posted_at_raw and len(posted_at_raw) == 8 and '/' in posted_at_raw:
                            parts = posted_at_raw.split('/')
                            posted_at = f"20{parts[0]}-{parts[1]}-{parts[2]}"
                        else:
                            posted_at = posted_at_raw
                    except:
                        posted_at = None
                    if title and len(title) > 2:
                        results.append({'title': title[:100], 'url': href, 'posted_at': posted_at, 'views': views, 'comments': comments})
                if len(results) >= 100:
                    break
        else:
            # 경쟁작 키워드는 마이너갤 직접 크롤링
            GALL_IDS = {
                '포트나이트': 'fortnite',
                '발로란트': 'valorant',
                '배틀그라운드': 'pubg',
                '이터널리턴': 'eternalreturn',
                '리그오브레전드': 'leagueoflegends',
            }
            gall_id = GALL_IDS.get(keyword)
            if not gall_id:
                return results
            from bs4 import BeautifulSoup
            for page in range(1, 4):
                url = f"https://gall.dcinside.com/mgallery/board/lists/?id={gall_id}&page={page}"
                response = requests.get(url, headers=HEADERS, timeout=10)
                soup = BeautifulSoup(response.text, 'html.parser')
                items = soup.select('tr.ub-content')
                if not items:
                    items = soup.select('tbody tr')
                for item in items:
                    title_tag = item.select_one('td.gall_tit a')
                    if not title_tag:
                        continue
                    title = title_tag.get_text(strip=True)
                    href = title_tag.get('href', '')
                    if not href.startswith('http'):
                        href = 'https://gall.dcinside.com' + href
                    view_tag = item.select_one('td.gall_count')
                    views = int(view_tag.get_text(strip=True).replace(',', '').replace('-', '0') or 0) if view_tag else 0
                    comment_tag = item.select_one('td.gall_comment')
                    comments = int(comment_tag.get_text(strip=True).replace(',', '').replace('-', '0') or 0) if comment_tag else 0
                    date_tag = item.select_one('td.gall_date')
                    posted_at_raw = date_tag.get('title', date_tag.get_text(strip=True)) if date_tag else None
                    try:
                        if posted_at_raw and len(posted_at_raw) == 8 and '/' in posted_at_raw:
                            parts = posted_at_raw.split('/')
                            posted_at = f"20{parts[0]}-{parts[1]}-{parts[2]}"
                        else:
                            posted_at = posted_at_raw
                    except:
                        posted_at = None
                    if title and len(title) > 2:
                        results.append({'title': title[:100], 'url': href, 'posted_at': posted_at, 'views': views, 'comments': comments})
                if len(results) >= 100:
                    break
        for page in range(1, 4):
            url = f"https://gall.dcinside.com/mgallery/board/lists/?id=arkheron&page={page}"
            response = requests.get(url, headers=HEADERS, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            items = soup.select('tr.ub-content')
            if not items:
                items = soup.select('tbody tr')
            for item in items:
                title_tag = item.select_one('td.gall_tit a')
                if not title_tag:
                    continue
                title = title_tag.get_text(strip=True)
                href = title_tag.get('href', '')
                if not href.startswith('http'):
                    href = 'https://gall.dcinside.com' + href
                view_tag = item.select_one('td.gall_count')
                views = int(view_tag.get_text(strip=True).replace(',', '').replace('-', '0') or 0) if view_tag else 0
                comment_tag = item.select_one('td.gall_comment')
                comments = int(comment_tag.get_text(strip=True).replace(',', '').replace('-', '0') or 0) if comment_tag else 0
                date_tag = item.select_one('td.gall_date')
                posted_at_raw = date_tag.get('title', date_tag.get_text(strip=True)) if date_tag else None
                try:
                    if posted_at_raw and len(posted_at_raw) == 8 and '/' in posted_at_raw:
                        parts = posted_at_raw.split('/')
                        posted_at = f"20{parts[0]}-{parts[1]}-{parts[2]}"
                    else:
                        posted_at = posted_at_raw
                except:
                    posted_at = None
                if title and len(title) > 2:
                    results.append({'title': title[:100], 'url': href, 'posted_at': posted_at, 'views': views, 'comments': comments})
            if len(results) >= 100:
                break
    except Exception as e:
        print(f"  ⚠️ 디시인사이드 실패: {e}")
    return results[:100]

def crawl_naver_cafe(keyword):
    print(f"\n📡 네이버 카페 - {keyword} 수집 중...")
    results = []
    try:
        client_id = os.getenv("NAVER_CLIENT_ID")
        client_secret = os.getenv("NAVER_CLIENT_SECRET")
        url = "https://openapi.naver.com/v1/search/cafearticle.json"
        headers = {**HEADERS, "X-Naver-Client-Id": client_id, "X-Naver-Client-Secret": client_secret}
        params = {"query": keyword, "display": 1000, "sort": "date"}
        response = requests.get(url, headers=headers, params=params, timeout=10)
        items = response.json().get("items", [])
        import re
        for item in items:
            title = re.sub('<[^>]+>', '', item.get("title", ""))
            link = item.get("link", "")
            posted_at = item.get("postdate", None)
            results.append({'title': title, 'url': link, 'posted_at': posted_at, 'views': 0, 'comments': 0})
    except Exception as e:
        print(f"  ⚠️ 네이버 카페 실패: {e}")
    return results

def crawl_arcalive(keyword):
    print(f"\n📡 아카라이브 - {keyword} 수집 중...")
    results = []
    try:
        encoded = requests.utils.quote(keyword)
        url = f"https://arca.live/b/breaking?keyword={encoded}"
        response = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        items = soup.select('a.vrow.column:not(.notice)')
        for item in items[:100]:
            title_tag = item.select_one('.col-title .title')
            if not title_tag:
                continue
            title = title_tag.get_text(strip=True)
            link = 'https://arca.live' + item.get('href', '')
            view_tag = item.select_one('.col-view')
            views = int(view_tag.get_text(strip=True).replace(',', '').replace('-', '0') or 0) if view_tag else 0
            date_tag = item.select_one('time')
            posted_at = date_tag.get('datetime') if date_tag else None
            results.append({'title': title, 'url': link, 'posted_at': posted_at, 'views': views, 'comments': 0})
    except Exception as e:
        print(f"  ⚠️ 아카라이브 실패: {e}")
    return results

def crawl_thisisgame(keyword):
    print(f"\n📡 디스이즈게임 - {keyword} 수집 중...")
    results = []
    try:
        client_id = os.getenv("NAVER_CLIENT_ID")
        client_secret = os.getenv("NAVER_CLIENT_SECRET")
        url = "https://openapi.naver.com/v1/search/news.json"
        headers = {**HEADERS, "X-Naver-Client-Id": client_id, "X-Naver-Client-Secret": client_secret}
        params = {"query": f"{keyword} thisisgame", "display": 100, "sort": "date"}
        response = requests.get(url, headers=headers, params=params, timeout=10)
        items = response.json().get("items", [])
        import re
        for item in items:
            link = item.get("originallink", item.get("link", ""))
            if "thisisgame.com" not in link:
                continue
            title = re.sub('<[^>]+>', '', item.get("title", ""))
            posted_at = item.get("pubDate", None)
            results.append({'title': title[:100], 'url': link, 'posted_at': posted_at, 'views': 0, 'comments': 0})
    except Exception as e:
        print(f"  ⚠️ 디스이즈게임 실패: {e}")
    return results

def crawl():
    print(f"\n🔍 커뮤니티 크롤링 시작: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    total, saved, skipped = 0, 0, 0

    crawlers = [
        ("인벤", crawl_inven),
        ("루리웹", crawl_ruliweb),
        ("디시인사이드", crawl_dcinside),
        ("네이버카페", crawl_naver_cafe),
        ("아카라이브", crawl_arcalive),
        ("디스이즈게임", crawl_thisisgame),
    ]

    for keyword in KEYWORDS:
        for community, crawler in crawlers:
            posts = crawler(keyword)
            print(f"  → {len(posts)}개 발견")
            for post in posts:
                total += 1
                if not is_game_related(post['title']):
                    skipped += 1
                    continue
                success, sentiment = save_post(
                    post['title'], "", post['url'], community,
                    post['views'], post['comments'], keyword, post['posted_at']
                )
                if success:
                    saved += 1
                    print(f"  ✅ [{sentiment}] {post['title'][:40]}...")
                else:
                    skipped += 1
                time.sleep(0.3)

    print(f"\n✨ 완료! 총 {total}개 수집 / {saved}개 저장 / {skipped}개 중복 스킵")

if __name__ == "__main__":
    crawl()
