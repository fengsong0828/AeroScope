import os,json,ssl
ssl._create_default_https_context = ssl._create_unverified_context
os.chdir(r'D:\AI大模型应用\Aeroscope\AeroScope')
from dotenv import load_dotenv; load_dotenv()
from supabase import create_client
db = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_ANON_KEY'))
r = db.table('patents').select('patent_number,title,applicant,inventors,abstract,legal_status,citation_count,created_at').eq('patent_number','CN114987756A').execute()
if r.data:
    p = r.data[0]
    print(f"专利号: {p['patent_number']}")
    print(f"标题: {p.get('title','')[:80]}")
    print(f"申请人: {p.get('applicant','')}")
    print(f"发明人: {p.get('inventors','')}")
    print(f"法律状态: {p.get('legal_status','')}")
    print(f"引用数: {p.get('citation_count','')}")
    print(f"摘要: {p.get('abstract','')[:100]}")
    print(f"创建时间: {p.get('created_at','')}")
else:
    print("NOT FOUND — 数据库中不存在")
