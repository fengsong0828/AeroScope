import os,json,sys,ssl
ssl._create_default_https_context = ssl._create_unverified_context
os.chdir(r'D:\AI大模型应用\Aeroscope\AeroScope')
sys.path.insert(0, 'pyScript')

# 读取抓到的专利数据
with open(r'D:\AI大模型应用\Aeroscope\Agent矩阵\demo_items.json','r',encoding='utf-8') as f:
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
import_dir = r'D:\AI大模型应用\Aeroscope\AeroScope\agent-workspace\data-engineer\data-schemas'
os.makedirs(import_dir, exist_ok=True)
output_path = os.path.join(import_dir, 'patent_details.json')
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f'Written: {output_path} ({len(patents)} patents)')
