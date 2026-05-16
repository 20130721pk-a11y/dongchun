import os, requests, re
from datetime import datetime, timezone
from supabase import create_client
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")
NAVER_CLIENT_ID = os.environ.get("NAVER_CLIENT_ID", "")
NAVER_CLIENT_SECRET = os.environ.get("NAVER_CLIENT_SECRET", "")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
COMPETITORS = {"포트나이트":["포트나이트 광고","fortnite korea 광고"],"배틀그라운드":["배그 광고","배틀그라운드 광고"],"발로란트":["발로란트 광고","valorant korea 광고"],"이터널리턴":["이터널리턴 광고"],"리그오브레전드":["롤 광고","리그오브레전드 광고"],"오버워치2":["오버워치 광고"],"에이펙스 레전드":["에이펙스 광고"]}
def save_ad(platform,competitor,title,description,url,thumbnail,published_at,ad_type,views=0):
    try:
        supabase.table("competitor_ads").upsert({"platform":platform,"competitor":competitor,"title":title[:500] if title else "","description":description[:1000] if description else "","url":url,"thumbnail":thumbnail,"published_at":published_at,"ad_type":ad_type,"views":views},on_conflict="url").execute()
    except Exception as e:
        print(f"저장 오류: {e}")

def crawl_meta_ads(competitor, search_terms):
    """Facebook Ads Library 스크래핑"""
    results = []
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox","--disable-setuid-sandbox","--disable-dev-shm-usage"]
            )
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="ko-KR"
            )
            page = context.new_page()
            for term in search_terms[:2]:
                try:
                    url = f"https://www.facebook.com/ads/library/?active_status=all&ad_type=all&country=KR&q={term}&search_type=keyword_unordered"
                    page.goto(url, timeout=30000, wait_until="domcontentloaded")
                    page.wait_for_timeout(5000)

                    # 광고 카드 추출
                    cards = page.query_selector_all("div[class*=\"x1lliihq\"]")
                    for card in cards[:15]:
                        try:
                            title = card.inner_text()[:200].strip().split("\n")[0]
                            imgs = card.query_selector_all("img")
                            thumbnail = imgs[0].get_attribute("src") if imgs else ""
                            links = card.query_selector_all("a[href]")
                            ad_url = links[0].get_attribute("href") if links else url
                            if title and len(title) > 5:
                                results.append({
                                    "platform": "Meta",
                                    "competitor": competitor,
                                    "title": title,
                                    "description": "",
                                    "url": ad_url or url,
                                    "thumbnail": thumbnail or "",
                                    "published_at": None,
                                    "ad_type": "디스플레이"
                                })
                        except:
                            pass
                    print(f"    Meta {term}: {len(results)}건")
                except Exception as e:
                    print(f"    Meta 오류 ({term}): {e}")
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
    for competitor,queries in COMPETITORS.items():
        crawl_youtube(competitor,queries)
        crawl_naver(competitor,queries)
        for ad in crawl_meta_ads(competitor, queries[:2]):
            save_ad(ad['platform'],ad['competitor'],ad['title'],ad['description'],ad['url'],ad['thumbnail'],ad['published_at'],ad['ad_type'])
    print("완료")
if __name__=="__main__":crawl()
