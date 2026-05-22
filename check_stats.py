import os, json
from datetime import datetime, timezone, timedelta
from collections import Counter
from supabase import create_client

supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
kst = timezone(timedelta(hours=9))
today = datetime.now(kst).strftime('%Y-%m-%d')

rows = supabase.table("community_posts").select("community,keyword,posted_at,collected_at") \
    .gte("collected_at", f"{today}T00:00:00+09:00").limit(2000).execute().data

rows7 = supabase.table("community_posts").select("collected_at") \
    .gte("collected_at", (datetime.now(kst)-timedelta(days=7)).strftime('%Y-%m-%d')) \
    .limit(5000).execute().data

comm  = Counter(r["community"] for r in rows)
kw    = Counter(r["keyword"]   for r in rows)
daily = Counter(r["collected_at"][:10] for r in rows7)
none_cnt = sum(1 for r in rows if not r.get("posted_at"))

result = {
    "checked_at": datetime.now(kst).strftime('%Y-%m-%d %H:%M KST'),
    "today_total": len(rows),
    "posted_at_null": none_cnt,
    "by_community": dict(sorted(comm.items(), key=lambda x: -x[1])),
    "by_keyword":   dict(sorted(kw.items(),   key=lambda x: -x[1])),
    "daily_7d":     dict(sorted(daily.items()))
}

with open("check_result.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(json.dumps(result, ensure_ascii=False, indent=2))
