import os, json, sys, ssl
ssl._create_default_https_context = ssl._create_unverified_context
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PYSCRIPT_DIR = os.path.dirname(_SCRIPT_DIR)
_PROJECT_ROOT = os.path.dirname(_PYSCRIPT_DIR)
os.chdir(_PROJECT_ROOT)
sys.path.insert(0, _PYSCRIPT_DIR)

_DEMO_ITEMS_PATH = os.getenv('DEMO_ITEMS_PATH',
    r'D:\AI大模型应用\Aeroscope\Agent矩阵\demo_items.json')
with open(_DEMO_ITEMS_PATH, 'r', encoding='utf-8') as f:
    source_items = json.load(f)

# 转成 patent_details.json 格式
patents = []
for item in source_items:
    clean = {k: v for k, v in item.items() if k != '_html'}
    clean.pop('created_at', None)
    clean.pop('draft', None)
    clean.pop('country_code', None)
    # LLM 分类字段单独处理
    for llm_field in ['technical_categories','technical_subcategory','industry_chain_sub']:
        clean.pop(llm_field, None)
    patents.append(clean)

data = {"patents": patents}

# 写入
import_dir = os.path.join(_PROJECT_ROOT, 'agent-workspace', 'data-engineer', 'data-schemas')
os.makedirs(import_dir, exist_ok=True)
output_path = os.path.join(import_dir, 'patent_details.json')
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f'Written: {output_path} ({len(patents)} patents)')
