import feedparser
import requests
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client
import os
import re
import urllib.parse

load_dotenv()

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

KEYWORDS = {
    "자사": [
        "드림에이지", "DRIMAGE", "아키텍트", "알케론", "arkheron",
        "본파이어 스튜디오", "Bonfire Studios"
    ],
    "경쟁사": [
        "포트나이트", "리그오브레전드", "롤", "이터널리턴",
        "배틀그라운드", "PUBG", "발로란트", "Valorant",
        "LCK", "VCT", "블랙서바이벌"
    ],
    "업계": ['신작', '런칭', '사전예약', '얼리액세스', '지스타', '배틀로얄 신작', 'MMORPG 신작', '게임스컴', '도쿄게임쇼', 'GDC', '크로스플랫폼 게임', '스팀 인기 게임']
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# 게임 전문 미디어 소스 (이 소스는 필터 없이 통과)
TRUSTED_GAME_SOURCES = ["인벤", "루리웹"]

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
    {"name": "디스이즈게임", "url": "https://www.thisisgame.com/webzine/game/nboard/5/?rss=1"},
    {"name": "게임조선", "url": "https://www.gamechosun.co.kr/rss/"},
    {"name": "게임메카", "url": "https://www.gamemeca.com/feed/"},
]

def search_naver_news(keyword, client_id, client_secret, display=100):
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

# 게임 전용 키워드 (범용 단어 제외)
GAME_SPECIFIC_KEYWORDS = [
    # 게임 장르/형식
    "게임", "게이머", "게임사", "모바일게임", "온라인게임", "인디게임",
    "pvp", "pve", "rpg", "fps", "moba", "mmorpg", "배틀로얄",
    "pc방", "e스포츠", "esports",
    # 게임 액션
    "패치노트", "핫픽스", "얼리액세스", "오픈베타", "cbt", "obt",
    "서비스종료", "섭종", "게임쇼", "지스타", "gdc", "tgs",
    "게임런칭", "게임출시", "신작게임",
    # 게임 콘텐츠
    "캐릭터", "아이템", "스킬", "퀘스트", "레이드", "던전",
    "시즌패스", "배틀패스", "게임패치",
    # 자사 고유
    "드림에이지", "알케론", "arkheron", "drimage",
    # 경쟁사 고유 (게임 이름)
    "포트나이트", "발로란트", "배틀그라운드", "이터널리턴",
    "리그오브레전드", "pubg", "valorant", "fortnite",
    # 게임 회사
    "넥슨", "엔씨소프트", "넷마블", "크래프톤", "카카오게임즈",
    "위메이드", "컴투스", "스마일게이트", "펄어비스",
    "블리자드", "라이엇", "에픽게임즈",
    "닌텐도", "플레이스테이션", "xbox",
    # 게임 미디어
    "인벤", "루리웹", "gaming", "game"
]

# 게임과 무관한 키워드가 제목에 있으면 제외
NON_GAME_BLOCKLIST = [
    # 컴퓨터/전자기기 상업
    "중고 컴퓨터", "컴퓨터 매입", "pc 수거", "컴퓨터 수거", "노트북 매입",
    "모니터 추천", "이어폰 추천", "헤드셋 추천", "노트북 추천", "pc 추천",
    "그래픽카드 추천", "cpu 추천", "ram 추천", "ssd 추천",
    "파워서플라이", "컴퓨터 조립", "pc 조립", "수리", "출장수리", "부품",
    # 스마트폰/태블릿
    "갤럭시", "아이폰", "스마트폰 추천", "태블릿 추천",
    "아이패드", "갤럭시탭",
    # 주식/금융
    "주가", "주식", "코인", "투자", "펀드", "etf", "매입", "수거",
    "인텔 주가", "엔비디아 주가",
    "부동산", "아파트", "분양", "청약", "대출",
    # 생활/소비
    "맛집", "카페", "식당", "레스토랑",
    "화장품", "뷰티", "스킨케어",
    "여행", "호텔", "리조트",
    "자동차", "전기차", "suv",
    "영어 공부", "자격증", "인턴십",
    "쿠키", "과자", "음식", "배달",
    # 의료/건강
    "병원", "의원", "약국", "건강기능식품",
    # 게이밍 PC 상업
    "게이밍 컴퓨터", "조립 pc", "조립pc", "사양 추천", "갓성비 pc",
    "듀얼하드", "게이밍pc 추천", "컴퓨터 견적", "pc 견적",
    # 게이밍 PC/노트북 광고 패턴
    "게이밍과 업무", "게이밍 및 업무", "업무 효율", "업무용 pc",
    # 게이밍 주변기기 브랜드 광고
    "razer", "바라쿠다", "로지텍", "스틸시리즈", "커세어", "하이퍼엑스",
    "헤드셋 리뷰", "이어폰 리뷰", "키보드 리뷰", "마우스 리뷰",
    # PC 광고 패턴
    "고사양 컴퓨터", "컴퓨터 본체", "게이밍 본체", "본체 추천",
    "최적화 컴퓨터", "최적화 pc", "고사양 pc", "고성능 pc",
    "pc방 창업", "컴퓨터 임대", "렌탈", "할부",
    "쿠팡", "11번가", "지마켓", "옥션", "네이버쇼핑", "조이스틱", "트리거 핸드폰", "트리거 모바일", "배그 트리거", "배그 조이스틱", "이어폰 가성비", "이어폰 원픽", "라이젠", "ryzen", "데스크탑 추천", "가성비 원픽", "쿠팡파트너스", "협찬", "구매링크", "제휴마케팅", "트리거", "주연테크", "게이밍컴퓨터", "컴퓨터본체", "치진트리거", "고사양 게임 즐기기", "게임을 즐겨보세요",
]

def is_blog_title_game_related(title, keyword):
    """블로그는 제목에 게임 관련 키워드가 직접 포함되어야 함"""
    title_lower = title.lower()
    # 검색 키워드가 제목에 있어야 함
    if keyword and keyword.lower() in title_lower:
        return True
    # 게임 전문 용어가 제목에 있어야 함
    game_title_keywords = [
        "게임", "mmorpg", "rpg", "fps", "pvp", "모바일게임",
        "업데이트", "패치", "시즌", "이벤트", "공략", "리뷰",
        "드림에이지", "아키텍트", "알케론", "arkheron",
        "포트나이트", "배틀그라운드", "발로란트", "이터널리턴",
        "리그오브레전드", "롤", "배그", "lol",
    ]
    return any(kw in title_lower for kw in game_title_keywords)

def is_game_related(title, summary="", source_name=""):
    # 신뢰할 수 있는 게임 전문 소스는 통과
    if any(trusted in source_name for trusted in TRUSTED_GAME_SOURCES):
        return True

    text = (title + " " + (summary or "")).lower()
    title_lower = title.lower()

    # 비게임 키워드가 제목에 있으면 차단
    if any(block in title_lower for block in NON_GAME_BLOCKLIST):
        return False

    # 블로그 URL이면 더 엄격한 필터 적용
    if "blog.naver.com" in source_name or "blog.naver.com" in title.lower():
        return is_blog_title_game_related(title, "")

    # 자사 고유 키워드는 바로 통과
    if any(kw in text for kw in ["드림에이지", "알케론", "arkheron", "drimage"]):
        return True

    # 아키텍트는 게임 맥락 필수
    if "아키텍트" in text:
        return any(kw in text for kw in ["게임", "mmorpg", "rpg", "pvp", "모바일", "드림에이지", "알케론", "크로스플랫폼"])

    # 경쟁사 키워드 + 하드웨어 광고 패턴 차단
    COMPETITOR_KWS = ["배틀그라운드","배그","pubg","포트나이트","fortnite","발로란트","valorant","이터널리턴","리그오브레전드","오버워치"]
    NEWS_INDICATORS = ["업데이트","패치","시즌","이벤트","대회","e스포츠","esports","서버","신규","출시","발표","공개","개발사","소식","우승","선수","토너먼트","리그","버그","점검","공지","핫픽스","밸런스","오픈베타","cbt","obt"]
    HARDWARE_CONTEXT = ["추천","가성비","구매","후기 추천","노트북","데스크탑","핸드폰","스마트폰","이어폰","마우스","키보드","헤드셋","조이스틱","고사양","최적화 설정","그래픽 설정"]
    if any(kw in text for kw in COMPETITOR_KWS):
        has_news = any(ind in text for ind in NEWS_INDICATORS)
        has_hw = any(hw in text for hw in HARDWARE_CONTEXT)
        if has_hw and not has_news:
            return False
    return any(kw in text for kw in GAME_SPECIFIC_KEYWORDS)

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

def is_recent(published_iso, hours=48):
    """published_at이 최근 N시간 이내인지 확인"""
    if not published_iso:
        return False  # 날짜 없으면 수집 안 함 (오래된 기사 방지)
    try:
        from datetime import timezone, timedelta
        pub = datetime.fromisoformat(published_iso.replace("Z", "+00:00"))
        if pub.tzinfo is None:
            pub = pub.replace(tzinfo=timezone.utc)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        return pub >= cutoff
    except:
        return False  # 파싱 실패 시 수집 안 함

def crawl():
    print(f"\n🚀 크롤링 시작: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    total, saved, skipped, filtered = 0, 0, 0, 0

    # 기존 수집 URL 캐시 (중복 방지)
    try:
        from datetime import timedelta, timezone
        existing = supabase.table("news").select("url").gte("collected_at", (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()).execute()
        existing_urls = {r["url"] for r in existing.data if r.get("url")}
        print(f"  기존 URL {len(existing_urls)}개 캐시 완료")
    except Exception as e:
        existing_urls = set()
        print(f"  URL 캐시 실패: {e}")

    # RSS 피드 수집
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
                    from datetime import timezone
                    published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).isoformat()
                except:
                    pass

            # 게임 관련 여부 필터링
            if not is_game_related(title, summary, source["name"]):
                filtered += 1
                continue

            # 48시간 이내 기사만 수집
            if not is_recent(published):
                filtered += 1
                continue

            # URL 중복 체크
            if url in existing_urls:
                skipped += 1
                continue
            existing_urls.add(url)

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
        "경쟁사": ["포트나이트", "이터널리턴", "배틀그라운드", "발로란트", "LCK", "VCT 퍼시픽"],
        "업계": ['신작', '런칭', '사전예약', '얼리액세스', '지스타', '배틀로얄 신작', 'MMORPG 신작', '게임스컴', '도쿄게임쇼', 'GDC', '크로스플랫폼 게임', '스팀 인기 게임']
    }
    for category, keywords in naver_keywords.items():
        for keyword in keywords:
            print(f"\n📡 네이버 뉴스 - {keyword} 수집 중...")
            items = search_naver_news(keyword, naver_id, naver_secret)
            print(f"  → {len(items)}개 발견")
            for item in items:
                total += 1
                title = re.sub('<[^>]+>', '', item.get("title", ""))
                url = item.get("link", "")
                summary = re.sub('<[^>]+>', '', item.get("description", ""))
                pubdate_raw = item.get("pubDate", None)
                if pubdate_raw:
                    try:
                        from email.utils import parsedate_to_datetime
                        published = parsedate_to_datetime(pubdate_raw).isoformat()
                    except:
                        published = pubdate_raw
                else:
                    published = None

                # 48시간 이내 기사만 수집
                if not is_recent(published):
                    filtered += 1
                    continue

                # URL 중복 체크
                if url in existing_urls:
                    skipped += 1
                    continue
                existing_urls.add(url)

                url_source = "blog.naver.com" if "blog.naver.com" in url else ""
                if not is_game_related(title, summary, url_source):
                    filtered += 1
                    continue

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
        "자사": ["드림에이지", "알케론", "드림에이지 아키텍트"],
        "경쟁사": ["포트나이트", "리그오브레전드", "이터널리턴", "배틀그라운드", "발로란트"],
        "업계": ["MMORPG 신작", "배틀로얄 신작", "스팀 인기 게임"]
    }
    for category, keywords in naver_blog_keywords.items():
        for keyword in keywords:
            print(f"\n📡 네이버 블로그 - {keyword} 수집 중...")
            url = "https://openapi.naver.com/v1/search/blog.json"
            headers = {"X-Naver-Client-Id": naver_id, "X-Naver-Client-Secret": naver_secret}
            params = {"query": keyword, "display": 100, "sort": "date"}
            try:
                response = requests.get(url, headers=headers, params=params, timeout=10)
                items = response.json().get("items", [])
                print(f"  → {len(items)}개 발견")
                for item in items:
                    total += 1
                    title = re.sub('<[^>]+>', '', item.get("title", ""))
                    link = item.get("link", "")
                    description = re.sub('<[^>]+>', '', item.get("description", ""))
                    postdate_raw = item.get("postdate", None)
                    if postdate_raw and len(postdate_raw) == 8:
                        try:
                            from datetime import timezone
                            published = datetime(int(postdate_raw[:4]), int(postdate_raw[4:6]), int(postdate_raw[6:8]), tzinfo=timezone.utc).isoformat()
                        except:
                            published = None
                    else:
                        published = postdate_raw

                    if not is_blog_title_game_related(title, keyword) or not is_game_related(title, description):
                        filtered += 1
                        continue

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

    # 미니맵 매거진 수집
    print(f"\n📡 미니맵 매거진 수집 중...")
    try:
        resp = requests.get(
            "https://minimap.net/api/magazine/getMagazineList?sort=DISPLAY_TIME_DESC&l=kr",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=15
        )
        if resp.status_code == 200:
            magazines = resp.json().get("magazineList", [])
            print(f"  → {len(magazines)}개 발견")
            for mag in magazines:
                total += 1
                title = mag.get("title", "").strip()
                url = f"https://minimap.net/magazine/{mag.get('url', '')}"
                summary = mag.get("content", "").strip()
                display_time = mag.get("displayTime", "")
                try:
                    published = display_time.replace(" ", "T") if display_time else None
                except:
                    published = None
                if not title:
                    filtered += 1
                    continue
                if not is_recent(published):
                    filtered += 1
                    continue
                category, _ = get_category(title, summary)
                tags = get_tags(title, summary)
                try:
                    supabase.table("news").insert({
                        "title": title,
                        "url": url,
                        "summary": summary[:500] if summary else None,
                        "source": "미니맵",
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
        else:
            print(f"  ⚠️ 미니맵 매거진 API 오류: {resp.status_code}")
    except Exception as e:
        print(f"  ⚠️ 미니맵 매거진 수집 오류: {e}")

    print(f"\n✨ 완료! 총 {total}개 수집 / {saved}개 저장 / {skipped}개 중복 / {filtered}개 필터링")

if __name__ == "__main__":
    crawl()
