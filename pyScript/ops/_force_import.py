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
# 不查重，直接插入
data = {
    "patent_number": "CN114987756A",
    "title": "一种仿生蜻蜓扑翼飞行器",
    "abstract": "本发明公开了一种仿生蜻蜓扑翼飞行器",
    "applicant": "Nanjing University of Science and Technology",
    "google_url": "https://patents.google.com/patent/CN114987756A/zh",
    "draft": False,
}
try:
    core.db_write.table('patents').insert(data).execute()
    print("INSERT OK: CN114987756A")
except Exception as e:
    print(f"FAIL: {e}")
