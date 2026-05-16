import requests
import os
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime

load_dotenv()
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

KEYWORDS = {
    "자사": ["드림에이지", "알케론", "arkheron", "드림에이지 아키텍트"],
    "경쟁사": ["포트나이트", "리그오브레전드", "이터널리턴", "배틀그라운드", "발로란트", "오버워치2", "에이펙스 레전드"],

}


SEGMENT_ALIASES = {
    "드림에이지":    ["드림에이지", "drimage", "dream age"],
    "알케론":        ["알케론", "arkheron"],
    "아키텍트":      ["아키텍트", "드림에이지 아키텍트"],
    "포트나이트":    ["포트나이트", "fortnite"],
    "리그오브레전드":["리그오브레전드", "리그 오브 레전드", "league of legends", "lol", "롤"],
    "이터널리턴":    ["이터널리턴", "이터널 리턴", "eternal return", "eternalreturn", "블랙서바이벌"],
    "배틀그라운드":  ["배틀그라운드", "pubg", "battlegrounds", "배그"],
    "발로란트":      ["발로란트", "valorant"],
}


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


GAME_KEYWORDS = [
    "게임","게이머","플레이","출시","업데이트","패치","서버","캐릭터","아이템",
    "스킬","pvp","pve","rpg","fps","moba","mmorpg","모바일게임","스팀","콘솔",
    "e스포츠","esports","대회","시즌","배틀","테스트","베타","신작","런칭",
    "드림에이지","알케론","아키텍트","포트나이트","발로란트",
    "배틀그라운드","pubg","valorant","fortnite","이터널리턴",
    "리그오브레전드","lol","gaming","game","gameplay"
]

def is_game_related(title):
    text = title.lower()
    if any(kw in text for kw in ["드림에이지","알케론","arkheron","drimage"]):
        return True
    return any(kw.lower() in text for kw in GAME_KEYWORDS)

def get_tags(title, summary=""):
    text = (title + " " + (summary or "")).lower()
    found = []
    for keywords in KEYWORDS.values():
        for kw in keywords:
            if kw.lower() in text:
                found.append(kw)
    return found

def crawl_chzzk(keyword, category, max_pages=5):
    """페이지네이션으로 최대 100개 수집"""
    headers = {**HEADERS, "Origin": "https://chzzk.naver.com", "Referer": "https://chzzk.naver.com"}
    results = []
    next_offset = 0

    for _ in range(max_pages):
        try:
            url = "https://api.chzzk.naver.com/service/v1/search/lives"
            params = {"keyword": keyword, "size": 20, "offset": next_offset}
            response = requests.get(url, params=params, headers=headers, timeout=10)
            data = response.json()
            content = data.get("content", {})
            items = content.get("data", [])
            if not items:
                break

            for item in items:
                live = item.get("live", item)
                channel = item.get("channel", {})
                title = live.get("liveTitle", "")
                channel_id = channel.get("channelId", live.get("channel", {}).get("channelId", ""))
                thumbnail = (live.get("liveImageUrl") or "").replace("{type}", "480")
                stream_url = f"https://chzzk.naver.com/live/{channel_id}" if channel_id else ""
                channel_name = channel.get("channelName", live.get("channel", {}).get("channelName", ""))
                concurrent = live.get("concurrentUserCount", 0)
                results.append({
                    "title": title,
                    "channel": channel_name,
                    "url": stream_url,
                    "thumbnail": thumbnail,
                    "is_live": True,
                    "viewers": concurrent,
                    "started_at": live.get("openDate") or live.get("liveStartDate") or datetime.now().isoformat()
                })

            # 다음 페이지 여부 확인
            page_info = content.get("page", {})
            if len(items) < 20:
                break
            next_offset += 20

        except Exception as e:
            print(f"  ⚠️ 치지직 요청 실패: {e}")
            break

    return results

def save_stream(title, channel, platform, url, thumbnail, category, is_live, tags, viewer_count=0, started_at=None):
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
            "started_at": started_at or datetime.now().isoformat(),
            "viewer_count": viewer_count,
        }).execute()
        return True
    except Exception as e:
        if "duplicate" in str(e).lower() or "unique" in str(e).lower():
            return False
        print(f"  ❌ 저장 실패: {e}")
        return False

def crawl():
    print(f"\n🎥 치지직 크롤링 시작: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    total, saved, skipped = 0, 0, 0

    for category, keywords in KEYWORDS.items():
        for keyword in keywords:
            print(f"\n📡 치지직 - {keyword} 수집 중...")
            max_p = 5 if category == "자사" else 2
            items = crawl_chzzk(keyword, category, max_pages=max_p)
            print(f"  → {len(items)}개 발견")
            for item in items:
                total += 1
                title = item.get("title", "") or ""
                channel = item.get("channel", "") or ""
                stream_url = item.get("url", "")
                thumbnail = item.get("thumbnail", "")
                viewer_count = item.get("viewers", 0)
                tags = get_tags(title)
                # 검색 키워드의 정식 세그먼트명을 태그에 강제 추가
                for seg, aliases in SEGMENT_ALIASES.items():
                    if keyword.lower() in [a.lower() for a in aliases]:
                        if seg not in tags: tags.append(seg)
                        break
                else:
                    if keyword not in tags: tags.append(keyword)
                if not is_game_related(title):
                    skipped += 1
                    continue
                # 당일(KST) 방송만 수집
                started = item.get("started_at") or ""
                if started:
                    try:
                        import pytz
                        from datetime import datetime as dt2
                        pub_dt = dt2.fromisoformat(str(started).replace("Z", "+00:00"))
                        kst = pytz.timezone('Asia/Seoul')
                        if pub_dt.astimezone(kst).date() < dt2.now(kst).date():
                            skipped += 1
                            continue
                    except:
                        pass
                if save_stream(title, channel, "치지직", stream_url, thumbnail, category, True, tags, viewer_count, item.get("started_at")):
                    saved += 1
                    print(f"  ✅ [🔴LIVE] {title[:40]}...")
                else:
                    skipped += 1

    print(f"\n✨ 완료! 총 {total}개 수집 / {saved}개 저장 / {skipped}개 중복 스킵")

if __name__ == "__main__":
    crawl()
