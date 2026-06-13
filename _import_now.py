import os,json,ssl
ssl._create_default_https_context = ssl._create_unverified_context
os.chdir(r'D:\AI大模型应用\Aeroscope\AeroScope')
import sys; sys.path.insert(0, 'pyScript')
from dotenv import load_dotenv; load_dotenv()
from supabase import create_client

db = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_ANON_KEY'))

with open(r'D:\AI大模型应用\Aeroscope\Agent矩阵\demo_items.json','r',encoding='utf-8') as f:
    items = json.load(f)

for item in items:
    for bad in ['_html','created_at','country_code','application_number','technical_categories','technical_subcategory','industry_chain_sub']:
        item.pop(bad, None)
    item['draft'] = False
    pn = item['patent_number']
    try:
        ex = db.table('patents').select('id').eq('patent_number',pn).execute()
        if ex.data:
            db.table('patents').update(item).eq('patent_number',pn).execute()
            print(f"UPDATE: {pn}")
        else:
            db.table('patents').insert(item).execute()
            print(f"INSERT: {pn}")
    except Exception as e:
        print(f"FAIL: {pn} — {str(e)[:100]}")
print('Done')
