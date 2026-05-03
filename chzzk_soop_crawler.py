import requests
import os
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime

load_dotenv()

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

KEYWORDS = {
    "자사": ["드림에이지", "아키텍트", "알케론"],
    "경쟁사": ["포트나이트", "리그오브레전드", "이터널리턴", "배틀그라운드", "발로란트"],
    "업계": ["모바일게임", "게임 출시", "신작 게임"],
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def get_tags(title):
    found = []
    for keywords in KEYWORDS.values():
        for kw in keywords:
            if kw.lower() in title.lower():
                found.append(kw)
    return found

def crawl_chzzk(keyword, category):
    url = "https://api.chzzk.naver.com/service/v1/search/lives"
    params = {"keyword": keyword, "size": 10}
    headers = {**HEADERS, "Origin": "https://chzzk.naver.com", "Referer": "https://chzzk.naver.com"}
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        data = response.json()
        items = data.get("content", {}).get("data", [])
        return items
    except Exception as e:
        print(f"  ⚠️ 치지직 요청 실패: {e}")
        return []

def crawl_soop(keyword, category):
    url = "https://vod.sooplive.co.kr/ajax/search_video_list.php"
    params = {"szSearchType": "title", "szKeyword": keyword, "nPageNo": 1, "nListCnt": 10}
    headers = {**HEADERS, "Origin": "https://www.sooplive.co.kr", "Referer": "https://www.sooplive.co.kr"}
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        data = response.json()
        items = data.get("DATA", [])
        return items
    except Exception as e:
        print(f"  ⚠️ SOOP 요청 실패: {e}")
        return []

def save_stream(title, channel, platform, url, thumbnail, category, is_live, tags):
    try:
        supabase.table("streams").insert({
            "title": title,
            "channel_name": channel,
            "platform": platform,
            "url": url,
            "thumbnail": thumbnail,
            "category": category,
            "tags": tags,
            "is_live": is_live,
            "started_at": datetime.now().isoformat(),
        }).execute()
        return True
    except Exception as e:
        if "duplicate" in str(e).lower() or "unique" in str(e).lower():
            return False
        print(f"  ❌ 저장 실패: {e}")
        return False

def crawl():
    print(f"\n🎥 치지직/SOOP 크롤링 시작: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    total, saved, skipped = 0, 0, 0

    for category, keywords in KEYWORDS.items():
        for keyword in keywords:
            # 치지직
            print(f"\n📡 치지직 - {keyword} 수집 중...")
            items = crawl_chzzk(keyword, category)
            print(f"  → {len(items)}개 발견")
            for item in items:
                total += 1
                live_info = item.get("liveInfo", {})
                channel_info = item.get("channel", {})
                title = live_info.get("liveTitle", "")
                channel = channel_info.get("channelName", "")
                live_id = live_info.get("liveId", "")
                channel_id = channel_info.get("channelId", "")
                thumbnail = live_info.get("liveThumbnailImageUrl", "")
                stream_url = f"https://chzzk.naver.com/live/{channel_id}"
                is_live = live_info.get("status") == "OPEN"
                tags = get_tags(title)
                if save_stream(title, channel, "치지직", stream_url, thumbnail, category, is_live, tags):
                    saved += 1
                    print(f"  ✅ [{'🔴LIVE' if is_live else 'VOD'}] {title[:40]}...")
                else:
                    skipped += 1

            # SOOP
            print(f"\n📡 SOOP - {keyword} 수집 중...")
            items = crawl_soop(keyword, category)
            print(f"  → {len(items)}개 발견")
            for item in items:
                total += 1
                title = item.get("BROAD_TITLE", item.get("STATION_NAME", ""))
                channel = item.get("NICK", "")
                user_id = item.get("USER_ID", "")
                thumbnail = item.get("BROAD_IMG", "")
                stream_url = f"https://www.sooplive.co.kr/{user_id}"
                is_live = item.get("BROAD_NO") is not None
                tags = get_tags(title)
                if save_stream(title, channel, "SOOP", stream_url, thumbnail, category, is_live, tags):
                    saved += 1
                    print(f"  ✅ [{'🔴LIVE' if is_live else 'VOD'}] {title[:40]}...")
                else:
                    skipped += 1

    print(f"\n✨ 완료! 총 {total}개 수집 / {saved}개 저장 / {skipped}개 중복 스킵")

if __name__ == "__main__":
    crawl()
