"""
CNIPA Patent Search - Session-based access with login support
"""
import requests, re, urllib3, time, json, os
from bs4 import BeautifulSoup

urllib3.disable_warnings()

SESSION_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                            "agent-workspace", "data-engineer", "data-schemas",
                            "cnipa_session.json")


def create_session():
    """Create a requests session that mimics a real browser for CNIPA"""
    sess = requests.Session()
    sess.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
    })
    sess.verify = False
    return sess


def test_access(sess):
    """Test basic access to CNIPA search pages"""
    urls = [
        'https://pss-system.cponline.cnipa.gov.cn/',
        'https://pss-system.cponline.cnipa.gov.cn/conventionalSearch',
    ]
    for url in urls:
        try:
            r = sess.get(url, timeout=30)
            print(f"{r.status_code} {len(r.text):6d}B  {url}")
            if r.status_code == 200:
                # Check title
                title_m = re.search(r'<title>(.*?)</title>', r.text, re.I)
                if title_m:
                    print(f"  Title: {title_m.group(1)}")
                # Check if it has search form
                has_input = 'input' in r.text.lower()
                has_search = 'search' in r.text.lower() or 'query' in r.text.lower()
                print(f"  Has input: {has_input}, Has search: {has_search}")
                # Show cookie count
                print(f"  Cookies: {len(sess.cookies)}")
                for c in sess.cookies:
                    print(f"    {c.name} = {c.value[:30]}...")
        except Exception as e:
            print(f"ERR {url}: {e}")


if __name__ == "__main__":
    sess = create_session()
    print("Testing CNIPA access...\n")
    test_access(sess)
    print("\nDone. If you have login credentials, provide them and I'll add login support.")
