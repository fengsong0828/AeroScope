import os,ssl
ssl._create_default_https_context = ssl._create_unverified_context
os.chdir(r'D:\AI大模型应用\Aeroscope\AeroScope')
import sys; sys.path.insert(0, 'pyScript')
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
