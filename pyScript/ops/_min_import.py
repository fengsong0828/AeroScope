import os, json, ssl, sys
ssl._create_default_https_context = ssl._create_unverified_context
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PYSCRIPT_DIR = os.path.dirname(_SCRIPT_DIR)
_PROJECT_ROOT = os.path.dirname(_PYSCRIPT_DIR)
os.chdir(_PROJECT_ROOT)
sys.path.insert(0, _PYSCRIPT_DIR)
from dotenv import load_dotenv; load_dotenv()

# 直接用 supabase，仅写必要字段
from supabase import create_client
db = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_ANON_KEY'))

# 最小字段集
data = {
    "patent_number": "CN114987756A",
    "title": "一种仿生蜻蜓扑翼飞行器",
    "abstract": "本发明公开了一种仿生蜻蜓扑翼飞行器，包括机身骨架、前后扑翼、传动机构、驱动电机、转向机构、俯仰机构和电源",
    "applicant": "Nanjing University of Science and Technology",
    "inventors": "李忠新",
    "legal_status": "有效",
    "google_url": "https://patents.google.com/patent/CN114987756A/zh",
    "citation_count": 10,
    "draft": False
}

# 仅查，不 import 全库
ex = db.table('patents').select('id').eq('patent_number','CN114987756A').execute()
if ex.data:
    db.table('patents').update(data).eq('patent_number','CN114987756A').execute()
    print("UPDATE OK")
else:
    db.table('patents').insert(data).execute()
    print("INSERT OK")
