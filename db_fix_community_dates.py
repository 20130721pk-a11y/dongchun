import os
from datetime import datetime, timedelta, timezone
from collections import Counter
from supabase import create_client

KST = timezone(timedelta(hours=9))
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

def to_kst_date(ts_str):
    if not ts_str:
        return None
    try:
        dt = datetime.fromisoformat(str(ts_str).replace("Z", "+00:00"))
        dt = dt.replace(tzinfo=KST) if dt.tzinfo is None else dt.astimezone(KST)
        return dt.date()
    except:
        return None

print(f"=== community_posts 날짜 정합성 수정 | {'DRY RUN' if DRY_RUN else '실제 업데이트'} ===\n")
print("레코드 조회 중...")

all_records, offset = [], 0
while True:
    res = (supabase.table("community_posts")
           .select("id,community,posted_at,collected_at")
           .not_.is_("posted_at", "null")
           .range(offset, offset + 999)
           .execute())
    if not res.data:
        break
    all_records.extend(res.data)
    if len(res.data) < 1000:
        break
    offset += 1000
    print(f"  {offset}건 조회 중...")

print(f"총 {len(all_records)}건 조회 완료\n")

mismatched = []
for r in all_records:
    p_date = to_kst_date(r["posted_at"])
    c_date = to_kst_date(r["collected_at"])
    if p_date and c_date and p_date != c_date:
        mismatched.append(r)

print(f"날짜 불일치 레코드: {len(mismatched)}건 / 전체 {len(all_records)}건\n")

by_comm = Counter(r["community"] for r in mismatched)
print("커뮤니티별:")
for c, n in by_comm.most_common():
    print(f"  {c:15s}: {n}건")

print("\n날짜 차이 분포 (collected_at - posted_at):")
diffs = Counter()
for r in mismatched:
    d = (to_kst_date(r["collected_at"]) - to_kst_date(r["posted_at"])).days
    diffs[d] += 1
for d in sorted(diffs.keys()):
    print(f"  +{d}일: {diffs[d]}건")

print("\n샘플 5건:")
for r in mismatched[:5]:
    print(f"  [{r['community']}] posted={str(r['posted_at'])[:10]}  collected={str(r['collected_at'])[:10]}")

if DRY_RUN:
    print(f"\n[DRY RUN] 업데이트 없음. DRY_RUN=false 로 재실행하면 실제 적용됩니다.")
else:
    print(f"\n⚠️  {len(mismatched)}건 collected_at → posted_at 으로 업데이트 시작...")
    ok, fail = 0, 0
    for i, r in enumerate(mismatched):
        try:
            (supabase.table("community_posts")
             .update({"collected_at": r["posted_at"]})
             .eq("id", r["id"])
             .execute())
            ok += 1
            if (i + 1) % 200 == 0:
                print(f"  {i+1}/{len(mismatched)}건 처리 완료...")
        except Exception as e:
            fail += 1
            print(f"  FAIL id={r['id']}: {e}")
    print(f"\n✅ 완료: {ok}건 업데이트 / {fail}건 실패")
