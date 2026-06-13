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

# 给四条 10/11 专利直接补 inventors（从 PDF 提取的中文名）
updates = {
    'CN108873942B': '{"边学静","殷玉芹","夏召莲","夏召亮"}',
    'CN109263957A': '{"武明建","曾鑫","吴志林","李忠新"}',
    'CN115292928A': '{"张洪海","费毓晗","任真苹","李博文","刘皞","钟罡"}',
    'CN114987756A': '{"武明建","曾鑫","吴志林","李忠新"}',
}

for pn, inv in updates.items():
    try:
        r = core.db_write.table('patents').update({'inventors':inv}).eq('patent_number',pn).execute()
        print(f'{pn}: OK')
    except Exception as e:
        print(f'{pn}: FAIL {e}')
