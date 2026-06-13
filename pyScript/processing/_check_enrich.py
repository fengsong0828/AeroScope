import os, ssl, json, sys
ssl._create_default_https_context = ssl._create_unverified_context
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PYSCRIPT_DIR = os.path.dirname(_SCRIPT_DIR)
_PROJECT_ROOT = os.path.dirname(_PYSCRIPT_DIR)
os.chdir(_PROJECT_ROOT)
sys.path.insert(0, _PYSCRIPT_DIR)
from dotenv import load_dotenv; load_dotenv()
from collector_core import CollectorCore
core = CollectorCore()

_INVENTORY_PATH = os.getenv('INVENTORY_PATH',
    r'D:\AI大模型应用\Aeroscope\Agent矩阵\agents\patent\inventory\incomplete.json')
with open(_INVENTORY_PATH, 'r', encoding='utf-8') as f:
    inv = json.load(f)

for pn, rec in sorted(inv.items(), key=lambda x: x[1].get('retries',0))[:5]:
    r = core.db.table('patents').select('patent_number,title,background_art,claims,pdf_url').eq('patent_number',pn).execute()
    if r.data:
        p = r.data[0]
        bg = 'Yes' if p.get('background_art') else 'None'
        cl = 'Yes' if p.get('claims') else 'None'
        pdf = 'Yes' if p.get('pdf_url') else 'None'
        print(f"{pn}: bg={bg} claims={cl} pdf={pdf} retries={rec['retries']} — {p.get('title','')[:50]}")
