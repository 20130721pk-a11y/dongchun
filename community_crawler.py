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

KEYWORDS = {
    "자사": [
        "드림에이지",
        "알케론",
        "arkheron",
        "Arkheron",
        "아키텍트",
        "드림에이지 아키텍트",
    ],
    "경쟁사": [
        "포트나이트",
        "이터널리턴",
        "배틀그라운드",
        "발로란트",
        "리그오브레전드",
        "오버워치2",
        "에이펙스 레전드",
    ],
}

def get_category(keyword):
    for category, kw_list in KEYWORDS.items():
        if keyword in kw_list:
            return category
    return "기타"

def get_all_keywords():
    return KEYWORDS["자사"] + KEYWORDS["경쟁사"]


def parse_date_safe(date_str):
    """다양한 날짜 형식을 ISO yyyy-mm-dd 로 변환"""
    if not date_str:
        return None
    try:
        s = str(date_str).strip()
        # YYYYMMDD
        if len(s) == 8 and s.isdigit():
            return f"{s[:4]}-{s[4:6]}-{s[6:]}"
        import re
        # yyyy.mm.dd or yyyy/mm/dd (시간 포함도 처리)
        m = re.search(r'(20\d{2})[./\-](\d{1,2})[./\-](\d{1,2})', s)
        if m:
            return f"{m.group(1)}-{m.group(2).zfill(2)}-{m.group(3).zfill(2)}"
        # mm.dd (올해)
        m2 = re.search(r'^(\d{1,2})\.(\d{1,2})\.?$', s)
        if m2:
            return f"{datetime.now().year}-{m2.group(1).zfill(2)}-{m2.group(2).zfill(2)}"
        # HH:MM or HH:MM:SS → 오늘 날짜로 처리
        m3 = re.search(r'^\d{1,2}:\d{2}', s)
        if m3:
            return datetime.now().strftime('%Y-%m-%d') + 'T' + s
        # 상대 시간 표현 ("방금", "N분 전", "N시간 전") → 오늘
        if any(x in s for x in ['방금', '분 전', '시간 전', '초 전', '방금전']):
            return datetime.now().isoformat()
        return None
    except:
        return None

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


GAME_KEYWORDS = [
    "게임", "게이머", "게임사", "플레이", "출시", "업데이트", "패치", "서버",
    "캐릭터", "아이템", "스킬", "pvp", "pve", "rpg", "fps", "moba",
    "mmorpg", "모바일게임", "스팀", "콘솔", "pc방", "e스포츠", "esports",
    "대회", "시즌", "배틀", "테스트", "베타", "신작", "런칭", "섭종",
    "드림에이지", "알케론", "포트나이트", "발로란트",
    "배틀그라운드", "pubg", "valorant", "fortnite", "이터널리턴",
    "리그오브레전드", "lol", "steam", "gaming", "game", "gameplay"
]

def is_korean(text):
    korean_chars = len([c for c in text if '가' <= c <= '힣'])
    total_chars = len([c for c in text if c.strip()])
    return total_chars == 0 or (korean_chars / total_chars) >= 0.2

NON_GAME_BLOCKLIST = [
    "중고 컴퓨터","컴퓨터 매입","pc 수거","컴퓨터 수거","노트북 매입",
    "모니터 추천","이어폰 추천","헤드셋 추천","노트북 추천","pc 추천",
    "그래픽카드 추천","cpu 추천","ram 추천","ssd 추천",
    "파워서플라이","컴퓨터 조립","pc 조립","수리","출장수리","부품",
    "갤럭시","아이폰","스마트폰 추천","태블릿 추천","아이패드","갤럭시탭",
    "주가","주식","코인","투자","펀드","etf","매입","수거",
    "부동산","아파트","분양","청약","대출",
    "맛집","카페","식당","레스토랑","화장품","뷰티","스킨케어",
    "여행","호텔","리조트","자동차","전기차","suv",
    "영어 공부","자격증","인턴십","쿠키","과자","음식","배달",
    "병원","의원","약국","건강기능식품",
    "게이밍 컴퓨터","조립 pc","조립pc","사양 추천","갓성비 pc",
    "게이밍pc 추천","컴퓨터 견적","pc 견적",
    "게이밍과 업무","게이밍 및 업무","업무 효율","업무용 pc",
    "razer","바라쿠다","로지텍","스틸시리즈","커세어","하이퍼엑스",
    "헤드셋 리뷰","이어폰 리뷰","키보드 리뷰","마우스 리뷰",
    "고사양 컴퓨터","컴퓨터 본체","게이밍 본체","본체 추천",
    "최적화 컴퓨터","최적화 pc","고사양 pc","고성능 pc",
    "pc방 창업","컴퓨터 임대","렌탈","할부",
    "쿠팡","11번가","지마켓","옥션","네이버쇼핑",
]

def is_game_related(title, summary=""):
    if not is_korean(title):
        return False
    text = (title + " " + (summary or "")).lower()
    title_lower = title.lower()
    if any(block in title_lower for block in NON_GAME_BLOCKLIST):
        return False
    if "드림에이지" in text or "알케론" in text or "arkheron" in text or "drimage" in text:
        return True
    if "아키텍트" in text and any(kw in text for kw in ["게임", "mmorpg", "rpg", "pvp", "모바일", "크로스플랫폼", "심연", "쟁"]):
        return True
    return any(kw.lower() in text for kw in GAME_KEYWORDS)

POSITIVE_WORDS = [
    # 게임 품질
    '갓겜','꿀잼','레전드','명작','완성도','퀄리티','훌륭','대박','최고',
    '재밌','재미있','즐겁','좋다','좋은','좋아','추천','강추','필수',
    '기대','기대작','기대됩','기대이상','설렌','설레','흥미','흥미롭',
    '멋지','멋있','감동','감사','칭찬','인정','ㄹㅇ','ㅇㅈ',
    # 게임플레이
    '꿀','핵꿀','쾌적','안정적','밸런스 좋','최적화','부드럽','깔끔',
    '업뎃 좋','패치 좋','개선','발전','성장','기대이상','예상이상',
    # 커뮤니티 반응
    '인기','핫','화제','트렌드','많이','터짐','몰림','대기열',
    '복귀','복귀함','돌아왔','다시시작','재시작','복귀유저',
]

NEGATIVE_WORDS = [
    # 게임 품질
    '망겜','쓰레기','최악','별로','노잼','노답','구리','구린','실망',
    '환불','튕김','버그','오류','에러','렉','끊김','튕','충돌',
    '망했','망함','폭망','역대급','개판','개최악','최하',
    # 운영 문제
    '현질','과금','결제','운영','탈주','탈함','나간다','접었','접는',
    '운영진','공지없','공지 없','소통없','소통 없','묵묵부답',
    '서버터짐','서버 터짐','접속오류','접속 오류','점검','긴급점검',
    # 밸런스
    '핵','어뷰징','핵쟁이','사기캐','사기스킬','사기급','밸붕','밸런스 붕괴',
    '불공평','불균형','너프','과도한 너프',
    # 감성 표현
    '싫다','싫어','짜증','화남','빡침','ㅡㅡ','ㅠㅠ','ㅜㅜ',
    '불만','항의','신고','문의해도','답변없','환불신청',
]

STRONG_POSITIVE = ['갓겜','레전드','명작','꿀잼','강추','개꿀','핵꿀']
STRONG_NEGATIVE = ['망겜','쓰레기','환불','튕김','탈주','서버터짐','핵','사기']

def analyze_sentiment_rule(title, content=""):
    text = (title + " " + (content or "")).lower()
    
    # 강한 감성 먼저 체크
    for w in STRONG_POSITIVE:
        if w in text: return '긍정', f'긍정 키워드 감지: {w}'
    for w in STRONG_NEGATIVE:
        if w in text: return '부정', f'부정 키워드 감지: {w}'
    
    pos = sum(1 for w in POSITIVE_WORDS if w in text)
    neg = sum(1 for w in NEGATIVE_WORDS if w in text)
    
    if pos > neg: return '긍정', '긍정적 표현 다수 감지'
    if neg > pos: return '부정', '부정적 표현 다수 감지'
    return '중립', '중립적 내용'

def analyze_sentiment(title, content=""):
    # 먼저 규칙 기반으로 빠르게 분석
    rule_result = analyze_sentiment_rule(title, content)
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
        if result.get("error"):
            return rule_result
        parsed = json.loads(result["content"][0]["text"])
        return parsed.get("sentiment", rule_result[0]), parsed.get("reason", rule_result[1])
    except:
        return rule_result

def save_post(title, content, url, community, views, comments, keyword, posted_at, category):
    sentiment, reason = analyze_sentiment_rule(title, content)
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
            "category": category,
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
        # 커뮤니티+웹진 통합 검색 URL
        url = f"https://www.inven.co.kr/search/community/all/{encoded}"
        response = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        seen = set()
        # fallback: a 태그 중 inven.co.kr 포함 href
        for a in soup.find_all('a', href=True):
            href = a.get('href', '')
            title = a.get_text(strip=True)
            if 'inven.co.kr' in href and len(title) > 5 and href not in seen:
                if any(x in href for x in ['/board/', '/article/', '/news/', '/webzine/']):
                    seen.add(href)
                    results.append({'title': title[:100], 'url': href, 'posted_at': datetime.now().isoformat(), 'views': 0, 'comments': 0})
            if len(results) >= 100:
                break
        print(f"  ✅ 인벤 {len(results)}건 수집")
    except Exception as e:
        print(f"  ⚠️ 인벤 실패: {e}")
    return results

def crawl_ruliweb(keyword):
    print(f"\n📡 루리웹 - {keyword} 수집 중...")
    results = []
    try:
        from playwright.sync_api import sync_playwright
        encoded = requests.utils.quote(keyword)
        url = f"https://bbs.ruliweb.com/search?q={encoded}&searchType=subject&orderType=latest"
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
            )
            page = browser.new_page(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)
            html = page.content()
            browser.close()
        soup = BeautifulSoup(html, 'html.parser')
        seen = set()
        # 루리웹 검색 결과: tr.item 또는 .list_body tr
        rows = soup.select('tr.item') or soup.select('.board_list_table tbody tr')
        for row in rows:
            title_tag = row.select_one('a.deco') or row.select_one('td.subject a') or row.select_one('a[href*="/read/"]')
            if not title_tag:
                continue
            title = title_tag.get_text(strip=True)
            href = title_tag.get('href', '')
            if not href.startswith('http'):
                href = 'https://bbs.ruliweb.com' + href
            if not title or len(title) < 5 or href in seen:
                continue
            seen.add(href)
            date_tag = row.select_one('td.time') or row.select_one('.time')
            posted_at_raw = date_tag.get_text(strip=True) if date_tag else None
            posted_at = parse_date_safe(posted_at_raw) or datetime.now().isoformat()
            view_tag = row.select_one('td.hit') or row.select_one('.hit')
            views = 0
            if view_tag:
                try:
                    views = int(view_tag.get_text(strip=True).replace(',', ''))
                except:
                    pass
            results.append({'title': title[:100], 'url': href, 'posted_at': posted_at, 'views': views, 'comments': 0})
            if len(results) >= 100:
                break
        print(f"  ✅ 루리웹 {len(results)}건 수집")
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
                '오버워치2': 'overwatch',
                '에이펙스 레전드': 'apexlegends',
            }
            gall_id = GALL_IDS.get(keyword)
            if not gall_id:
                # 전용 갤러리 없는 키워드는 검색 사용
                try:
                    search_url = f"https://search.dcinside.com/post/p/1/q/{requests.utils.quote(keyword)}"
                    response = requests.get(search_url, headers=HEADERS, timeout=10)
                    soup = BeautifulSoup(response.text, 'html.parser')
                    items = soup.select('.sch_result_txt')
                    for item in items[:30]:
                        title_tag = item.select_one('a')
                        if not title_tag: continue
                        title = title_tag.get_text(strip=True)
                        href = title_tag.get('href','')
                        if title and len(title) > 2:
                            results.append({'title':title[:100],'url':href,'posted_at':None,'views':0,'comments':0})
                except: pass
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
        params = {"query": keyword, "display": 100, "sort": "date", "start": 1}
        response = requests.get(url, headers=headers, params=params, timeout=10)
        items = response.json().get("items", [])
        import re
        for item in items:
            title = re.sub('<[^>]+>', '', item.get("title", ""))
            link = item.get("link", "")
            posted_at = parse_date_safe(item.get("postdate", None))
            results.append({'title': title, 'url': link, 'posted_at': posted_at, 'views': 0, 'comments': 0})
    except Exception as e:
        print(f"  ⚠️ 네이버 카페 실패: {e}")
    return results

def crawl_arcalive(keyword):
    print(f"\n📡 아카라이브 - {keyword} 수집 중...")
    results = []
    try:
        from playwright.sync_api import sync_playwright
        encoded = requests.utils.quote(keyword)
        url = f"https://arca.live/b/breaking?keyword={encoded}"
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
            )
            page = browser.new_page(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
            page.goto(url, timeout=30000, wait_until="networkidle")
            page.wait_for_timeout(3000)
            html = page.content()
            browser.close()
        soup = BeautifulSoup(html, 'html.parser')
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
        print(f"  ✅ 아카라이브 {len(results)}건 수집")
    except Exception as e:
        print(f"  ⚠️ 아카라이브 실패: {e}")
    return results


FMKOREA_BOARDS = {
    '발로란트': 'valorant', 'valorant': 'valorant',
    '리그오브레전드': 'lol', 'lol': 'lol',
    '오버워치': 'overwatch', '오버워치2': 'overwatch',
    '포트나이트': 'fortnite',
    '배틀그라운드': 'pubg', 'pubg': 'pubg',
    '에이펙스': 'apex', '에이펙스 레전드': 'apex',
    '이터널리턴': 'eternalreturn',
}

def _fmkorea_scrape_board(board):
    """전용 게시판 직접 스크래핑"""
    import re
    from playwright.sync_api import sync_playwright
    results = []
    url = f"https://www.fmkorea.com/{board}"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox","--disable-setuid-sandbox","--disable-dev-shm-usage"])
        page = browser.new_page(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
        page.goto(url, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        html = page.content()
        browser.close()
    soup = BeautifulSoup(html, 'html.parser')
    seen = set()
    for a in soup.find_all('a', href=True):
        href = a.get('href', '')
        title = a.get_text(strip=True)
        if not re.match(r'^/[0-9]{8,}$', href):
            continue
        if not title or len(title) < 5 or href in seen:
            continue
        seen.add(href)
        parent = a.find_parent('li') or a.find_parent('tr')
        posted_at = None
        if parent:
            time_tag = parent.find('time')
            if time_tag:
                posted_at = time_tag.get('datetime') or parse_date_safe(time_tag.get_text(strip=True))
        # 공지/고정글 제외 (제목이 [로 시작하는 경우)
        if title.startswith('['):
            continue
        # posted_at 없으면 오늘 날짜로 대체 (게시판 현재 글 기준)
        if not posted_at:
            from datetime import datetime, timezone, timedelta
            kst = timezone(timedelta(hours=9))
            posted_at = datetime.now(kst).isoformat()
        results.append({'title': title[:100], 'url': f"https://www.fmkorea.com{href}", 'posted_at': posted_at, 'views': 0, 'comments': 0})
        if len(results) >= 50:
            break
    return results

def _fmkorea_search_gsc(keyword):
    """Google CSE 검색 - 자사 키워드용"""
    from playwright.sync_api import sync_playwright
    import urllib.parse
    results = []
    encoded = urllib.parse.quote(keyword)
    url = f"https://www.fmkorea.com/search.php?act=IS&is_keyword={encoded}#gsc.q={encoded}&gsc.sort=date"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox","--disable-setuid-sandbox","--disable-dev-shm-usage"])
        page = browser.new_page(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
        page.goto(url, timeout=30000, wait_until="domcontentloaded")
        try:
            page.wait_for_selector('.gsc-result', timeout=10000)
        except:
            browser.close()
            return results
        html = page.content()
        browser.close()
    soup = BeautifulSoup(html, 'html.parser')
    seen = set()
    for r in soup.select('.gsc-result'):
        title_tag = r.select_one('.gs-title a')
        if not title_tag:
            continue
        href = title_tag.get('href', '')
        title = title_tag.get_text(strip=True)
        if 'fmkorea.com' not in href or href in seen:
            continue
        if keyword not in title and keyword.lower() not in title.lower():
            continue
        seen.add(href)
        from datetime import datetime, timezone, timedelta
        kst = timezone(timedelta(hours=9))
        results.append({'title': title[:100], 'url': href, 'posted_at': datetime.now(kst).isoformat(), 'views': 0, 'comments': 0})
        if len(results) >= 20:
            break
    return results

def crawl_fmkorea(keyword):
    print(f"\n📡 에펨코리아 - {keyword} 수집 중...")
    results = []
    try:
        board = FMKOREA_BOARDS.get(keyword) or FMKOREA_BOARDS.get(keyword.lower())
        if board:
            results = _fmkorea_scrape_board(board)
        else:
            results = _fmkorea_search_gsc(keyword)
        print(f"  ✅ 에펨코리아 {len(results)}건 수집")
    except Exception as e:
        print(f"  ⚠️ 에펨코리아 실패: {e}")
    return results


def crawl_nate(keyword):
    print(f"\n📡 네이트판 - {keyword} 수집 중...")
    results = []
    try:
        encoded = requests.utils.quote(keyword)
        url = f"https://pann.nate.com/search/talk?q={encoded}"
        response = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        seen = set()
        items = soup.select('a[href*="/talk/"]')
        for a in items:
            title = a.get_text(strip=True)
            href = a.get('href', '')
            if keyword.lower() in title.lower() and len(title) > 5 and href not in seen:
                full_url = href if href.startswith('http') else f"https://pann.nate.com{href}"
                seen.add(href)
                # 조회수/댓글 파싱 시도
                parent = a.find_parent('li') or a.find_parent('div')
                views = 0
                comments = 0
                if parent:
                    spans = parent.find_all('span')
                    for span in spans:
                        txt = span.get_text(strip=True).replace(',', '')
                        if txt.isdigit():
                            views = int(txt)
                            break
                results.append({'title': title[:100], 'url': full_url, 'posted_at': None, 'views': views, 'comments': comments})
            if len(results) >= 50:
                break
    except Exception as e:
        print(f"  ⚠️ 네이트판 실패: {e}")
    return results

def crawl_minimap(keyword):
    print(f"\n📡 미니맵 - {keyword} 수집 중...")
    results = []
    try:
        encoded = requests.utils.quote(keyword)
        url = f"https://minimap.net/api/search/getSearchMain?searchValue={encoded}"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            print(f"  ⚠️ 미니맵 API 오류: {resp.status_code}")
            return results
        data = resp.json()
        for item in data.get("postList", []):
            post_sn = item.get("postSn")
            title = item.get("title", "").strip() or item.get("pageTitle", "").strip()
            content = item.get("content", "").strip()
            display_time = item.get("displayTime", "")
            comment_cnt = item.get("commentCnt", 0) or 0
            if not title and not content:
                continue
            try:
                posted_at = display_time.split(".")[0].replace(" ", "T") if display_time else None
            except:
                posted_at = None
            post_url = f"https://minimap.net/post/{post_sn}" if post_sn else ""
            results.append({
                "title": title[:200],
                "content": content[:500],
                "url": post_url,
                "community": "미니맵",
                "views": 0,
                "comments": comment_cnt,
                "keyword": keyword,
                "posted_at": posted_at
            })
        print(f"  ✅ 미니맵 {len(results)}건 수집")
    except Exception as e:
        print(f"  ⚠️ 미니맵 크롤링 오류: {e}")
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
            pub_date_raw = item.get("pubDate", None)
            try:
                from email.utils import parsedate_to_datetime
                posted_at = parsedate_to_datetime(pub_date_raw).isoformat() if pub_date_raw else None
            except:
                posted_at = None
            results.append({'title': title[:100], 'url': link, 'posted_at': posted_at, 'views': 0, 'comments': 0})
    except Exception as e:
        print(f"  ⚠️ 디스이즈게임 실패: {e}")
    return results

def is_recent(posted_at, hours=72):
    if not posted_at:
        return False
    try:
        from datetime import timezone, timedelta
        import pytz
        pub = datetime.fromisoformat(str(posted_at).replace("Z", "+00:00"))
        if pub.tzinfo is None:
            pub = pub.replace(tzinfo=timezone.utc)
        kst = pytz.timezone('Asia/Seoul')
        today_kst = datetime.now(kst).date()
        return pub.astimezone(kst).date() >= today_kst
    except:
        return False  # 파싱 실패 시 수집 안 함

def crawl():
    print(f"\n🔍 커뮤니티 크롤링 시작: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    total, saved, skipped = 0, 0, 0

    # 기존 수집 URL 캐시 (중복 방지)
    try:
        from datetime import timezone, timedelta
        existing = supabase.table("community_posts").select("url").gte("collected_at", (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()).execute()
        existing_urls = {r["url"] for r in existing.data if r.get("url")}
        print(f"  기존 URL {len(existing_urls)}개 캐시 완료")
    except Exception as e:
        existing_urls = set()
        print(f"  URL 캐시 실패: {e}")

    crawlers = [
        ("인벤", crawl_inven),
        ("루리웹", crawl_ruliweb),
        ("디시인사이드", crawl_dcinside),
        ("네이버카페", crawl_naver_cafe),
        ("아카라이브", crawl_arcalive),
        ("에펨코리아", crawl_fmkorea),
        ("네이트판", crawl_nate),
        ("디스이즈게임", crawl_thisisgame),
        ("미니맵", crawl_minimap),
    ]

    for keyword in get_all_keywords():
        category = get_category(keyword)
        print(f"\n[{category}] 키워드: {keyword}")
        for community, crawler in crawlers:
            posts = crawler(keyword)
            print(f"  → {len(posts)}개 발견")
            for post in posts:
                total += 1
                # 검색 키워드가 제목에 포함된 경우 게임 관련성 필터 바이패스
                title_lower = post['title'].lower()
                keyword_in_title = keyword.lower() in title_lower or any(
                    alias in title_lower for alias in {
                        '드림에이지': ['drimage'], '알케론': ['arkheron'],
                        'arkheron': ['알케론'], '아키텍트': [],
                        '배틀그라운드': ['pubg','배그'], '포트나이트': ['fortnite'],
                        '발로란트': ['valorant'], '리그오브레전드': ['lol','롤'],
                        '에이펙스 레전드': ['apex'], '이터널리턴': ['eternal return'],
                        '오버워치2': ['overwatch','오버워치'],
                    }.get(keyword, [])
                )
                if not keyword_in_title and not is_game_related(post['title']):
                    skipped += 1
                    continue
                # 날짜 필터: 네이트판은 날짜 없어도 허용, 나머지는 당일만
                posted_at_val = post.get('posted_at')
                if community != '네이트판':
                    if not posted_at_val or not is_recent(posted_at_val):
                        skipped += 1
                        continue
                # URL 중복 체크
                post_url = post.get('url', '')
                if post_url and post_url in existing_urls:
                    skipped += 1
                    continue
                if post_url:
                    existing_urls.add(post_url)
                success, sentiment = save_post(
                    post['title'], "", post['url'], community,
                    post['views'], post['comments'], keyword, post['posted_at'],
                    category
                )
                if success:
                    saved += 1
                    print(f"  ✅ [{category}][{sentiment}] {post['title'][:40]}...")
                else:
                    skipped += 1
                time.sleep(0.3)

    print(f"\n✨ 완료! 총 {total}개 수집 / {saved}개 저장 / {skipped}개 중복 스킵")

if __name__ == "__main__":
    crawl()
