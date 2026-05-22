import os, requests
from datetime import datetime, timezone, timedelta
from collections import Counter
from supabase import create_client

supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
kst = timezone(timedelta(hours=9))
today = datetime.now(kst).strftime('%Y-%m-%d')
print(f"=== 수집 현황 체크: {datetime.now(kst).strftime('%Y-%m-%d %H:%M')} KST ===\n")

# 오늘 수집 데이터
rows = supabase.table("community_posts").select("community,keyword,posted_at,collected_at") \
    .gte("collected_at", f"{today}T00:00:00+09:00").execute().data
print(f"[오늘 수집] community_posts: {len(rows)}건")

comm = Counter(r["community"] for r in rows)
print("\n커뮤니티별:")
for k, v in sorted(comm.items(), key=lambda x: -x[1]):
    print(f"  {k}: {v}건")

kw = Counter(r["keyword"] for r in rows)
print("\n키워드별:")
for k, v in sorted(kw.items(), key=lambda x: -x[1]):
    print(f"  {k}: {v}건")

# 날짜별 7일 추이
rows7 = supabase.table("community_posts").select("collected_at") \
    .gte("collected_at", (datetime.now(kst)-timedelta(days=7)).strftime('%Y-%m-%d')) \
    .limit(5000).execute().data
daily = Counter(r["collected_at"][:10] for r in rows7)
print("\n최근 7일 날짜별:")
for d in sorted(daily):
    bar = "█" * (daily[d] // 5)
    print(f"  {d}: {daily[d]:>4}건 {bar}")

# posted_at None 비율 (날짜파싱 실패율)
none_cnt = sum(1 for r in rows if not r.get("posted_at"))
print(f"\n[날짜파싱 실패] posted_at=None: {none_cnt}건 / {len(rows)}건 ({none_cnt/len(rows)*100:.1f}%)" if rows else "")
