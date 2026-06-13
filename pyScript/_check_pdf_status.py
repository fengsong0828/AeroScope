"""检查哪些专利经过了 PDF 提取，哪些仅来自 Google Patents 网页"""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv; load_dotenv()
from collector_core import CollectorCore

core = CollectorCore()

def has_chinese(s):
    return bool(re.search(r'[\u4e00-\u9fff]', s or ""))

total = 0
pdf_extracted = 0   # pdf_url 不为空（PDF 已下载到 OSS）
has_cn_name = 0     # applicant 含中文（可能被 PDF 覆盖过）
has_claims = 0      # claims 不为空（必须是 PDF 提取）
has_bg = 0          # background_art 不为空
google_only = 0     # 纯 Google 抓取、无 PDF 痕迹

offset, batch = 0, 500
while True:
    r = core.db.table("patents").select(
        "applicant,claims,background_art,pdf_url,patent_number"
    ).order("id").range(offset, offset + batch - 1).execute()
    if not r.data:
        break
    for p in r.data:
        total += 1
        applicant = p.get("applicant") or ""
        claims = p.get("claims") or ""
        bg = p.get("background_art") or ""
        pdf = p.get("pdf_url") or ""

        if pdf:
            pdf_extracted += 1
        if has_chinese(applicant):
            has_cn_name += 1
        if claims.strip():
            has_claims += 1
        if bg.strip():
            has_bg += 1
        if not has_chinese(applicant) and not claims and not bg:
            google_only += 1

    offset += batch
    if len(r.data) < batch:
        break

print("=" * 50)
print(f"总专利数:               {total}")
print(f"已下载 PDF (pdf_url有值): {pdf_extracted}")
print(f"申请人含中文:           {has_cn_name}")
print(f"有权利要求 (claims):    {has_claims}")
print(f"有背景技术 (bg_art):    {has_bg}")
print(f"纯 Google 抓取无 PDF:   {google_only}")
