"""
AeroScope 专利PDF自动采集 + OSS上传 + 数据库回写
用法:
  python pyScript/patent_pdf_collector.py CN118280168A
  python pyScript/patent_pdf_collector.py --batch      # 批量处理DB中所有无PDF的专利
"""
import os, sys, re, time, argparse
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
os.chdir(SCRIPT_DIR)

from dotenv import load_dotenv; load_dotenv()
from supabase import create_client
import requests
from bs4 import BeautifulSoup
import oss2

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
}

GOOGLE_PATENTS = "https://patents.google.com/patent/{}/zh"
PDF_URL_PATTERN = re.compile(r"\.pdf$")


def init_db():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")
    return create_client(url, key)


def init_oss():
    auth = oss2.Auth(
        os.getenv("ALIBABA_ACCESS_KEY_ID"),
        os.getenv("ALIBABA_ACCESS_KEY_SECRET")
    )
    bucket = oss2.Bucket(auth, os.getenv("OSS_ENDPOINT"), os.getenv("OSS_PRIVATE_BUCKET"))
    return bucket


def find_pdf_url(patent_number):
    try:
        resp = requests.get(GOOGLE_PATENTS.format(patent_number), headers=HEADERS, timeout=20)
        if resp.status_code != 200:
            print(f"  HTTP {resp.status_code} for {patent_number}")
            return None
        soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.find_all("a", href=PDF_URL_PATTERN):
            href = a.get("href", "")
            if "patentimages.storage.googleapis.com" in href:
                return href
        for meta in soup.find_all("meta"):
            content = meta.get("content", "")
            if "patentimages.storage.googleapis.com" in content and content.endswith(".pdf"):
                return content
        return None
    except Exception as e:
        print(f"  Error finding PDF for {patent_number}: {e}")
        return None


def download_and_upload(patent_number, pdf_url, bucket, db, dry_run=False):
    """下载PDF并直接上传OSS，全程内存操作，不产生本地文件"""
    try:
        # 1. 下载到内存
        resp = requests.get(pdf_url, headers=HEADERS, timeout=60)
        if resp.status_code != 200 or len(resp.content) < 1000:
            print(f"  Download failed: HTTP {resp.status_code}, size {len(resp.content)}")
            return False
        pdf_bytes = resp.content
        size_kb = len(pdf_bytes) / 1024
        print(f"  Downloaded: {size_kb:.0f} KB (in memory)")

        if dry_run:
            print(f"  [DRY RUN] would upload and update DB")
            return True

        # 2. 直接上传到OSS（内存 → OSS，不写磁盘）
        oss_path = f"patents/{patent_number}.pdf"
        bucket.put_object(oss_path, pdf_bytes, headers={
            "Content-Type": "application/pdf",
            "Content-Disposition": "inline"
        })
        oss_url = bucket.sign_url("GET", oss_path, 86400 * 365)
        print(f"  Uploaded to OSS: {oss_path}")

        # 3. 更新DB（相对路径，适配任意部署环境）
        proxy_url = f"/pdf/{oss_path}"
        db.table("patents").update({
            "pdf_url": proxy_url,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("patent_number", patent_number).execute()
        print(f"  DB updated: {patent_number}")
        return True
    except Exception as e:
        print(f"  Error: {e}")
        return False


def process_patent(patent_number, db, bucket, dry_run=False):
    print(f"\n{'='*50}")
    print(f"  Processing: {patent_number}")
    
    # Check existing
    existing = db.table("patents").select("pdf_url").eq("patent_number", patent_number).execute()
    if existing.data and existing.data[0].get("pdf_url"):
        print(f"  SKIP: already has pdf_url")
        return True
    
    # Find PDF URL
    pdf_url = find_pdf_url(patent_number)
    if not pdf_url:
        print(f"  No PDF found on Google Patents")
        return False
    
    print(f"  PDF URL: {pdf_url[:80]}...")
    
    return download_and_upload(patent_number, pdf_url, bucket, db, dry_run)


def main():
    parser = argparse.ArgumentParser(description="AeroScope Patent PDF Collector")
    parser.add_argument("patent_number", nargs="?", help="Single patent number to process")
    parser.add_argument("--batch", action="store_true", help="Batch process all patents missing PDF")
    parser.add_argument("--max", type=int, default=0, help="Max patents to process in batch mode")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    db = init_db()
    bucket = init_oss()

    if args.patent_number:
        process_patent(args.patent_number, db, bucket, args.dry_run)

    elif args.batch:
        # Find patents without pdf_url but with google_url
        query = db.table("patents").select("patent_number,google_url") \
            .is_("pdf_url", "null") \
            .not_.is_("google_url", "null") \
            .order("application_date", desc=True)
        
        if args.max > 0:
            query = query.limit(args.max)
        
        result = query.execute()
        patents = result.data
        
        print(f"\nFound {len(patents)} patents without PDF")
        
        success = 0
        for i, p in enumerate(patents):
            pn = p["patent_number"]
            print(f"\n[{i+1}/{len(patents)}]")
            if process_patent(pn, db, bucket, args.dry_run):
                success += 1
            print(f"  Progress: {success}/{i+1} ok")
            time.sleep(2)  # Rate limit
            
        print(f"\n{'='*60}")
        print(f"  BATCH COMPLETE: {success}/{len(patents)} ok")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
