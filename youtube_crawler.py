import requests
import os
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime, timedelta, timezone

load_dotenv()

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

KST = timezone(timedelta(hours=9))

KEYWORDS = {
    "자사": ["드림에이지", "알케론", "arkheron", "드림에이지 아키텍트"],
    "경쟁사": ["포트나이트", "리그오브레전드", "이터널리턴", "배틀그라운드", "발로란트", "오버워치2", "에이펙스 레전드"],
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
    if "아키텍트" in text:
        return True
    return any(kw.lower() in text for kw in GAME_KEYWORDS)

def is_today_kst(published_str):
    """published_at(ISO8601) 문자열이 오늘(KST) 날짜인지 확인"""
    if not published_str:
        return True  # 날짜 없으면 통과
    try:
        pub_dt = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
        return pub_dt.astimezone(KST).date() >= datetime.now(KST).date()
    except Exception:
        return True

def search_youtube(keyword, max_results=50, live_only=False, max_pages=1):
    url = "https://www.googleapis.com/youtube/v3/search"
    all_items = []
    next_page_token = None

    if not YOUTUBE_API_KEY:
        print("  ❌ YOUTUBE_API_KEY 환경변수 없음")
        return []

    for _ in range(max_pages):
        params = {
            "part": "snippet",
            "q": keyword,
            "type": "video",
            "order": "date",
            "maxResults": 50,
            "regionCode": "KR",
            "relevanceLanguage": "ko",
            "key": YOUTUBE_API_KEY,
        }
        if live_only:
            params["eventType"] = "live"
        if next_page_token:
            params["pageToken"] = next_page_token
        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()

            # ✅ API 오류 명시적 로깅
            if "error" in data:
                err = data["error"]
                code = err.get("code", "?")
                msg = err.get("message", "")
                reason = err.get("errors", [{}])[0].get("reason", "")
                print(f"  ❌ YouTube API 오류 [{code}] {reason}: {msg[:80]}")
                break

            items = data.get("items", [])
            all_items.extend(items)
            next_page_token = data.get("nextPageToken")
            if not next_page_token or len(items) < 50:
                break
        except Exception as e:
            print(f"  ⚠️ 유튜브 요청 실패: {e}")
            break
    return all_items


SEGMENT_ALIASES = {
    "드림에이지":    ["드림에이지", "drimage", "dream age"],
    "알케론":        ["알케론", "arkheron"],
    "아키텍트":      ["아키텍트", "드림에이지 아키텍트"],
    "포트나이트":    ["포트나이트", "fortnite"],
    "리그오브레전드":["리그오브레전드", "league of legends", "lol", "롤"],
    "이터널리턴":    ["이터널리턴", "eternal return", "블랙서바이벌"],
    "배틀그라운드":  ["배틀그라운드", "pubg", "배그"],
    "발로란트":      ["발로란트", "valorant"],
}

def get_tags(title, summary=""):
    text = (title + " " + (summary or "")).lower()
    found = []
    for keywords in KEYWORDS.values():
        for kw in keywords:
            if kw.lower() in text:
                found.append(kw)
    return found

def crawl_youtube():
    print(f"\n🎥 유튜브 크롤링 시작: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    if not YOUTUBE_API_KEY:
        print("❌ YOUTUBE_API_KEY 없음. 크롤링 중단.")
        return
    total, saved, skipped = 0, 0, 0

    # 일반 영상 수집
    for category, keywords in KEYWORDS.items():
        for keyword in keywords:
            print(f"\n📡 유튜브 - {keyword} 수집 중...")
            items = search_youtube(keyword, max_results=50)
            print(f"  → {len(items)}개 발견")

            for item in items:
                total += 1
                snippet = item.get("snippet", {})
                video_id = item.get("id", {}).get("videoId", "")
                title = snippet.get("title", "")
                channel = snippet.get("channelTitle", "")
                thumbnail = snippet.get("thumbnails", {}).get("medium", {}).get("url", "")
                published = snippet.get("publishedAt", None)
                url = f"https://www.youtube.com/watch?v={video_id}"
                is_live = snippet.get("liveBroadcastContent") == "live"

                tags = get_tags(title)
                for seg, aliases in SEGMENT_ALIASES.items():
                    if keyword.lower() in [a.lower() for a in aliases]:
                        if seg not in tags: tags.append(seg)
                        break
                else:
                    if keyword not in tags: tags.append(keyword)

                if not is_game_related(title):
                    skipped += 1
                    continue

                if not is_today_kst(published):
                    skipped += 1
                    continue

                try:
                    supabase.table("streams").insert({
                        "title": title,
                        "channel_name": channel,
                        "platform": "유튜브",
                        "url": url,
                        "thumbnail": thumbnail,
                        "category": category,
                        "tags": tags,
                        "is_live": is_live,
                        "started_at": published,
                    }).execute()
                    saved += 1
                    live_tag = "🔴 LIVE " if is_live else ""
                    print(f"  ✅ [{category}] {live_tag}{title[:40]}...")
                except Exception as e:
                    if "duplicate" in str(e).lower() or "unique" in str(e).lower():
                        skipped += 1
                    else:
                        print(f"  ❌ 저장 실패: {e}")

    # 라이브 방송 수집
    live_keywords = {
        "자사": ["드림에이지", "알케론", "arkheron", "드림에이지 아키텍트"],
        "경쟁사": ["포트나이트", "발로란트", "배틀그라운드", "이터널리턴", "리그오브레전드", "오버워치2", "에이펙스 레전드"],
    }
    for category, keywords in live_keywords.items():
        for keyword in keywords:
            print(f"\n📡 유튜브 라이브 - {keyword} 수집 중...")
            items = search_youtube(keyword, max_results=50, live_only=True)
            print(f"  → {len(items)}개 발견")
            for item in items:
                total += 1
                snippet = item.get("snippet", {})
                video_id = item.get("id", {}).get("videoId", "")
                title = snippet.get("title", "")
                channel = snippet.get("channelTitle", "")
                thumbnail = snippet.get("thumbnails", {}).get("medium", {}).get("url", "")
                published = snippet.get("publishedAt", None)
                url = f"https://www.youtube.com/watch?v={video_id}"
                tags = []
                for kws in KEYWORDS.values():
                    for kw in kws:
                        if kw.lower() in title.lower():
                            tags.append(kw)
                if not is_game_related(title):
                    skipped += 1
                    continue

                if not is_today_kst(published):
                    skipped += 1
                    continue

                try:
                    supabase.table("streams").insert({
                        "title": title,
                        "channel_name": channel,
                        "platform": "유튜브",
                        "url": url,
                        "thumbnail": thumbnail,
                        "category": category,
                        "tags": tags,
                        "is_live": True,
                        "started_at": published,
                    }).execute()
                    saved += 1
                    print(f"  ✅ [🔴LIVE] {title[:40]}...")
                except Exception as e:
                    if "duplicate" in str(e).lower() or "unique" in str(e).lower():
                        skipped += 1
                    else:
                        print(f"  ❌ 저장 실패: {e}")

    print(f"\n✨ 완료! 총 {total}개 수집 / {saved}개 저장 / {skipped}개 중복 스킵")

if __name__ == "__main__":
    crawl_youtube()
