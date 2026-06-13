import os,ssl; ssl._create_default_https_context=ssl._create_unverified_context
os.chdir(r'D:\AI大模型应用\Aeroscope\AeroScope')
import sys; sys.path.insert(0,'pyScript')
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
