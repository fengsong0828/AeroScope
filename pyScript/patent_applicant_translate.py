"""
Batch translate unmatched English applicant names to Chinese using LLM.
Reads unmatched_applicants.json, calls LLM, outputs applicant_cn_map.json
"""
import os
import sys
import json
from dotenv import load_dotenv

load_dotenv()

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE = os.path.join(os.path.dirname(os.path.dirname(SCRIPT_DIR)),
                         "agent-workspace", "data-engineer", "data-schemas")
UNMATCHED_FILE = os.path.join(WORKSPACE, "unmatched_applicants.json")
OUTPUT_MAP = os.path.join(WORKSPACE, "applicant_cn_map.json")


def translate_batch(names, api_key, base_url, model):
    """Call LLM to translate a batch of English names to Chinese"""
    import requests
    
    prompt = """You are a Chinese-English company/org name translator specializing in patent applicants.
Translate each English company/university/institute name below to its Chinese official name.
Rules:
- University: translate to official Chinese name (e.g. "Peking University" -> "北京大学")
- Company: translate to official Chinese company name (e.g. "Huawei Technologies Co Ltd" -> "华为技术有限公司")  
- Institute: translate to Chinese (e.g. "Institute of Automation of CAS" -> "中国科学院自动化研究所")
- Individual / person names: keep as-is
- Output ONLY a valid JSON object like {"English Name": "中文名", ...}
- If unsure, return the original English name as value

Names to translate:
""" + json.dumps(names, ensure_ascii=False, indent=2)

    resp = requests.post(
        f"{base_url}/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens": 16000
        },
        timeout=180
    )
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]
    
    # Extract JSON from response
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r'^```\w*\n?', '', content)
        content = re.sub(r'\n?```$', '', content)
    
    import re
    return json.loads(content)


def main():
    import re
    
    api_key = os.getenv("LLM_API_KEY")
    base_url = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
    model = os.getenv("LLM_MODEL", "deepseek-chat")

    if not api_key:
        print("[ERROR] LLM_API_KEY not found in .env")
        sys.exit(1)

    with open(UNMATCHED_FILE, 'r', encoding='utf-8') as f:
        unmatched = json.load(f)

    # Load existing translations to avoid overwriting
    existing_translations = {}
    if os.path.exists(OUTPUT_MAP):
        try:
            with open(OUTPUT_MAP, 'r', encoding='utf-8') as f:
                existing_translations = json.load(f)
        except:
            pass

    names = list(unmatched.keys())
    total = len(names)
    print(f"Total unmatched: {total}")

    # Split into batches of 80 to stay within token limits
    BATCH_SIZE = 80
    all_translations = dict(existing_translations) 

    for i in range(0, total, BATCH_SIZE):
        batch = names[i:i + BATCH_SIZE]
        print(f"Translating batch {i//BATCH_SIZE + 1}/{(total + BATCH_SIZE - 1)//BATCH_SIZE} ({len(batch)} names)...")
        try:
            result = translate_batch(batch, api_key, base_url, model)
            all_translations.update(result)
            print(f"  -> Got {len(result)} translations")
        except Exception as e:
            print(f"  [ERROR] {e}")
            # Save progress so far
            break

    print(f"\nTotal translated: {len(all_translations)}/{total}")

    with open(OUTPUT_MAP, 'w', encoding='utf-8') as f:
        json.dump(all_translations, f, ensure_ascii=False, indent=2)
    print(f"Saved to: {OUTPUT_MAP}")


if __name__ == "__main__":
    main()
