import os, ssl, sys
ssl._create_default_https_context = ssl._create_unverified_context
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PYSCRIPT_DIR = os.path.dirname(_SCRIPT_DIR)
_PROJECT_ROOT = os.path.dirname(_PYSCRIPT_DIR)
os.chdir(_PROJECT_ROOT)
sys.path.insert(0, _PYSCRIPT_DIR)
from dotenv import load_dotenv; load_dotenv()

from patent_agent import PatentAgent as PA

agent = PA()
data = {
    "patent_number": "CN114987756A",
    "title": "一种仿生蜻蜓扑翼飞行器",
    "abstract": "本发明公开了一种仿生蜻蜓扑翼飞行器",
    "applicant": "Nanjing University of Science and Technology",
    "inventors": "李忠新",
    "legal_status": "Granted",
    "google_url": "https://patents.google.com/patent/CN114987756A/zh",
    "citation_count": 10,
}
agent.insert_patent(data)
print("DONE")
