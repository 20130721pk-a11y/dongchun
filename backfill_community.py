"""
1회성 커뮤니티 백필 크롤러 - 최근 7일치 수집
is_recent를 7일(168시간) 기준으로 오버라이드
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))

import community_crawler as _cc
from datetime import datetime, timezone, timedelta

def is_recent_7d(posted_at, hours=168):
    if not posted_at:
        return False
    try:
        import pytz
        pub = datetime.fromisoformat(str(posted_at).replace("Z", "+00:00"))
        if pub.tzinfo is None:
            pub = pub.replace(tzinfo=timezone.utc)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        return pub >= cutoff
    except:
        return False

_cc.is_recent = is_recent_7d

print("🔄 커뮤니티 백필 크롤러 시작 (최근 7일치 수집)")
print(f"   수집 범위: {(datetime.now(timezone.utc) - timedelta(hours=168)).strftime('%Y-%m-%d')} ~ 오늘\n")

_cc.crawl()
