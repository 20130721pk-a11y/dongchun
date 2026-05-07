import os
import re
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime, timedelta

load_dotenv()
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

MONITORED_KEYWORDS = {
    '자사': [
        # 회사
        '드림에이지', 'DRIMAGE',
        # 아키텍트 (크로스플랫폼 MMORPG)
        '아키텍트', '드림에이지 아키텍트', '아키텍트 MMORPG',
        '아키텍트 모바일', '아키텍트 업데이트', '아키텍트 패치',
        '아키텍트 서버', '아키텍트 이벤트', '아키텍트 시즌',
        '아키텍트 던전', '아키텍트 길드', '아키텍트 레이드',
        '아키텍트 200일', '아키텍트 아시아', '아키텍트 크로스플랫폼',
        # 알케론 (배틀로얄+MOBA PvP)
        '알케론', 'arkheron', 'Arkheron', 'ARKHERON',
        '알케론 pvp', '알케론 배틀로얄', '알케론 스팀',
        '알케론 얼리액세스', '알케론 알파테스트', '알케론 CBT',
        '알케론 플레이스테이션', '알케론 Xbox',
        'arkheron steam', 'arkheron pvp',
        # 개발사
        '본파이어 스튜디오', 'Bonfire Studios',
    ],
    '경쟁사': [
        # 포트나이트
        '포트나이트', 'Fortnite', 'fortnite',
        '포트나이트 시즌', '포트나이트 업데이트', '포트나이트 콜라보',
        '에픽게임즈 포트나이트',
        # 리그오브레전드
        '리그오브레전드', 'LOL', 'LoL', '롤',
        'LCK', 'LCK 경기', '롤드컵', 'MSI',
        '롤 패치', '롤 시즌', '리그오브레전드 업데이트',
        # 배틀그라운드
        '배틀그라운드', 'PUBG',
        '배그', '배그 시즌', '배그 업데이트', '배틀그라운드 시즌',
        # 발로란트
        '발로란트', 'Valorant', 'valorant',
        'VCT', 'VCT 퍼시픽', '발로란트 패치', '발로란트 에이전트',
        '발로란트 시즌',
        # 이터널리턴
        '이터널리턴', '이터널리턴 시즌', '이터널리턴 업데이트',
        '이터널리턴 캐릭터', '블랙서바이벌',
    ],
    '업계': [
        # 장르
        '모바일게임', '온라인게임', '콘솔게임', 'PC게임',
        'MMORPG', 'RPG', 'FPS', 'MOBA', '배틀로얄', 'MMO',
        '인디게임', '크로스플랫폼',
        # 서비스
        '신작', '게임사', '서비스종료', '사전예약', '런칭',
        '얼리액세스', 'CBT', 'OBT', '정식출시', '오픈베타',
        '게임 출시', '모바일게임 출시',
        # 플랫폼
        '스팀', 'Steam', '게임패스', 'PS Plus',
        'PS5 신작', 'Xbox 신작', '닌텐도 스위치 신작',
        # 시장/순위
        '모바일게임 순위', '게임 매출 순위',
        '구글플레이 인기게임', '앱스토어 인기게임',
        '스팀 인기게임', '스팀 신작',
        # 업계 동향
        '게임사 인수', '게임사 합병', '게임사 상장', '게임사 폐업',
        '게임 서비스종료', '게임 셧다운',
        # 이벤트/전시
        '지스타', 'G-STAR', '서머게임페스트', 'GDC', 'TGS', '게임스컴',
        # 회사
        '넥슨', '넷마블', '크래프톤', '엔씨소프트', '카카오게임즈',
        '위메이드', '스마일게이트', '펄어비스', '컴투스',
        '블리자드', '라이엇', '에픽게임즈',
        '닌텐도', '소니', '마이크로소프트',
    ],
}

KEYWORD_MAP: dict = {}
for cat, keywords in MONITORED_KEYWORDS.items():
    for kw in keywords:
        KEYWORD_MAP[kw.lower()] = (kw, cat)


def extract_keywords(text: str) -> list:
    text_lower = text.lower()
    found = []
    seen = set()
    for kw_lower, (kw_original, kw_cat) in KEYWORD_MAP.items():
        if kw_lower in text_lower and kw_original not in seen:
            found.append((kw_original, kw_cat))
            seen.add(kw_original)
    return found


def crawl_keywords():
    print(f"\n🔍 키워드 추출 시작: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    since = (datetime.now() - timedelta(days=7)).isoformat()
    result = supabase.table("news").select("id, title, summary, category, collected_at").gte("collected_at", since).execute()
    news_list = result.data or []
    print(f"  → {len(news_list)}개 뉴스 분석 중...")

    existing = supabase.table("news_keywords").select("news_id").execute()
    existing_ids = set(r["news_id"] for r in (existing.data or []))

    saved = 0
    skipped = 0

    for news in news_list:
        if news["id"] in existing_ids:
            skipped += 1
            continue

        text = (news.get("title") or "") + " " + (news.get("summary") or "")
        text = re.sub(r'<[^>]+>', '', text)

        keywords = extract_keywords(text)
        if not keywords:
            skipped += 1
            continue

        rows = [{
            "news_id": news["id"],
            "keyword": kw,
            "category": cat,
            "collected_at": news.get("collected_at", datetime.now().isoformat())
        } for kw, cat in keywords]

        try:
            supabase.table("news_keywords").insert(rows).execute()
            saved += len(rows)
            print(f"  ✅ [{news['category']}] {news['title'][:40]}...")
            print(f"      → {[kw for kw, _ in keywords[:5]]}")
        except Exception as e:
            print(f"  ❌ 저장 실패: {e}")

    print(f"\n✨ 완료! {len(news_list)}개 뉴스 / {saved}개 키워드 저장 / {skipped}개 스킵")


if __name__ == "__main__":
    crawl_keywords()
