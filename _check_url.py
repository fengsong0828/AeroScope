import os,ssl,json
ssl._create_default_https_context=ssl._create_unverified_context
os.chdir(r'D:\AI大模型应用\Aeroscope\AeroScope')
import sys; sys.path.insert(0,'pyScript')
from dotenv import load_dotenv; load_dotenv()
from collector_core import CollectorCore
core = CollectorCore()

with open(r'D:\AI大模型应用\Aeroscope\Agent矩阵\agents\patent\inventory\incomplete.json','r',encoding='utf-8') as f:
    inv = json.load(f)

total = len(inv)
has_url = sum(1 for rec in inv.values() if rec.get('google_url'))
no_url = total - has_url
print(f'Incomplete: {total}')
print(f'Has google_url in inventory: {has_url}')
print(f'No google_url in inventory: {no_url}')

# 抽查 DB 中是否有 google_url
no_url_sample = [pn for pn, rec in inv.items() if not rec.get('google_url')][:5]
print(f'\nSample without url (inventory): {no_url_sample}')
for pn in no_url_sample[:3]:
    try:
        r = core.db.table('patents').select('patent_number,google_url').eq('patent_number',pn).execute()
        if r.data:
            db_url = r.data[0].get('google_url','')
            print(f'{pn}: DB has url = {bool(db_url)} ({str(db_url)[:80]})')
    except:
        print(f'{pn}: DB query failed')
