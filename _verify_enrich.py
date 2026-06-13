import os,ssl
ssl._create_default_https_context = ssl._create_unverified_context
os.chdir(r'D:\AI大模型应用\Aeroscope\AeroScope')
import sys; sys.path.insert(0,'pyScript')
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
