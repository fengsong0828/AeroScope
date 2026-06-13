import json,os,ssl
ssl._create_default_https_context = ssl._create_unverified_context
os.chdir(r'D:\AI大模型应用\Aeroscope\AeroScope')
import sys; sys.path.insert(0,'pyScript')
from dotenv import load_dotenv; load_dotenv()
from collector_core import CollectorCore
core = CollectorCore()

# 查刚才 enrich 过的几条专利，看实际字段
pns = ['CN108873942B','CN109263957A','CN115292928A','CN114987756A']
for pn in pns:
    r = core.db.table('patents').select(
        'patent_number,title,abstract,applicant,inventors,claims,background_art,pdf_url,publication_number,publication_date,application_number,application_date').eq('patent_number',pn).execute()
    if r.data:
        p = r.data[0]
        present = []
        missing = []
        for f in ['title','abstract','applicant','inventors','publication_number','publication_date','application_number','application_date','claims','background_art','pdf_url']:
            val = p.get(f)
            if val and (isinstance(val,str) and len(val.strip()) > 3):
                present.append(f)
            else:
                missing.append(f)
        score = len(present)
        print(f'\n{pn}: {score}/11 fields')
        print(f'  有: {present}')
        print(f'  缺: {missing}')
