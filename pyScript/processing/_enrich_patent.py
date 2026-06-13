import os, ssl, re, sys
ssl._create_default_https_context = ssl._create_unverified_context
os.environ['SSL_CERT_FILE'] = ''
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PYSCRIPT_DIR = os.path.dirname(_SCRIPT_DIR)
_PROJECT_ROOT = os.path.dirname(_PYSCRIPT_DIR)
os.chdir(_PROJECT_ROOT)
sys.path.insert(0, _PYSCRIPT_DIR)
from dotenv import load_dotenv; load_dotenv()

import requests,urllib3; urllib3.disable_warnings()
u=os.getenv('SUPABASE_URL'); k=os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_ANON_KEY')
H={'apikey':k,'Authorization':f'Bearer {k}','Content-Type':'application/json'}
s=requests.Session(); s.verify=False

# 下载 PDF + 提取文本
resp = s.get('https://patentimages.storage.googleapis.com/eb/32/f5/4ae6fdbdf5a090/CN114987756A.pdf',
             headers={'User-Agent':'Mozilla/5.0'}, timeout=60)
from PyPDF2 import PdfReader
from io import BytesIO
reader = PdfReader(BytesIO(resp.content))
text = ''
for page in reader.pages:
    text += (page.extract_text() or '') + '\n'

# ─── 摘要: (57) → 权利要求书 ───
m = re.search(r'\(57\)[^\n]*\n(.+?)(?=权利要求书)', text, re.DOTALL)
abstract = re.sub(r'\s+', '', m.group(1).strip()) if m else ''

# ─── 权利要求: 1.一 → 权　利　要　求　书 ───
m2 = re.search(r'(1\.\s*[\u4e00-\u9fff][\s\S]+?)(?=权\s*利\s*要\s*求\s*书\s*\d)', text)
claims = m2.group(1)[:8000] if m2 else ''

# ─── 背景技术: 背景技术 → 发明内容/附图说明 ───
m3 = re.search(r'背景技术\s*\n(.+?)(?=\n\s*(?:发明内容|附图说明|具体实施方式))', text, re.DOTALL)
background = m3.group(1).strip()[:3000] if m3 else ''

print(f"摘要: {len(abstract)} 字")
print(f"权利要求: {len(claims)} 字")
print(f"背景技术: {len(background)} 字")

# 更新 DB
update = {
    "abstract": abstract,
    "claims": claims,
    "background_art": background,
}
r = s.patch(f'{u}/rest/v1/patents?patent_number=eq.CN114987756A', headers=H, json=update, timeout=30)
print(f"DB: {r.status_code}")

# 验证
r2 = s.get(f'{u}/rest/v1/patents?select=abstract,claims,background_art&patent_number=eq.CN114987756A', headers=H, timeout=30)
if r2.json():
    p = r2.json()[0]
    print(f"\n摘要({len(p.get('abstract',''))}字): {p.get('abstract','')[:120]}...")
    print(f"权利要求({len(p.get('claims',''))}字)")
    print(f"背景技术({len(p.get('background_art',''))}字): {p.get('background_art','')[:120]}...")
