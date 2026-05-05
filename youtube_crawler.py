import requests
import os
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime

load_dotenv()

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

KEYWORDS = {
    "자사": ["드림에이지", "아키텍트", "알케론"],
    "경쟁사": ["포트나이트", "리그오브레전드", "이터널리턴", "배틀그라운드", "발로란트"],
    "업계": ["모바일게임 신작", "게임 출시", "게임 사전예약"],
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

def is_game_related(title, summary=""):
    text = (title + " " + (summary or "")).lower()
    # 자사 키워드는 무조건 통과
    own_keywords = ["드림에이지", "알케론", "아키텍트", "arkheron", "drimage"]
    if any(kw.lower() in text for kw in own_keywords):
        return True
    return any(kw.lower() in text for kw in GAME_KEYWORDS)

def search_youtube(keyword, max_results=10):
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "q": keyword,
        "type": "video",
        "order": "date",
        "maxResults": max_results,
        "regionCode": "KR",
        "relevanceLanguage": "ko",
        "key": YOUTUBE_API_KEY,
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        return response.json().get("items", [])
    except Exception as e:
        print(f"  ⚠️ 유튜브 요청 실패: {e}")
        return []

def crawl_youtube():
    print(f"\n🎥 유튜브 크롤링 시작: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    total, saved, skipped = 0, 0, 0

    for category, keywords in KEYWORDS.items():
        for keyword in keywords:
            print(f"\n📡 유튜브 - {keyword} 수집 중...")
            items = search_youtube(keyword)
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

                tags = []
                for kws in KEYWORDS.values():
                    for kw in kws:
                        if kw.lower() in title.lower():
                            tags.append(kw)

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

    print(f"\n✨ 완료! 총 {total}개 수집 / {saved}개 저장 / {skipped}개 중복 스킵")

if __name__ == "__main__":
    crawl_youtube()
