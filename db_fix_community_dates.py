"""
DB 날짜 정합성 수정 스크립트
community_posts 테이블에서 collected_at이 posted_at과 다른 날짜인 레코드를
collected_at = posted_at 로 업데이트

실행 전 확인사항:
- 영향 범위를 먼저 DRY_RUN=True 로 출력
- 확인 후 DRY_RUN=False 로 실제 업데이트

로직:
- posted_at의 KST 날짜 != collected_at의 KST 날짜 인 레코드만 대상
- posted_at이 NULL인 레코드는 제외
- collected_at을 posted_at 값으로 덮어씀
  (대시보드 7일 차트가 collected_at 기준이므로 실제 게시일로 맞춤)
"""

import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

KST = timezone(timedelta(hours=9))
DRY_RUN = True  # True: 영향 범위만 출력 / False: 실제 업데이트

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

def to_kst_date(ts_str):
    if not ts_str:
        return None
    try:
        dt = datetime.fromisoformat(str(ts_str).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=KST)
        else:
            dt = dt.astimezone(KST)
        return dt.date()
    except:
        return None

def main():
    print("=== community_posts 날짜 정합성 수정 ===")
    print(f"모드: {'DRY RUN (확인만)' if DRY_RUN else '⚠️  실제 업데이트'}\n")

    # 전체 레코드 조회 (posted_at 있는 것만)
    print("레코드 조회 중...")
    all_records = []
    offset = 0
    batch = 1000
    while True:
        res = supabase.table("community_posts") \
            .select("id, community, posted_at, collected_at") \
            .not_.is_("posted_at", "null") \
            .range(offset, offset + batch - 1) \
            .execute()
        if not res.data:
            break
        all_records.extend(res.data)
        if len(res.data) < batch:
            break
        offset += batch
        print(f"  {offset}건 조회됨...")

    print(f"총 {len(all_records)}건 조회 완료\n")

    # 날짜 불일치 레코드 필터링
    mismatched = []
    for r in all_records:
        p_date = to_kst_date(r["posted_at"])
        c_date = to_kst_date(r["collected_at"])
        if p_date and c_date and p_date != c_date:
            mismatched.append(r)

    print(f"날짜 불일치 레코드: {len(mismatched)}건 (전체 {len(all_records)}건 중)\n")

    # 커뮤니티별 통계
    from collections import Counter
    by_community = Counter(r["community"] for r in mismatched)
    print("커뮤니티별 불일치 현황:")
    for comm, cnt in by_community.most_common():
        print(f"  {comm:15s}: {cnt}건")

    # 날짜 차이 분포
    print("\n날짜 차이 분포 (collected - posted, 일 기준):")
    diffs = Counter()
    for r in mismatched:
        p = to_kst_date(r["posted_at"])
        c = to_kst_date(r["collected_at"])
        diff = (c - p).days
        bucket = f"+{diff}일" if diff > 0 else f"{diff}일"
        diffs[bucket] += 1
    for diff, cnt in sorted(diffs.items(), key=lambda x: int(x[0].replace('+','').replace('일',''))):
        print(f"  {diff:8s}: {cnt}건")

    if DRY_RUN:
        print(f"\n[DRY RUN] 실제 업데이트 없음.")
        print(f"실제 업데이트를 진행하려면 DRY_RUN = False 로 변경 후 재실행")
        return

    # 실제 업데이트 (배치 처리)
    print(f"\n⚠️  {len(mismatched)}건 업데이트 시작...")
    updated = 0
    failed = 0
    for i, r in enumerate(mismatched):
        try:
            supabase.table("community_posts") \
                .update({"collected_at": r["posted_at"]}) \
                .eq("id", r["id"]) \
                .execute()
            updated += 1
            if (i + 1) % 100 == 0:
                print(f"  {i+1}/{len(mismatched)}건 처리...")
        except Exception as e:
            failed += 1
            print(f"  ❌ id={r['id']} 실패: {e}")

    print(f"\n✅ 완료: {updated}건 업데이트 / {failed}건 실패")

if __name__ == "__main__":
    main()
