import os, requests, re
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
nid = os.getenv("NAVER_CLIENT_ID")
nsec = os.getenv("NAVER_CLIENT_SECRET")

print("=" * 60)
print("1. 미니맵 API 테스트")
print("=" * 60)
try:
    url = "https://minimap.net/api/search/getSearchMain?searchValue=배틀그라운드"
    r = requests.get(url, headers=HEADERS, timeout=15)
    print(f"status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        posts = data.get("postList", [])
        print(f"postList 건수: {len(posts)}")
        if posts:
            p0 = posts[0]
            print(f"  첫 번째: title={p0.get('title','')[:40]}, displayTime={p0.get('displayTime','')}")
    else:
        print(f"응답: {r.text[:100]}")
except Exception as e:
    print(f"오류: {e}")

print()
print("=" * 60)
print("2. 디스이즈게임 naver news 링크 구조")
print("=" * 60)
h = {"X-Naver-Client-Id": nid, "X-Naver-Client-Secret": nsec, "User-Agent": "Mozilla/5.0"}
try:
    resp = requests.get("https://openapi.naver.com/v1/search/news.json",
        headers=h, params={"query": "배틀그라운드 thisisgame", "display": 10, "sort": "date"}, timeout=10)
    items = resp.json().get("items", [])
    for item in items[:5]:
        link = item.get("originallink", "")
        link2 = item.get("link", "")
        pub = item.get("pubDate", "")[:25]
        has_this = "thisisgame.com" in link
        print(f"  {'✅' if has_this else '❌'} originallink: {link[:60]}")
        print(f"     pubDate: {pub}")
except Exception as e:
    print(f"오류: {e}")

print()
print("=" * 60)
print("3. webkr로 thisisgame 시도")
print("=" * 60)
try:
    resp = requests.get("https://openapi.naver.com/v1/search/webkr.json",
        headers=h, params={"query": "배틀그라운드 site:thisisgame.com", "display": 5, "sort": "date"}, timeout=10)
    items = resp.json().get("items", [])
    print(f"건수: {len(items)}")
    for item in items[:3]:
        link = item.get("link", "")
        postdate = item.get("postdate", "")
        print(f"  link: {link[:60]}")
        print(f"  postdate: {postdate}")
except Exception as e:
    print(f"오류: {e}")
