import os
from datetime import datetime, timedelta, timezone
from collections import Counter
from supabase import create_client

KST = timezone(timedelta(hours=9))
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

today_start = datetime.now(KST).strftime("%Y-%m-%d") + "T00:00:00+09:00"
today_str = datetime.now(KST).strftime("%Y-%m-%d")

# 삭제 전 현황 출력
res = supabase.table("community_posts").select("community").gte("collected_at", today_start).limit(5000).execute()
counts = Counter(r["community"] for r in res.data)
total = len(res.data)
print(f"=== 오늘({today_str} KST) community_posts 삭제 ===")
print(f"삭제 대상: {total}건")
for c, n in counts.most_common():
    print(f"  {c}: {n}건")

# 삭제 실행
supabase.table("community_posts").delete().gte("collected_at", today_start).execute()
print(f"\n✅ 삭제 완료: {total}건")
