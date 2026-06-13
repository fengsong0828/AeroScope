"""
PDF 批量提取 (71) 申请人 → 回写 patents.applicant
=================================================
处理范围: applicant 非纯中文的专利 (纯英文/中英夹杂)
来源: OSS 私有桶 patents/{pn}.pdf
目标: 提取 PDF 中的正式中文申请人名称，替换 DB 中的英文/混合名
进度: 每 50 条保存断点，中断后可续跑
"""
import sys, os, re, json, time
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv; load_dotenv()
from collector_core import CollectorCore
import oss2
from io import BytesIO
from PyPDF2 import PdfReader

core = CollectorCore()

OSS_KEY = os.getenv("ALIBABA_ACCESS_KEY_ID")
OSS_SECRET = os.getenv("ALIBABA_ACCESS_KEY_SECRET")
OSS_ENDPOINT = os.getenv("OSS_ENDPOINT")
OSS_BUCKET = os.getenv("OSS_PRIVATE_BUCKET")
PROGRESS_FILE = os.path.join(os.path.dirname(__file__), "_pdf_extract_progress.json")

# ─── 工具: 从 PDF 首页提取 (71) 申请人 ───
def extract_applicant_from_pdf(pdf_bytes: bytes) -> str:
    """返回 PDF 中 (71) 申请人的中文名，失败返回空字符串"""
    try:
        reader = PdfReader(BytesIO(pdf_bytes))
        # 扫描前 3 页 (首页 + 摘要页)
        text = ""
        for i in range(min(3, len(reader.pages))):
            text += (reader.pages[i].extract_text() or "") + "\n"

        if not text.strip():
            return ""

        # 策略 1: 标准格式 (71) 申请人
        #   (71)申请人 XXX公司
        #   (71) 申请人 XXX
        for pat in [
            r'\(71\)\s*申\s*请\s*人\s*[：:\s]*([^\n]{4,80})',
            r'\(71\)\s*申\s*请\s*人[：:\s]*\n?\s*([^\n]{4,80})',
            r'申\s*请\s*人\s*[：:]\s*([^\n]{4,80})',
            r'专利权人\s*[：:]\s*([^\n]{4,80})',
        ]:
            m = re.search(pat, text[:4000])
            if m:
                name = m.group(1).strip()
                # 去除多余标点和空格
                name = re.sub(r'[\,，。；;]+.*$', '', name)
                name = re.sub(r'\s+', '', name)
                if len(name) >= 4:
                    return name

        # 策略 2: 英文格式 (71) Applicant → 保留英文，后续 LLM 翻译
        for pat in [
            r'\(71\)\s*Applicant\s*[：:\s]*([^\n]{4,120})',
            r'\(71\)\s*Applicant[：:\s]*\n?\s*([^\n]{4,120})',
            r'Applicant\s*[：:]\s*([^\n]{4,120})',
        ]:
            m = re.search(pat, text[:4000])
            if m:
                name = m.group(1).strip()
                name = re.sub(r'[\,，。；;]+.*$', '', name)
                if len(name) >= 4:
                    return name

        return ""
    except Exception as e:
        return ""


def has_chinese(s):
    return bool(re.search(r'[\u4e00-\u9fff]', s or ""))


def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"done_ids": [], "failed_ids": [], "skip_no_pdf": [], "skip_no_text": []}


def save_progress(p):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(p, f, ensure_ascii=False, indent=2)


# ─── 主流程 ───
def main():
    if not all([OSS_KEY, OSS_SECRET, OSS_ENDPOINT, OSS_BUCKET]):
        print("ERROR: OSS 环境变量缺失 (ALIBABA_ACCESS_KEY_ID/SECRET/OSS_ENDPOINT/OSS_PRIVATE_BUCKET)")
        return

    auth = oss2.Auth(OSS_KEY, OSS_SECRET)
    bucket = oss2.Bucket(auth, OSS_ENDPOINT, OSS_BUCKET)

    progress = load_progress()
    done_set = set(progress["done_ids"])
    failed_set = set(progress["failed_ids"])

    print(f"OSS Bucket: {OSS_BUCKET}")
    print(f"已处理: {len(done_set)}  已失败: {len(failed_set)}")

    # 1. 查询需要处理的专利
    print("\n查询待处理专利...")
    targets = []
    offset, batch = 0, 500
    while True:
        r = core.db.table("patents").select(
            "id,applicant,patent_number,pdf_url"
        ).order("id").range(offset, offset + batch - 1).execute()
        if not r.data:
            break
        for p in r.data:
            pid = p["id"]
            if pid in done_set or pid in failed_set:
                continue
            app = (p.get("applicant") or "").strip()
            if has_chinese(app):
                continue  # 已中文，跳过
            if not p.get("pdf_url"):
                progress["skip_no_pdf"].append(pid)
                continue
            targets.append({
                "id": pid,
                "pn": p.get("patent_number", ""),
                "old_applicant": app,
            })
        offset += batch
        if len(r.data) < batch:
            break

    print(f"待处理: {len(targets)} 条")
    if not targets:
        print("全部已完成!")
        return

    # 2. 逐个处理
    total = len(targets)
    updated = 0
    failed = 0
    t_start = time.time()

    for idx, t in enumerate(targets):
        pid = t["id"]
        pn = t["pn"]
        old = t["old_applicant"]

        try:
            # 从 OSS 下载 PDF
            obj = bucket.get_object(f"patents/{pn}.pdf")
            pdf_bytes = obj.read()

            applicant_cn = extract_applicant_from_pdf(pdf_bytes)

            if applicant_cn:
                # 写入 DB
                core.db_write.table("patents").update({
                    "applicant": applicant_cn
                }).eq("id", pid).execute()
                updated += 1
                done_set.add(pid)
                status = f"✓ → [{applicant_cn[:40]}]"
            else:
                failed += 1
                failed_set.add(pid)
                status = f"✗ 未提取到(71)申请人 [原: {old[:40]}]"

        except oss2.exceptions.NoSuchKey:
            failed += 1
            failed_set.add(pid)
            status = f"✗ OSS文件不存在 {pn}.pdf"
        except Exception as e:
            failed += 1
            failed_set.add(pid)
            status = f"✗ {str(e)[:50]}"

        # 进度输出
        elapsed = time.time() - t_start
        speed = (idx + 1) / elapsed if elapsed > 0 else 0
        eta = (total - idx - 1) / speed if speed > 0 else 0
        eta_min = int(eta // 60)
        eta_sec = int(eta % 60)
        print(f"  [{idx+1}/{total}] {status} | {speed:.1f}条/s | 还需 {eta_min}m{eta_sec}s")

        # 每 50 条存盘
        if (idx + 1) % 50 == 0:
            progress["done_ids"] = sorted(list(done_set))
            progress["failed_ids"] = sorted(list(failed_set))
            save_progress(progress)

    # 3. 最终保存
    progress["done_ids"] = sorted(list(done_set))
    progress["failed_ids"] = sorted(list(failed_set))
    save_progress(progress)

    print(f"\n{'='*50}")
    print(f"  完成! 更新 {updated} 条, 失败 {failed} 条")
    print(f"  进度文件: {PROGRESS_FILE}")


if __name__ == "__main__":
    main()
