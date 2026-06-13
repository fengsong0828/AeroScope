import os, ssl, sys
ssl._create_default_https_context = ssl._create_unverified_context
os.environ['SSL_CERT_FILE'] = ''
os.environ['REQUESTS_CA_BUNDLE'] = ''
os.environ['CURL_CA_BUNDLE'] = ''

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PYSCRIPT_DIR = os.path.dirname(_SCRIPT_DIR)
_PROJECT_ROOT = os.path.dirname(_PYSCRIPT_DIR)
os.chdir(_PROJECT_ROOT)
sys.path.insert(0, _PYSCRIPT_DIR)
from dotenv import load_dotenv; load_dotenv()

# 用 supabase REST API 直调（非 supabase-py）
import requests,urllib3; urllib3.disable_warnings()
u=os.getenv('SUPABASE_URL')
k=os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_ANON_KEY')
H={'apikey':k,'Authorization':f'Bearer {k}','Content-Type':'application/json'}
s=requests.Session(); s.verify=False

update = {
    "publication_number": "CN114987756A",
    "application_number": "202210646175.4",
    "application_date": "2022-06-09",
    "publication_date": "2022-09-02",
}
r=s.patch(f'{u}/rest/v1/patents?patent_number=eq.CN114987756A',headers=H,json=update,timeout=30)
print(f"UPDATE: {r.status_code}")

# 验证
r2=s.get(f'{u}/rest/v1/patents?select=patent_number,publication_number,application_number,application_date,publication_date,grant_date,priority_date&patent_number=eq.CN114987756A',headers=H,timeout=30)
if r2.json():
    p=r2.json()[0]
    for k,v in p.items():
        print(f"  {k}: {v}")
