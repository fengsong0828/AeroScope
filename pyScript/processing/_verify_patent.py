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
r = core.db.table('patents').select('patent_number,title,applicant,created_at').eq('patent_number','CN114987756A').execute()
if r.data:
    p = r.data[0]
    print(f"专利号: {p['patent_number']}")
    print(f"标题: {p.get('title','')[:80]}")
    print(f"申请人: {p.get('applicant','')}")
    print(f"创建时间: {p.get('created_at','')}")
else:
    print("NOT IN DB")
