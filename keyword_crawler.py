import os
import re
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime, timedelta

load_dotenv()
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

# 불용어 목록
STOPWORDS = set([
    # 조사/접속사
    '이', '그', '저', '것', '수', '등', '및', '를', '을', '가', '은', '는',
    '에', '의', '로', '으로', '와', '과', '도', '에서', '에게', '부터', '까지',
    '위해', '통해', '대해', '위한', '대한', '관련', '따른', '따라', '관한',
    # 시간/부사
    '이후', '이전', '현재', '최근', '지난', '올해', '내년', '오는', '지금',
    '다시', '또', '더', '매우', '가장', '모든', '각', '전', '후', '중',
    '내', '외', '간', '당', '약', '총', '이번', '오늘', '내일', '어제',
    # 언론/미디어
    '기자', '뉴스', '기사', '보도', '발표', '공개', '확인', '예정', '진행',
    '영상', '사진', '포토', '인터뷰', '칼럼', '리뷰', '현장', '결과',
    # 일반 동사형
    '하다', '있다', '되다', '않다', '없다', '같다', '했다', '됐다',
    '한다', '된다', '있는', '없는', '하는', '되는',
    # 숫자/특수
    'quot', 'amp', 'nbsp', 'http', 'https', 'com', 'www',
    # 게임 무관 키워드
    '매입', '판매', '구매', '할인', '이벤트', '쿠폰', '혜택', '추천',
    '방법', '하는곳', '최고가', '시세', '정직하게', '중고',
    '컴퓨터', '노트북', '모니터', '사무용',
    '어린이날', '롯데', '백화점', '카페', '편의점',
    # 회사명 기본형
    '코리아', '스튜디오', '엔터테인먼트',
])

def extract_keywords(text: str, top_n: int = 10):
    words = re.findall(r'[가-힣A-Za-z0-9][가-힣A-Za-z0-9]{1,}', text)
    freq: dict = {}
    for w in words:
        if w not in STOPWORDS and len(w) >= 2:
            freq[w] = freq.get(w, 0) + 1
    return sorted(freq.items(), key=lambda x: x[1], reverse=True)[:top_n]

def crawl_keywords():
    print(f"\n🔍 키워드 추출 시작: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    # 최근 7일 뉴스 가져오기
    since = (datetime.now() - timedelta(days=7)).isoformat()
    result = supabase.table("news").select("id, title, summary, category").gte("collected_at", since).execute()
    news_list = result.data or []
    print(f"  → {len(news_list)}개 뉴스 분석 중...")

    # 이미 처리된 news_id 가져오기
    existing = supabase.table("news_keywords").select("news_id").execute()
    existing_ids = set(r["news_id"] for r in (existing.data or []))

    saved = 0
    skipped = 0

    for news in news_list:
        if news["id"] in existing_ids:
            skipped += 1
            continue

        text = (news.get("title") or "") + " " + (news.get("summary") or "")
        text = re.sub(r'<[^>]+>', '', text)  # HTML 제거
        
        keywords = extract_keywords(text)
        if not keywords:
            continue

        rows = [{
            "news_id": news["id"],
            "keyword": kw,
            "category": news.get("category"),
            "collected_at": datetime.now().isoformat()
        } for kw, _ in keywords]

        try:
            supabase.table("news_keywords").insert(rows).execute()
            saved += len(rows)
            print(f"  ✅ [{news['category']}] {news['title'][:30]}... → {[kw for kw,_ in keywords[:5]]}")
        except Exception as e:
            print(f"  ❌ 저장 실패: {e}")

    print(f"\n✨ 완료! {len(news_list)}개 뉴스 / {saved}개 키워드 저장 / {skipped}개 스킵")

if __name__ == "__main__":
    crawl_keywords()
