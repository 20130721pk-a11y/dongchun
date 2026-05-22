import os, json, base64, requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"}
results = {}

# ── 1. 인벤 (requests) ──────────────────────────────────────
print("=== 인벤 ===")
try:
    url = "https://www.inven.co.kr/search/community/all/%ED%8F%AC%ED%8A%B8%EB%82%98%EC%9D%B4%ED%8A%B8"
    r = requests.get(url, headers=HEADERS, timeout=10)
    soup = BeautifulSoup(r.text, 'html.parser')
    # 어떤 a 태그가 있는지
    inven_links = [a.get('href','') for a in soup.find_all('a', href=True) if 'inven.co.kr' in a.get('href','')][:10]
    board_links = [l for l in inven_links if any(x in l for x in ['/board/','/article/','/news/','/webzine/'])]
    results['inven'] = {
        'status': r.status_code,
        'total_inven_links': len(inven_links),
        'board_links': board_links[:5],
        'html_sample': r.text[:500],
        'title': soup.title.string if soup.title else 'NO TITLE'
    }
    print(f"status={r.status_code}, inven_links={len(inven_links)}, board_links={len(board_links)}")
except Exception as e:
    results['inven'] = {'error': str(e)}
    print(f"ERROR: {e}")

# ── 2. 루리웹 (Playwright) ──────────────────────────────────
print("\n=== 루리웹 ===")
try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox","--disable-setuid-sandbox"])
        page = browser.new_page(user_agent=HEADERS['User-Agent'])
        page.goto("https://bbs.ruliweb.com/search?q=%ED%8F%AC%ED%8A%B8%EB%82%98%EC%9D%B4%ED%8A%B8&searchType=subject&orderType=latest", timeout=20000, wait_until="domcontentloaded")
        page.wait_for_timeout(1500)
        html = page.content()
        browser.close()
    soup = BeautifulSoup(html, 'html.parser')
    tr_items = soup.select('tr.item')
    board_rows = soup.select('.board_list_table tbody tr')
    any_tr = soup.find_all('tr')[:5]
    results['ruliweb'] = {
        'tr_item_count': len(tr_items),
        'board_rows_count': len(board_rows),
        'total_tr': len(soup.find_all('tr')),
        'title': soup.title.string if soup.title else 'NO TITLE',
        'html_sample': html[:800],
        'sample_tr_classes': [str(tr.get('class','')) for tr in soup.find_all('tr')[:8]]
    }
    print(f"tr.item={len(tr_items)}, board_rows={len(board_rows)}, total_tr={len(soup.find_all('tr'))}")
    print(f"title={soup.title.string if soup.title else 'NO TITLE'}")
except Exception as e:
    results['ruliweb'] = {'error': str(e)}
    print(f"ERROR: {e}")

# ── 3. 아카라이브 (Playwright) ──────────────────────────────
print("\n=== 아카라이브 ===")
try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox","--disable-setuid-sandbox"])
        page = browser.new_page(user_agent=HEADERS['User-Agent'])
        # 전용 채널
        page.goto("https://arca.live/b/valorant", timeout=20000, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        html = page.content()
        browser.close()
    soup = BeautifulSoup(html, 'html.parser')
    vrow_column = soup.select('a.vrow.column:not(.notice)')
    vrow_any = soup.select('a.vrow')
    all_a = soup.find_all('a', href=True)
    results['arcalive'] = {
        'vrow_column_count': len(vrow_column),
        'vrow_any_count': len(vrow_any),
        'total_a': len(all_a),
        'title': soup.title.string if soup.title else 'NO TITLE',
        'html_sample': html[:800],
        'sample_a_classes': [str(a.get('class','')) for a in all_a[:10]]
    }
    print(f"a.vrow.column={len(vrow_column)}, a.vrow={len(vrow_any)}, total_a={len(all_a)}")
    print(f"title={soup.title.string if soup.title else 'NO TITLE'}")
except Exception as e:
    results['arcalive'] = {'error': str(e)}
    print(f"ERROR: {e}")

# ── 4. 에펨코리아 (Playwright) ───────────────────────────────
print("\n=== 에펨코리아 ===")
try:
    from playwright.sync_api import sync_playwright
    import re
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox","--disable-setuid-sandbox"])
        page = browser.new_page(user_agent=HEADERS['User-Agent'])
        page.goto("https://www.fmkorea.com/valorant", timeout=20000, wait_until="domcontentloaded")
        page.wait_for_timeout(1500)
        html = page.content()
        browser.close()
    soup = BeautifulSoup(html, 'html.parser')
    digit_links = [a.get('href','') for a in soup.find_all('a', href=True) if re.match(r'^/[0-9]{8,}$', a.get('href',''))]
    all_hrefs = [a.get('href','') for a in soup.find_all('a', href=True)][:20]
    results['fmkorea'] = {
        'digit_links_count': len(digit_links),
        'digit_links_sample': digit_links[:5],
        'all_hrefs_sample': all_hrefs[:10],
        'title': soup.title.string if soup.title else 'NO TITLE',
        'html_sample': html[:800]
    }
    print(f"digit_links={len(digit_links)}")
    print(f"title={soup.title.string if soup.title else 'NO TITLE'}")
    print(f"sample hrefs: {all_hrefs[:5]}")
except Exception as e:
    results['fmkorea'] = {'error': str(e)}
    print(f"ERROR: {e}")

# 결과 저장
with open('debug_result.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

# GitHub API로 커밋
token = os.environ.get("GH_TOKEN","")
if token:
    content_str = json.dumps(results, ensure_ascii=False, indent=2)
    encoded = base64.b64encode(content_str.encode()).decode()
    hdrs = {"Authorization": f"token {token}", "Content-Type": "application/json"}
    r2 = requests.get("https://api.github.com/repos/20130721pk-a11y/dongchun/contents/debug_result.json", headers=hdrs)
    sha = r2.json().get("sha","")
    body = {"message":"debug: crawler HTML dump","content":encoded}
    if sha: body["sha"] = sha
    resp = requests.put("https://api.github.com/repos/20130721pk-a11y/dongchun/contents/debug_result.json", headers=hdrs, json=body)
    print(f"\n결과 커밋: {resp.status_code}")
print("완료")
