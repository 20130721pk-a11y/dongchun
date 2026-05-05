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


GAME_KEYWORDS = [
    "게임", "게이머", "게임사", "플레이", "출시", "업데이트", "패치", "서버",
    "캐릭터", "아이템", "스킬", "pvp", "pve", "rpg", "fps", "moba",
    "mmorpg", "모바일게임", "스팀", "콘솔", "pc방", "e스포츠", "esports",
    "대회", "시즌", "배틀", "테스트", "베타", "신작", "런칭", "섭종",
    "드림에이지", "알케론", "아키텍트", "포트나이트", "발로란트",
    "배틀그라운드", "pubg", "valorant", "fortnite", "이터널리턴",
    "리그오브레전드", "lol", "steam", "gaming", "game", "gameplay"
]

def is_korean(text):
    korean_chars = len([c for c in text if '가' <= c <= '힣'])
    total_chars = len([c for c in text if c.strip()])
    return total_chars == 0 or (korean_chars / total_chars) >= 0.2

def is_game_related(title, summary=""):
    if not is_korean(title):
        return False
    text = (title + " " + (summary or "")).lower()
    if "드림에이지" in text or "알케론" in text or "arkheron" in text or "drimage" in text:
        return True
    if "아키텍트" in text and any(kw in text for kw in ["게임", "mmorpg", "rpg", "pvp", "모바일", "크로스플랫폼", "심연", "쟁"]):
        return True
    return any(kw.lower() in text for kw in GAME_KEYWORDS)

def get_tags(title):
    found = []
    for keywords in KEYWORDS.values():
        for kw in keywords:
            if kw.lower() in title.lower():
                found.append(kw)
    return found

def crawl_chzzk(keyword, category):
    headers = {**HEADERS, "Origin": "https://chzzk.naver.com", "Referer": "https://chzzk.naver.com"}
    results = []
    try:
        # 키워드 검색으로 라이브 수집
        url = "https://api.chzzk.naver.com/service/v1/search/lives"
        params = {"keyword": keyword, "size": 20}
        response = requests.get(url, params=params, headers=headers, timeout=10)
        data = response.json()
        items = data.get("content", {}).get("data", [])
        for item in items:
            live = item.get("live", item)
            channel = item.get("channel", {})
            title = live.get("liveTitle", "")
            live_id = live.get("liveId", "")
            channel_id = channel.get("channelId", live.get("channel", {}).get("channelId", ""))
            thumbnail = live.get("liveImageUrl", "").replace("{type}", "480")
            stream_url = f"https://chzzk.naver.com/live/{channel_id}" if channel_id else ""
            channel_name = channel.get("channelName", live.get("channel", {}).get("channelName", ""))
            concurrent = live.get("concurrentUserCount", 0)
            results.append({
                "title": title,
                "channel": channel_name,
                "url": stream_url,
                "thumbnail": thumbnail,
                "is_live": True,
                "viewers": concurrent
            })
    except Exception as e:
        print(f"  ⚠️ 치지직 요청 실패: {e}")
    return results

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

def save_stream(title, channel, platform, url, thumbnail, category, is_live, tags, viewer_count=0):
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
            "viewer_count": viewer_count,
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
                title = item.get("title", "")
                channel = item.get("channel", "")
                stream_url = item.get("url", "")
                thumbnail = item.get("thumbnail", "")
                is_live = item.get("is_live", True)
                tags = get_tags(title)
                if not is_game_related(title):
                    skipped += 1
                    continue
                viewer_count = item.get("viewers", 0)
                if save_stream(title, channel, "치지직", stream_url, thumbnail, category, is_live, tags, viewer_count):
                    saved += 1
                    print(f"  ✅ [🔴LIVE] {title[:40]}...")
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
