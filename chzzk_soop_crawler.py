import requests
import os
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime, timedelta, timezone

load_dotenv()
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

KST = timezone(timedelta(hours=9))

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

def is_today_kst(dt_str):
    """KST 기준 오늘 날짜 방송인지 확인 (pytz 없이 stdlib)"""
    if not dt_str:
        return True
    try:
        pub = datetime.fromisoformat(str(dt_str).replace("Z", "+00:00"))
        if pub.tzinfo is None:
            pub = pub.replace(tzinfo=KST)
        return pub.astimezone(KST).date() >= datetime.now(KST).date()
    except:
        return True


# ── 치지직 ─────────────────────────────────────────────
def crawl_chzzk(keyword, category, max_pages=5):
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
                started_at = live.get("openDate") or live.get("liveStartDate") or datetime.now(KST).isoformat()
                results.append({
                    "title": title, "channel": channel_name, "url": stream_url,
                    "thumbnail": thumbnail, "is_live": True,
                    "viewers": concurrent, "started_at": started_at,
                })

            if len(items) < 20:
                break
            next_offset += 20

        except Exception as e:
            print(f"  ⚠️ 치지직 요청 실패: {e}")
            break

    return results


# ── SOOP ───────────────────────────────────────────────
def crawl_soop(keyword, category, max_pages=3):
    """SOOP 라이브 방송 검색"""
    results = []
    headers = {**HEADERS, "Origin": "https://www.sooplive.co.kr", "Referer": "https://www.sooplive.co.kr"}

    for page in range(1, max_pages + 1):
        try:
            # SOOP 라이브 검색 API
            url = "https://www.sooplive.co.kr/api/search/getAll.php"
            params = {
                "szKeyword": keyword,
                "nPageNo": page,
                "szType": "live",
                "nListCnt": 20,
            }
            response = requests.get(url, params=params, headers=headers, timeout=10)
            if response.status_code != 200:
                break
            data = response.json()
            items = data.get("REAL_BROAD", data.get("data", data.get("DATA", [])))
            if not items:
                break

            for item in items:
                title = item.get("BROAD_TITLE", item.get("title", ""))
                user_id = item.get("USER_ID", item.get("userId", ""))
                channel_name = item.get("USER_NICK", item.get("nickName", user_id))
                thumbnail = item.get("BROAD_IMG", item.get("thumbnail", ""))
                if thumbnail and not thumbnail.startswith("http"):
                    thumbnail = "https:" + thumbnail
                stream_url = f"https://www.sooplive.co.kr/{user_id}" if user_id else ""
                viewer_count = int(item.get("TOTAL_VIEW_CNT", item.get("viewerCount", 0)) or 0)
                started_at = item.get("BROAD_START", item.get("startedAt", datetime.now(KST).isoformat()))

                results.append({
                    "title": title, "channel": channel_name, "url": stream_url,
                    "thumbnail": thumbnail, "is_live": True,
                    "viewers": viewer_count, "started_at": started_at,
                })

            if len(items) < 20:
                break

        except Exception as e:
            print(f"  ⚠️ SOOP 요청 실패 (page {page}): {e}")
            break

    return results


# ── 저장 ───────────────────────────────────────────────
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
            "started_at": started_at or datetime.now(KST).isoformat(),
            "viewer_count": viewer_count,
        }).execute()
        return True
    except Exception as e:
        if "duplicate" in str(e).lower() or "unique" in str(e).lower():
            return False
        print(f"  ❌ 저장 실패: {e}")
        return False


# ── 메인 ───────────────────────────────────────────────
def crawl():
    print(f"\n🎥 치지직/SOOP 크롤링 시작: {datetime.now(KST).strftime('%Y-%m-%d %H:%M')} KST")
    total, saved, skipped = 0, 0, 0

    crawlers = [
        ("치지직", crawl_chzzk),
        ("SOOP",   crawl_soop),
    ]

    for platform, crawler_fn in crawlers:
        for category, keywords in KEYWORDS.items():
            for keyword in keywords:
                print(f"\n📡 {platform} - {keyword} 수집 중...")
                max_p = 5 if category == "자사" else 3
                items = crawler_fn(keyword, category, max_pages=max_p)
                print(f"  → {len(items)}개 발견")

                for item in items:
                    total += 1
                    title = item.get("title", "") or ""
                    channel = item.get("channel", "") or ""
                    stream_url = item.get("url", "")
                    thumbnail = item.get("thumbnail", "")
                    viewer_count = item.get("viewers", 0)
                    started_at = item.get("started_at")

                    # 태그
                    tags = get_tags(title)
                    for seg, aliases in SEGMENT_ALIASES.items():
                        if keyword.lower() in [a.lower() for a in aliases]:
                            if seg not in tags:
                                tags.append(seg)
                            break
                    else:
                        if keyword not in tags:
                            tags.append(keyword)

                    # 게임 필터
                    if not is_game_related(title):
                        skipped += 1
                        continue

                    # 당일(KST) 필터 — pytz 없이 stdlib
                    if not is_today_kst(started_at):
                        skipped += 1
                        continue

                    if save_stream(title, channel, platform, stream_url, thumbnail,
                                   category, True, tags, viewer_count, started_at):
                        saved += 1
                        print(f"  ✅ [{platform}][🔴LIVE] {title[:40]}...")
                    else:
                        skipped += 1

    print(f"\n✨ 완료! 총 {total}개 수집 / {saved}개 저장 / {skipped}개 중복 스킵")

if __name__ == "__main__":
    crawl()
