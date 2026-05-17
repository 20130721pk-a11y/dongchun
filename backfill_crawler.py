"""
1회성 백필 크롤러 - 최근 7일치 뉴스 수집
정상 운영 크롤러(crawler.py)는 48시간 기준이나,
이 스크립트는 168시간(7일) 기준으로 1회 실행
"""
import os
os.environ['BACKFILL_HOURS'] = '168'

# crawler.py의 모든 함수를 그대로 사용하되 is_recent만 오버라이드
import sys
sys.path.insert(0, os.path.dirname(__file__))

import crawler as _crawler
from datetime import datetime, timezone, timedelta

# is_recent를 7일 기준으로 오버라이드
def is_recent_7d(published_iso, hours=168):
    if not published_iso:
        return False
    try:
        pub = datetime.fromisoformat(published_iso.replace("Z", "+00:00"))
        if pub.tzinfo is None:
            pub = pub.replace(tzinfo=timezone.utc)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        return pub >= cutoff
    except:
        return False

_crawler.is_recent = is_recent_7d

print("🔄 백필 크롤러 시작 (최근 7일치 수집)")
print(f"   기준 시각: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC")
print(f"   수집 범위: {(datetime.now(timezone.utc) - timedelta(hours=168)).strftime('%Y-%m-%d')} ~ 오늘\n")

_crawler.crawl()
