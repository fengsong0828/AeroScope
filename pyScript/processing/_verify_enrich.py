import os, ssl, sys
ssl._create_default_https_context = ssl._create_unverified_context
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PYSCRIPT_DIR = os.path.dirname(_SCRIPT_DIR)
_PROJECT_ROOT = os.path.dirname(_PYSCRIPT_DIR)
os.chdir(_PROJECT_ROOT)
sys.path.insert(0, _PYSCRIPT_DIR)
from dotenv import load_dotenv; load_dotenv()
from collector_core import CollectorCore
core = CollectorCore()
r = core.db.table('patents').select('patent_number,title,background_art,claims').eq('patent_number','CN109263957A').execute()
if r.data:
    p = r.data[0]
    print(f"Patent: {p['patent_number']}")
    print(f"Title: {p.get('title','')[:80]}")
    print(f"background_art: {type(p.get('background_art')).__name__} — {str(p.get('background_art',''))[:100]}")
    print(f"claims: {'yes' if p.get('claims') else 'no'} {len(p.get('claims','') or '')}")
    print(f"pdf_url: {str(p.get('pdf_url',''))[:80]}")
else:
    print("NOT FOUND")
