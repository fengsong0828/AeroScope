"""
AeroScope 企业官网发现 + Logo 补全
对缺 website_url 的企业，用 LLM 搜索官网 → 写入 → 自动抓 Logo

用法:
  python pyScript/logo_fetcher.py --discover     # 先发现官网，再抓 Logo
  python pyScript/logo_fetcher.py --discover --dry-run
"""
import json, time, argparse
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

DISCOVER_PROMPT = """你是一个企业信息查询助手。请根据企业名称，给出其官方网站域名。

要求：
1. 输出严格 JSON 格式：{"name": "企业名", "website": "https://www.example.com"}
2. 如果找不到官网，website 设为空字符串
3. 不要输出任何其他文字"""


class LogoFetcher:
    def __init__(self, dry_run=False):
        from dotenv import load_dotenv; load_dotenv()
        from collector_core import CollectorCore
        self.core = CollectorCore()
        self.dry_run = dry_run

    def discover_websites(self):
        """LLM 发现缺网址企业的官网"""
        r = self.core.db.table('companies').select('id,name,website_url')\
            .eq('draft', False).is_('website_url', 'null').limit(50).execute()
        companies = r.data or []
        if not companies:
            print("没有需要发现网址的企业")
            return 0

        print(f"\nLLM 发现官网: {len(companies)} 家")
        found = 0
        for c in companies:
            name = c['name']
            llm_raw = self.core.call_llm(DISCOVER_PROMPT, name)
            data = self.core.parse_llm_json(llm_raw)
            if data and data.get('website') and data['website'].startswith('http'):
                web = data['website'].strip().rstrip('/')
                print(f"  {name[:20]} -> {web}")
                if not self.dry_run:
                    self.core.db_write.table('companies').update({'website_url': web}).eq('id', c['id']).execute()
                found += 1
            else:
                print(f"  {name[:20]} -> 未找到")
            time.sleep(0.5)

        print(f"  发现 {found}/{len(companies)}")
        return found

    def fetch_logos(self):
        """抓取有网址缺 logo 的企业的 logo"""
        r = self.core.db.table('companies').select('id,name,website_url,logo_url')\
            .eq('draft', False).is_('logo_url', 'null').not_.is_('website_url', 'null').limit(50).execute()
        companies = r.data or []
        if not companies:
            print("没有需要抓取 logo 的企业")
            return 0

        print(f"\n抓取 Logo: {len(companies)} 家")
        import requests as http
        from bs4 import BeautifulSoup
        from urllib.parse import urljoin

        found = 0
        for c in companies:
            web = c.get('website_url', '')
            if not web.startswith('http'):
                continue
            try:
                resp = http.get(web, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15, allow_redirects=True)
                if resp.status_code != 200:
                    continue
                soup = BeautifulSoup(resp.text, 'html.parser')
                # og:image
                og = soup.find('meta', property='og:image')
                if og and og.get('content'):
                    logo = urljoin(web, og['content'])
                else:
                    apple = soup.find('link', rel='apple-touch-icon')
                    if apple and apple.get('href'):
                        logo = urljoin(web, apple['href'])
                    else:
                        imgs = soup.find_all('img')
                        logo = None
                        for img in imgs:
                            cls = ' '.join(img.get('class', [])).lower()
                            if 'logo' in cls:
                                logo = urljoin(web, img.get('src', ''))
                                break
                        if not logo and imgs:
                            logo = urljoin(web, imgs[0].get('src', ''))

                if logo:
                    print(f"  {c['name'][:20]} -> {logo[:60]}")
                    if not self.dry_run:
                        self.core.db_write.table('companies').update({'logo_url': logo}).eq('id', c['id']).execute()
                    found += 1
            except:
                pass
            time.sleep(0.5)

        print(f"  抓取 {found}/{len(companies)}")
        return found


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument('--discover', action='store_true', help='先用LLM发现缺网址企业的官网')
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--company', type=str)
    a = p.parse_args()
    f = LogoFetcher(dry_run=a.dry_run)

    if a.discover:
        f.discover_websites()
    f.fetch_logos()
