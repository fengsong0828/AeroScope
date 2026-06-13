import os, sys, ssl
ssl._create_default_https_context = ssl._create_unverified_context
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PYSCRIPT_DIR = os.path.dirname(_SCRIPT_DIR)
_PROJECT_ROOT = os.path.dirname(_PYSCRIPT_DIR)
os.chdir(_PROJECT_ROOT)
sys.path.insert(0, _PYSCRIPT_DIR)
from dotenv import load_dotenv; load_dotenv()
from collector_core import CollectorCore
c=CollectorCore()
r=c.db.table('patents').select('patent_number,background_art').eq('patent_number','CN115576186A').execute()
if r.data:
    p=r.data[0]
    bg=p.get('background_art','')
    print(f"CN115576186A: bg={'YES' if bg else 'NO'} ({len(bg or '')} chars)")
else:
    print("NOT FOUND")
