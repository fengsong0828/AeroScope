import os, json, ssl, sys
ssl._create_default_https_context = ssl._create_unverified_context
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PYSCRIPT_DIR = os.path.dirname(_SCRIPT_DIR)
_PROJECT_ROOT = os.path.dirname(_PYSCRIPT_DIR)
os.chdir(_PROJECT_ROOT)
sys.path.insert(0, _PYSCRIPT_DIR)
from dotenv import load_dotenv; load_dotenv()
from supabase import create_client

db = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_ANON_KEY'))

_DEMO_ITEMS_PATH = os.getenv('DEMO_ITEMS_PATH',
    r'D:\AI大模型应用\Aeroscope\Agent矩阵\demo_items.json')
with open(_DEMO_ITEMS_PATH, 'r', encoding='utf-8') as f:
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
