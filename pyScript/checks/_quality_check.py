import os, sys, ssl
ssl._create_default_https_context = ssl._create_unverified_context
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PYSCRIPT_DIR = os.path.dirname(_SCRIPT_DIR)
_PROJECT_ROOT = os.path.dirname(_PYSCRIPT_DIR)
os.chdir(_PROJECT_ROOT)
sys.path.insert(0, _PYSCRIPT_DIR)
from dotenv import load_dotenv; load_dotenv()
from collector_core import CollectorCore
core = CollectorCore()

# 随机取几条最近 enrich 过的
pns = ['CN109263957A','CN115292928A','CN108873942B','CN111433122B']
for pn in pns:
    r = core.db.table('patents').select(
        'patent_number,title,applicant,inventors,claims,background_art,publication_number,publication_date,application_date').eq('patent_number',pn).execute()
    if r.data:
        p = r.data[0]
        claims = p.get('claims','') or ''
        bg = p.get('background_art','') or ''
        inventors = p.get('inventors','') or ''
        print(f'{pn}:')
        print(f'  applicant: {p.get("applicant","")}')
        print(f'  inventors: {inventors}')
        print(f'  pub_num: {p.get("publication_number","")}  pub_date: {p.get("publication_date","")}')
        print(f'  app_date: {p.get("application_date","")}')
        print(f'  claims: {len(claims)}字')
        print(f'  bg: {len(bg)}字')
        # 检查 claims 内容质量
        if claims and len(claims) > 10:
            print(f'  claims前50字: {claims[:50]}')
        if bg and len(bg) > 10:
            print(f'  bg前50字: {bg[:50]}')
        print()
