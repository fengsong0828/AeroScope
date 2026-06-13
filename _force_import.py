import os,ssl
ssl._create_default_https_context = ssl._create_unverified_context
os.chdir(r'D:\AI大模型应用\Aeroscope\AeroScope')
import sys; sys.path.insert(0,'pyScript')
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
