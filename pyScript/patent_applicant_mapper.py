"""
AeroScope Patent Applicant Mapper
查询 Supabase companies 表，将 patent_details.json 中的英文申请人名
自动映射为中文名，添加 applicant_cn 字段。

用法:
  python pyScript/patent_applicant_mapper.py
  python pyScript/patent_applicant_mapper.py --export-unmatched  # 导出未匹配的申请人清单
"""
import os
import sys
import re
import json
import time
import argparse
from dotenv import load_dotenv

load_dotenv()

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE = os.path.join(os.path.dirname(os.path.dirname(SCRIPT_DIR)),
                         "agent-workspace", "data-engineer", "data-schemas")
INPUT_FILE = os.path.join(WORKSPACE, "patent_details.json")
UNMATCHED_FILE = os.path.join(WORKSPACE, "unmatched_applicants.json")
LLM_MAP_FILE = os.path.join(WORKSPACE, "applicant_cn_map.json")

# 常见中英对照（硬编码兜底）
FALLBACK_MAP = {
    "Beihang University": "北京航空航天大学",
    "Tsinghua University": "清华大学",
    "Zhejiang University ZJU": "浙江大学",
    "Zhejiang University": "浙江大学",
    "Shanghai Jiao Tong University": "上海交通大学",
    "Xidian University": "西安电子科技大学",
    "Central South University": "中南大学",
    "Jinan University": "暨南大学",
    "Nanchang Hangkong University": "南昌航空大学",
    "Northwestern Polytechnical University": "西北工业大学",
    "Nanjing University of Aeronautics and Astronautics": "南京航空航天大学",
    "Hefei University of Technology": "合肥工业大学",
    "Beijing Institute of Technology BIT": "北京理工大学",
    "Beijing University of Posts and Telecommunications": "北京邮电大学",
    "Nanjing University of Posts and Telecommunications": "南京邮电大学",
    "Nanjing Post and Telecommunication University": "南京邮电大学",
    "South China University of Technology SCUT": "华南理工大学",
    "Wuhan University WHU": "武汉大学",
    "National University of Defense Technology": "国防科技大学",
    "Individual": "个人",
    "SZ DJI Technology Co Ltd": "大疆创新科技有限公司",
    "Shenzhen Dajiang Innovations Technology Co Ltd": "大疆创新科技有限公司",
    "Shenzhen Autel Intelligent Aviation Technology Co Ltd": "道通智能航空技术股份有限公司",
    "Beijing Xiaomi Mobile Software Co Ltd": "北京小米移动软件有限公司",
    "Beijing Jingdong Century Trading Co Ltd": "北京京东世纪贸易有限公司",
    "SF Technology Co Ltd": "顺丰科技有限公司",
    "Rainbow UAV Technology Co Ltd": "彩虹无人机科技有限公司",
    "China Aeronautical Radio Electronics Research Institute": "中国航空无线电电子研究所",
    "Hubei Institute Of Aerospacecraft": "湖北航天飞行器研究所",
    "Xian Aircraft Design and Research Institute of AVIC": "中航工业西安飞机设计研究所",
    "Sichuan Tengdun Technology Co Ltd": "四川腾盾科技有限公司",
    "Zhonglian Deguan Technology Beijing Co ltd": "中联德冠科技(北京)有限公司",
    "Chengdu Dagong Bochuang Information Technology Co ltd": "成都大公博创信息技术有限公司",
    "MAINTENANCE COMPANY QINGHAI ELECTRIC POWER CO LTD": "青海电力公司检修公司",
    "FUZHOU ZHENYUAN TECHNOLOGY DEVELOPMENT CO LTD": "福州振源科技发展有限公司",
    "Electric Power Research Institute of State Grid Shandong Electric Power Co Ltd": "国网山东省电力公司电力科学研究院",
    "Electric Power Research Institute of Guangxi Power Grid Co Ltd": "广西电网有限责任公司电力科学研究院",
    "GUANGZHOU KUAIFEI COMPUTER TECHNOLOGY Co Ltd": "广州快飞计算机科技有限公司",
    "Guangdong Power-Fly Air Technology Development Co Ltd": "广东力飞航空科技发展有限公司",
    "Taizhou Xinagda Fire Service Implement Co ltd": "泰州祥达消防器材有限公司",
    "Southwest University of Science and Technology": "西南科技大学",
    "Xiamen University": "厦门大学",
    "West Anhui University": "皖西学院",
    "Tongji University": "同济大学",
    "Xian Jiaotong University": "西安交通大学",
    "Chinese Aeronautical Est": "中国航空研究院",
    "Lightstar Uav System Co Ltd": "光星无人机系统有限公司",
    "Linoya Electronics Technology Co ltd": "力诺亚电子科技有限公司",
    "Emso Innovation Pte Ltd": "Emso Innovation Pte Ltd",
    "Joby Aviation Inc": "Joby Aviation 公司",
    "TDWB Corp": "TDWB 公司",
    "Farsighted Earthquake Protection Science And Technology Ltd Of Yantai Ke Libo": "烟台科力博远震防护科技有限公司",
    "PowerVision Robot Inc": "臻迪机器人公司",
    "Aircam UAV Technology Corp": "爱尔康无人机科技公司",
    "M Ni Gowers Kobita LLC": "M Ni Gowers Kobita LLC",
    "Kerim Aircraft Co Ltd": "克里姆飞机有限公司",
    "Air Co ltd": "Air 有限公司",
    "Geoby Flight Ltd": "极飞航空有限公司",
    "Nileworks Inc": "Nileworks 公司",
    "Wokoport Ltd": "沃科港有限公司",
    "Dms Corp": "DMS 公司",
}


def clean_name(name):
    """Normalize a name for comparison"""
    if not name:
        return ""
    n = name.lower().strip()
    n = re.sub(r'\(.*?\)', '', n)
    n = re.sub(r'[^\w\s]', '', n)
    n = re.sub(r'\s+', ' ', n).strip()
    return n


def fetch_company_map():
    """从 Supabase 查询 companies 表，构建 name_en -> name 映射"""
    try:
        from supabase import create_client
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_ANON_KEY")
        if not supabase_url or not supabase_key:
            print("[WARN] Supabase credentials not found in .env, using fallback map only")
            return {}
        db = create_client(supabase_url, supabase_key)
        r = db.table("companies").select("name,name_en").execute()
        mapping = {}
        for c in (r.data or []):
            en = (c.get("name_en") or "").strip()
            cn = (c.get("name") or "").strip()
            if en and cn:
                mapping[clean_name(en)] = cn
        print(f"  Fetched {len(mapping)} name_en mappings from DB")
        return mapping
    except Exception as e:
        print(f"  [WARN] DB fetch failed: {e}, using fallback map only")
        return {}


def load_llm_map():
    """Load LLM-generated translation map"""
    if os.path.exists(LLM_MAP_FILE):
        try:
            with open(LLM_MAP_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {}


def match_applicant(applicant, db_map, fallback_map, llm_map):
    """Try to find Chinese name for an English applicant"""
    # 1. Exact match in DB
    key = clean_name(applicant)
    if key in db_map:
        return db_map[key]
    # 2. Exact match in LLM map
    if applicant.strip() in llm_map:
        cn = llm_map[applicant.strip()]
        if cn and cn != applicant.strip():
            return cn
    # 3. Exact match in fallback
    if applicant.strip() in fallback_map:
        return fallback_map[applicant.strip()]
    # 4. Fuzzy: applicant contains a known key
    for fk, fv in fallback_map.items():
        if clean_name(fk) in key or key in clean_name(fk):
            return fv
    # 5. Check if already Chinese
    if any('\u4e00' <= c <= '\u9fff' for c in applicant):
        return applicant
    return ""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--export-unmatched", action="store_true",
                        help="Export unmatched applicants to JSON for manual mapping")
    args = parser.parse_args()

    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Fetch DB mapping
    print("Fetching company names from database...")
    db_map = fetch_company_map()

    # Load LLM-generated map
    llm_map = load_llm_map()
    print(f"  Loaded {len(llm_map)} LLM translations")

    # Build combined fallback (clean keys)
    fallback_clean = {clean_name(k): v for k, v in FALLBACK_MAP.items()}

    # Match each patent
    matched = 0
    unmatched = {}
    total = len(data["patents"])

    for p in data["patents"]:
        applicant = p.get("applicant", "")
        existing_cn = p.get("applicant_cn", "").strip()
        cn_name = match_applicant(applicant, db_map, FALLBACK_MAP, llm_map)
        if cn_name:
            p["applicant_cn"] = cn_name
            matched += 1
        elif existing_cn:
            matched += 1
        else:
            p["applicant_cn"] = ""
            unmatched[applicant] = unmatched.get(applicant, 0) + 1

    # Save updated JSON
    data["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(INPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n{'=' * 50}")
    print(f"  MAPPING COMPLETE")
    print(f"  Total patents: {total}")
    print(f"  Matched: {matched} ({100*matched//total}%)")
    print(f"  Unmatched applicants: {len(unmatched)}")
    print(f"{'=' * 50}")

    # Export unmatched
    if unmatched:
        unmatched_sorted = sorted(unmatched.items(), key=lambda x: -x[1])
        with open(UNMATCHED_FILE, 'w', encoding='utf-8') as f:
            json.dump(dict(unmatched_sorted), f, ensure_ascii=False, indent=2)
        print(f"\nUnmatched applicants exported to: {UNMATCHED_FILE}")
        if not args.export_unmatched:
            print("Top unmatched:")
            for name, count in unmatched_sorted[:20]:
                print(f"  {count:3d}  {name}")
            print(f"\nAdd translations to FALLBACK_MAP in patent_applicant_mapper.py and re-run.")


if __name__ == "__main__":
    main()
