import os, requests, re
from datetime import datetime, timezone
from supabase import create_client
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")
NAVER_CLIENT_ID = os.environ.get("NAVER_CLIENT_ID", "")
NAVER_CLIENT_SECRET = os.environ.get("NAVER_CLIENT_SECRET", "")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
COMPETITORS = {
    "포트나이트":     {"fb_page": "FortniteKO",           "queries": ["포트나이트 광고","fortnite korea"]},
    "배틀그라운드":   {"fb_page": "PUBGBATTLEGROUNDSKR",   "queries": ["배틀그라운드 광고","PUBG korea"]},
    "발로란트":       {"fb_page": "VALORANTKR",            "queries": ["발로란트 광고","valorant korea"]},
    "리그오브레전드": {"fb_page": "LeagueofLegendsKor",    "queries": ["리그오브레전드 광고","LoL korea"]},
    "오버워치2":      {"fb_page": "OverwatchKR",           "queries": ["오버워치 광고","overwatch korea"]},
    "에이펙스 레전드":{"fb_page": "playapex",              "queries": ["에이펙스 광고","apex legends korea"]},
    "이터널리턴":     {"fb_page": "EternalReturnGame",     "queries": ["이터널리턴 광고","eternal return"]},
}
def save_ad(platform,competitor,title,description,url,thumbnail,published_at,ad_type,views=0,region=""):
    try:
        supabase.table("competitor_ads").upsert({"platform":platform,"competitor":competitor,"title":title[:500] if title else "","description":description[:1000] if description else "","url":url,"thumbnail":thumbnail,"published_at":published_at,"ad_type":ad_type,"views":views,"region":region},on_conflict="url").execute()
    except Exception as e:
        print(f"저장 오류: {e}")


GOOGLE_COMPETITORS = {
    "포트나이트":     {"queries": ["Epic Games"],                              "label": "Epic Games(포트나이트)"},
    "배틀그라운드":   {"queries": ["PUBG Corporation", "Krafton", "PUBG"],   "label": "Krafton(배틀그라운드)"},
    "발로란트":       {"queries": ["Riot Games"],                              "label": "Riot Games(발로란트)"},
    "리그오브레전드": {"queries": ["Riot Games"],                              "label": "Riot Games(리그오브레전드)"},
    "오버워치2":      {"queries": ["Blizzard Entertainment"],                  "label": "Blizzard(오버워치2)"},
    "에이펙스 레전드":{"queries": ["Electronic Arts"],                         "label": "EA(에이펙스 레전드)"},
    "이터널리턴":     {"queries": ["Nimble Neuron", "Eternal Return", "이터널리턴"], "label": "Nimble Neuron(이터널리턴)"},
}

TARGET_REGIONS = ["KR", "US", "JP", "TW", "GB", "DE", "BR"]

def crawl_google_ads(competitor, keywords, region="KR"):
    """Google Ads Transparency Center 크롤링 (키워드 fallback 지원)"""
    if isinstance(keywords, str):
        keywords = [keywords]
    results = []
    try:
        from GoogleAds import GoogleAds
        a = GoogleAds(region=region)
        data = None
        for keyword in keywords:
            try:
                suggestions = a.get_all_search_suggestions(keyword)
                print(f"    [DEBUG] {competitor}[{region}] '{keyword}' suggestions={len(suggestions)}건: {str(suggestions)[:200]}")
            except Exception as se:
                print(f"    [DEBUG] {competitor}[{region}] suggestions 오류: {se}")
            data = a.get_creative_Ids(keyword, 20)
            print(f"    [DEBUG] {competitor}[{region}] creative_ids={len(data.get('Creative_Ids',[]) if data else [])}건 ad_count={data.get('Ad Count',0) if data else 0}")
            if data and data.get("Creative_Ids"):
                print(f"    Google {competitor} [{region}]: 키워드='{keyword}' 매칭")
                break
            else:
                print(f"    Google {competitor} [{region}]: '{keyword}' 0건, 다음 키워드 시도")
        if not data or not data.get("Creative_Ids"):
            print(f"    Google {competitor} [{region}]: 모든 키워드 0건")
            return results
        adv_id = data["Advertisor Id"]
        for cid in data["Creative_Ids"][:10]:
            try:
                brief = a.get_breif_ads(adv_id, cid)
                if not brief:
                    continue
                ad_link = brief.get("Ad Link","")
                ad_format = brief.get("Ad Format","")
                last_shown = brief.get("Last Shown","")
                # 최근 90일 이내 광고만 수집
                if last_shown:
                    try:
                        from datetime import date
                        shown_date = date.fromisoformat(last_shown)
                        if (date.today() - shown_date).days > 365:
                            continue
                    except:
                        pass
                # 썸네일: 이미지는 직접 URL, 영상은 투명성 센터 링크
                thumbnail = ad_link if ad_format == "Image" else ""
                results.append({
                    "platform": "Google",
                    "competitor": competitor,
                    "title": f"{data.get('Advertisor',keyword)}",
                    "description": f"형식: {ad_format} | 마지막 노출: {last_shown}",
                    "url": f"https://adstransparency.google.com/advertiser/{adv_id}/creative/{cid}?region={region}",
                    "thumbnail": thumbnail,
                    "published_at": last_shown or None,
                    "ad_type": ad_format,
                    "region": region,
                })
            except Exception as e:
                print(f"    brief 오류 (cid={cid}): {e}")
        print(f"    Google {competitor} [{region}]: {len(results)}건")
    except Exception as e:
        print(f"    Google 오류 ({competitor}, {region}): {e}")
    return results

def crawl_meta_ads(competitor, keyword):
    """Facebook Ads Library 키워드 검색 스크래핑"""
    results = []
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox","--disable-setuid-sandbox","--disable-dev-shm-usage"]
            )
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                locale="ko-KR"
            )
            page = context.new_page()
            try:
                import urllib.parse
                encoded = urllib.parse.quote(keyword)
                url = f"https://www.facebook.com/ads/library/?active_status=all&ad_type=all&country=KR&q={encoded}&search_type=keyword_unordered"
                page.goto(url, timeout=30000, wait_until="networkidle")
                page.wait_for_timeout(8000)
                page.evaluate("window.scrollTo(0, 300)")
                page.wait_for_timeout(3000)
                title = page.title()
                print(f"    페이지 제목: {title}")
                body_text = page.inner_text("body")[:200]
                print(f"    페이지 내용: {body_text}")

                # 광고 카드: aria-label 또는 data 속성 기반으로 안정적 추출
                page.evaluate("window.scrollTo(0, 300)")
                page.wait_for_timeout(2000)

                # 광고 본문 텍스트 추출 (구조 독립적)
                ad_data = page.evaluate("""() => {
                    const ads = [];
                    // 광고 라이브러리는 각 광고가 독립된 div에 렌더링됨
                    const allDivs = document.querySelectorAll('div[role="article"]');
                    allDivs.forEach(div => {
                        const text = div.innerText?.trim();
                        const imgs = div.querySelectorAll('img[src*="fbcdn"]');
                        const thumb = imgs.length > 0 ? imgs[0].src : "";
                        const links = div.querySelectorAll('a[href*="facebook"]');
                        const link = links.length > 0 ? links[0].href : "";
                        if (text && text.length > 10) {
                            ads.push({
                                text: text.substring(0, 300),
                                thumbnail: thumb,
                                url: link
                            });
                        }
                    });
                    return ads;
                }""")

                for ad in ad_data[:20]:
                    title = ad.get("text","").split("\n")[0][:200]
                    if title and len(title) > 5:
                        results.append({
                            "platform": "Meta",
                            "competitor": competitor,
                            "title": title,
                            "description": ad.get("text","")[:500],
                            "url": ad.get("url","") or url,
                            "thumbnail": ad.get("thumbnail",""),
                            "published_at": None,
                            "ad_type": "디스플레이"
                        })
                print(f"    Meta {keyword}: {len(results)}건")
            except Exception as e:
                print(f"    Meta 오류 ({keyword}): {e}")
            browser.close()
    except Exception as e:
        print(f"  Meta 크롤링 오류: {e}")
    return results

def crawl_youtube(competitor,queries):
    print(f"  YouTube: {competitor}")
    for query in queries:
        try:
            params={"part":"snippet","q":query,"type":"video","maxResults":10,"order":"date","key":YOUTUBE_API_KEY,"relevanceLanguage":"ko","regionCode":"KR"}
            resp=requests.get("https://www.googleapis.com/youtube/v3/search",params=params,timeout=10)
            if resp.status_code!=200:continue
            for item in resp.json().get("items",[]):
                vid_id=item.get("id",{}).get("videoId","")
                if not vid_id:continue
                sn=item.get("snippet",{})
                pub=sn.get("publishedAt","")
                try:published_at=datetime.fromisoformat(pub.replace("Z","+00:00")).isoformat()
                except:published_at=None
                save_ad("유튜브",competitor,sn.get("title",""),sn.get("description",""),f"https://www.youtube.com/watch?v={vid_id}",sn.get("thumbnails",{}).get("medium",{}).get("url",""),published_at,"영상")
        except Exception as e:print(f"  YouTube 오류: {e}")
def crawl_naver(competitor,queries):
    print(f"  Naver: {competitor}")
    headers={"X-Naver-Client-Id":NAVER_CLIENT_ID,"X-Naver-Client-Secret":NAVER_CLIENT_SECRET}
    for query in queries:
        for st in ["news","blog"]:
            try:
                resp=requests.get(f"https://openapi.naver.com/v1/search/{st}.json",params={"query":query,"display":20,"sort":"date"},headers=headers,timeout=10)
                if resp.status_code!=200:continue
                for item in resp.json().get("items",[]):
                    title=re.sub('<[^<]+?>','',item.get("title",""))
                    desc=re.sub('<[^<]+?>','',item.get("description",""))
                    url=item.get("link","") or item.get("originallink","")
                    pub=item.get("pubDate","")
                    try:
                        from email.utils import parsedate_to_datetime
                        published_at=parsedate_to_datetime(pub).isoformat() if pub else None
                    except:published_at=None
                    save_ad("네이버",competitor,title,desc,url,"",published_at,"뉴스" if st=="news" else "블로그")
            except Exception as e:print(f"  Naver 오류: {e}")
def crawl():
    print(f"\n광고 크롤링 시작: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    for competitor,info in COMPETITORS.items():
        queries = info["queries"]
        fb_page = info["fb_page"]
        # Google 광고만 수집 (권역별)
        for region in TARGET_REGIONS:
            g = GOOGLE_COMPETITORS.get(competitor, {})
            g_label = g.get("label", competitor)
            g_queries = g.get("queries", [competitor])
            for ad in crawl_google_ads(g_label, g_queries, region=region):
                save_ad(ad['platform'],ad['competitor'],ad['title'],ad['description'],ad['url'],ad['thumbnail'],ad['published_at'],ad['ad_type'],region=ad.get('region',''))
    print("완료")
if __name__=="__main__":crawl()
