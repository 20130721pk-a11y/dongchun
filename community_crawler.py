import requests
from bs4 import BeautifulSoup
import os
import json
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))  # 전역 KST 상수
import time

load_dotenv()

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

KEYWORDS = {
    "자사": [
        "드림에이지",
        "알케론",
        "arkheron",
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
            return f"{s[:4]}-{s[4:6]}-{s[6:]}T00:00:00+09:00"  # YYYYMMDD → KST 자정
        import re
        # yyyy.mm.dd or yyyy/mm/dd or yyyy-mm-dd (시간 포함도 처리)
        m = re.search(r'(20\d{2})[./\-](\d{1,2})[./\-](\d{1,2})', s)
        if m:
            return f"{m.group(1)}-{m.group(2).zfill(2)}-{m.group(3).zfill(2)}"
        # YY.MM.DD (디시인사이드 날짜 형식: "26.05.23")
        m_yy = re.match(r'^(\d{2})\.(\d{2})\.(\d{2})$', s)
        if m_yy:
            return f"20{m_yy.group(1)}-{m_yy.group(2)}-{m_yy.group(3)}"
        # mm.dd (올해)
        m2 = re.search(r'^(\d{1,2})\.(\d{1,2})\.?$', s)
        if m2:
            return f"{datetime.now(KST).year}-{m2.group(1).zfill(2)}-{m2.group(2).zfill(2)}"
        # HH:MM or HH:MM:SS → 오늘 날짜로 처리
        m3 = re.search(r'^\d{1,2}:\d{2}', s)
        if m3:
            return datetime.now(KST).strftime('%Y-%m-%d') + 'T' + s
        # 상대 시간 표현 ("방금", "N분 전", "N시간 전") → 오늘
        if any(x in s for x in ['방금', '분 전', '시간 전', '초 전', '방금전']):
            return datetime.now(KST).isoformat()
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
        client_id = os.getenv("NAVER_CLIENT_ID")
        client_secret = os.getenv("NAVER_CLIENT_SECRET")
        if not client_id:
            return results
        headers = {**HEADERS, "X-Naver-Client-Id": client_id, "X-Naver-Client-Secret": client_secret}
        # 네이버 검색 API로 inven.co.kr 결과만 필터링
        # webkr: 인벤 커뮤니티 글 / cafearticle: 인벤 카페 / news: 인벤 뉴스
        params = {"query": f"{keyword} site:inven.co.kr", "display": 100, "sort": "date"}
        resp = requests.get("https://openapi.naver.com/v1/search/webkr.json", headers=headers, params=params, timeout=10)
        if resp.status_code != 200 or not resp.json().get("items"):
            params2 = {"query": f"{keyword}", "display": 100, "sort": "date"}
            resp = requests.get("https://openapi.naver.com/v1/search/cafearticle.json", headers=headers, params=params2, timeout=10)
        import re
        for item in resp.json().get("items", []):
            link = item.get("originallink", item.get("link", ""))
            if "inven.co.kr" not in link:
                continue
            title = re.sub('<[^>]+>', '', item.get("title", ""))
            # webkr.json은 pubDate 없음 → postdate(YYYYMMDD) 또는 pubDate(RFC2822) 순서로 시도
            posted_at = None
            pub_raw = item.get("postdate") or item.get("pubDate")
            if pub_raw:
                try:
                    from email.utils import parsedate_to_datetime
                    posted_at = parsedate_to_datetime(str(pub_raw)).isoformat()
                except:
                    posted_at = parse_date_safe(str(pub_raw))
            if not posted_at:
                posted_at = None  # postdate 없으면 None → is_recent_day 필터에서 차단
            results.append({'title': title[:100], 'url': link, 'posted_at': posted_at, 'views': 0, 'comments': 0})
        print(f"  ✅ 인벤 {len(results)}건 수집")
    except Exception as e:
        print(f"  ⚠️ 인벤 실패: {e}")
    return results

def crawl_ruliweb(keyword):
    print(f"\n📡 루리웹 - {keyword} 수집 중...")
    results = []
    try:
        client_id = os.getenv("NAVER_CLIENT_ID")
        client_secret = os.getenv("NAVER_CLIENT_SECRET")
        if not client_id:
            print("  ⚠️ 루리웹: NAVER_CLIENT_ID 없음")
            return results
        headers = {**HEADERS, "X-Naver-Client-Id": client_id, "X-Naver-Client-Secret": client_secret}
        import re
        for search_type, endpoint in [
            (f"{keyword} site:bbs.ruliweb.com", "https://openapi.naver.com/v1/search/webkr.json"),
            (f"{keyword} ruliweb",               "https://openapi.naver.com/v1/search/news.json"),
        ]:
            params = {"query": search_type, "display": 50, "sort": "date"}
            resp = requests.get(endpoint, headers=headers, params=params, timeout=10)
            if resp.status_code != 200:
                continue
            for item in resp.json().get("items", []):
                link = item.get("originallink") or item.get("link", "")
                if "ruliweb.com" not in link:
                    continue
                title = re.sub('<[^>]+>', '', item.get("title", ""))
                pub_raw = item.get("pubDate") or item.get("postdate")
                try:
                    from email.utils import parsedate_to_datetime
                    posted_at = parsedate_to_datetime(str(pub_raw)).isoformat() if pub_raw and '@' not in str(pub_raw) else parse_date_safe(str(pub_raw))
                except:
                    posted_at = parse_date_safe(str(pub_raw)) if pub_raw else None
                if not posted_at:
                    posted_at = None
                results.append({'title': title[:100], 'url': link, 'posted_at': posted_at, 'views': 0, 'comments': 0})
            if results:
                break
        # 중복 URL 제거
        seen = set()
        unique = []
        for r in results:
            if r['url'] not in seen:
                seen.add(r['url'])
                unique.append(r)
        results = unique[:100]
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
                response = requests.get(url, headers=HEADERS, timeout=20)
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
                    posted_at = parse_date_safe(posted_at_raw) or datetime.now(KST).isoformat()
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
                try:
                    response = requests.get(url, headers=HEADERS, timeout=20)
                except Exception as te:
                    print(f"  ⚠️ 디시인사이드 타임아웃 ({url}): {te}")
                    break
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
                    posted_at = parse_date_safe(posted_at_raw) or datetime.now(KST).isoformat()
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
        dates_seen = []
        for item in items:
            title = re.sub('<[^>]+>', '', item.get("title", ""))
            link = item.get("link", "")
            postdate_raw = item.get("postdate", None)
            posted_at = parse_date_safe(postdate_raw)
            dates_seen.append(postdate_raw)
            results.append({'title': title, 'url': link, 'posted_at': posted_at, 'views': 0, 'comments': 0})
        valid_dates = [d for d in dates_seen if d]
        if valid_dates:
            print(f"    카페 날짜 범위: {min(valid_dates)} ~ {max(valid_dates)}")
        else:
            print(f"    카페 날짜 범위: 날짜 정보 없음 ({len(results)}건)")
    except Exception as e:
        print(f"  ⚠️ 네이버 카페 실패: {e}")
    return results


def crawl_arcalive(keyword):
    print(f"\n📡 아카라이브 - {keyword} 수집 중...")
    results = []
    try:
        client_id = os.getenv("NAVER_CLIENT_ID")
        client_secret = os.getenv("NAVER_CLIENT_SECRET")
        if not client_id:
            print("  ⚠️ 아카라이브: NAVER_CLIENT_ID 없음")
            return results
        headers = {**HEADERS, "X-Naver-Client-Id": client_id, "X-Naver-Client-Secret": client_secret}
        import re
        params = {"query": f"{keyword} site:arca.live", "display": 50, "sort": "date"}
        resp = requests.get("https://openapi.naver.com/v1/search/webkr.json", headers=headers, params=params, timeout=10)
        for item in resp.json().get("items", []):
            link = item.get("originallink") or item.get("link", "")
            if "arca.live" not in link:
                continue
            title = re.sub('<[^>]+>', '', item.get("title", ""))
            pub_raw = item.get("postdate") or item.get("pubDate")
            posted_at = parse_date_safe(str(pub_raw)) if pub_raw else None
            results.append({'title': title[:100], 'url': link, 'posted_at': posted_at, 'views': 0, 'comments': 0})
        results = results[:100]
        print(f"  ✅ 아카라이브 {len(results)}건 수집")
    except Exception as e:
        print(f"  ⚠️ 아카라이브 실패: {e}")
    return results


def crawl_fmkorea(keyword):
    print(f"\n📡 에펨코리아 - {keyword} 수집 중...")
    results = []
    try:
        client_id = os.getenv("NAVER_CLIENT_ID")
        client_secret = os.getenv("NAVER_CLIENT_SECRET")
        if not client_id:
            print("  ⚠️ 에펨코리아: NAVER_CLIENT_ID 없음")
            return results
        headers = {**HEADERS, "X-Naver-Client-Id": client_id, "X-Naver-Client-Secret": client_secret}
        import re
        params = {"query": f"{keyword} site:fmkorea.com", "display": 50, "sort": "date"}
        resp = requests.get("https://openapi.naver.com/v1/search/webkr.json", headers=headers, params=params, timeout=10)
        for item in resp.json().get("items", []):
            link = item.get("originallink") or item.get("link", "")
            if "fmkorea.com" not in link:
                continue
            title = re.sub('<[^>]+>', '', item.get("title", ""))
            pub_raw = item.get("postdate") or item.get("pubDate")
            posted_at = parse_date_safe(str(pub_raw)) if pub_raw else None
            results.append({'title': title[:100], 'url': link, 'posted_at': posted_at, 'views': 0, 'comments': 0})
        results = results[:100]
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
                # 날짜 파싱 시도 (parent 요소에서)
                posted_at = None
                if parent:
                    for tag in parent.find_all(['span', 'em', 'time', 'p']):
                        txt = tag.get_text(strip=True)
                        parsed = parse_date_safe(txt)
                        if parsed and len(parsed) >= 8:
                            posted_at = parsed
                            break
                # 날짜 없으면 오늘로 처리 (2019 등 과거 데이터 방지)
                if not posted_at:
                    posted_at = datetime.now(KST).isoformat()
                results.append({'title': title[:100], 'url': full_url, 'posted_at': posted_at, 'views': views, 'comments': comments})
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
                if display_time:
                    # "2026-05-23 12:30:45.123" 또는 "2026.05.23 12:30:45" 등 처리
                    dt_clean = display_time.strip()
                    # ISO 형식이면 밀리초만 제거
                    if 'T' in dt_clean or '-' in dt_clean[:8]:
                        posted_at = dt_clean.split('.')[0] if '.' in dt_clean and len(dt_clean.split('.')[0]) > 10 else dt_clean
                    else:
                        # "2026.05.23 12:30:45" → parse_date_safe 활용
                        posted_at = parse_date_safe(dt_clean.split(' ')[0]) or datetime.now(KST).isoformat()
                else:
                    posted_at = datetime.now(KST).isoformat()
            except:
                posted_at = datetime.now(KST).isoformat()
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
        import re as _re
        client_id = os.getenv("NAVER_CLIENT_ID")
        client_secret = os.getenv("NAVER_CLIENT_SECRET")
        # news API 대신 webkr API 사용 (네이버 뉴스 색인에 thisisgame 최신 기사 없음)
        url = "https://openapi.naver.com/v1/search/webkr.json"
        headers = {**HEADERS, "X-Naver-Client-Id": client_id, "X-Naver-Client-Secret": client_secret}
        params = {"query": f"site:thisisgame.com {keyword}", "display": 100, "sort": "date"}
        response = requests.get(url, headers=headers, params=params, timeout=10)
        items = response.json().get("items", [])
        for item in items:
            link = item.get("link", "")
            if "thisisgame.com" not in link:
                continue
            title = _re.sub('<[^>]+>', '', item.get("title", ""))
            # webkr postdate 없으면 None → is_recent_day 필터에서 차단
            postdate = item.get("postdate", "").strip()
            posted_at = parse_date_safe(postdate) if postdate and len(postdate) == 8 else None
            description = _re.sub('<[^>]+>', '', item.get("description", ""))
            results.append({'title': title[:100], 'content': description[:300], 'url': link, 'posted_at': posted_at, 'views': 0, 'comments': 0})
        print(f"  ✅ 디스이즈게임 {len(results)}건 수집")
    except Exception as e:
        print(f"  ⚠️ 디스이즈게임 실패: {e}")
    return results

def is_recent_day(posted_at, days=1):
    """posted_at이 KST 기준 오늘 또는 최근 days일 이내인지 확인
    - days=1: 오늘 + 어제 (23:59에 올라온 글이 다음날 크롤링에 누락되는 케이스 방지)
    - days=3: 웹진 전용 (네이버 색인 지연 고려)
    - fallback(datetime.now)으로 설정된 오늘 날짜도 통과
    """
    if not posted_at:
        return False
    try:
        pub = datetime.fromisoformat(str(posted_at).replace("Z", "+00:00"))
        if pub.tzinfo is None:
            pub = pub.replace(tzinfo=KST)
        else:
            pub = pub.astimezone(KST)
        today_kst = datetime.now(KST).date()
        earliest = today_kst - timedelta(days=days)
        return pub.date() >= earliest
    except:
        return False

def crawl():
    print(f"\n🔍 커뮤니티 크롤링 시작: {datetime.now(KST).strftime('%Y-%m-%d %H:%M')}")
    total, saved, skipped = 0, 0, 0

    # 당일 수집 URL 캐시 (같은 실행 내 중복 방지)
    # 30일 캐시 → 당일로 축소: 과거 URL이 새 글 수집을 막는 문제 해결
    try:
        cache_start = (datetime.now(KST) - timedelta(days=3)).strftime('%Y-%m-%dT00:00:00+09:00')
        existing = supabase.table("community_posts").select("url").gte("collected_at", cache_start).limit(5000).execute()
        existing_urls = {r["url"] for r in existing.data if r.get("url")}
        print(f"  최근 3일 수집 URL {len(existing_urls)}개 캐시 완료")
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

    # 게임 필터 바이패스할 소스 (해당 게임 전용 소스라 필터 불필요)
    # 네이버 API site: 검색 기반 크롤러는 키워드 포함 보장 → 게임필터 바이패스
    GAME_SOURCE_BYPASS = {'네이버카페', '디시인사이드', '아카라이브', '에펨코리아', '미니맵', '루리웹', '디스이즈게임'}
    skip_game, skip_date, skip_url, skip_db = 0, 0, 0, 0

    for keyword in get_all_keywords():
        category = get_category(keyword)
        print(f"\n[{category}] 키워드: {keyword}")
        for community, crawler in crawlers:
            posts = crawler(keyword)
            print(f"  → {len(posts)}개 발견")
            for post in posts:
                total += 1
                # 게임 관련성 필터 (전용 소스는 바이패스)
                if community not in GAME_SOURCE_BYPASS:
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
                        skip_game += 1; skipped += 1
                        continue
                # 날짜 필터: KST 날짜 기준 (롤링 시간 윈도우 → 날짜 기준으로 교체)
                # 웹진(네이버 색인 지연 고려): 오늘 포함 최근 3일
                # 커뮤니티: 오늘 + 어제 (심야 게시글 누락 방지)
                posted_at_val = post.get('posted_at')
                max_days = 3 if community in {'디스이즈게임', '인벤', '루리웹'} else 1
                if not posted_at_val or not is_recent_day(posted_at_val, days=max_days):
                    skip_date += 1; skipped += 1
                    continue
                # URL 중복 체크 (당일 캐시)
                post_url = post.get('url', '')
                if post_url and post_url in existing_urls:
                    skip_url += 1; skipped += 1
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
                    skip_db += 1; skipped += 1
                time.sleep(0.3)

    print(f"\n✨ 완료! 총 {total}개 수집 / {saved}개 저장 / {skipped}개 스킵")
    print(f"   스킵 분류: 게임필터={skip_game} / 날짜={skip_date} / URL중복={skip_url} / DB중복={skip_db}")

if __name__ == "__main__":
    crawl()
