"""
CLI wrapper for PatentCrawler - runs without tkinter GUI.
Usage:
  python pyScript/patent_crawler_cli.py --seed URL --max 2000 --export
  python pyScript/patent_crawler_cli.py --seed URL --max 2000 --resume
"""
import os, sys, time, argparse
sys.path.insert(0, os.path.dirname(__file__))
from patent_crawler import PatentCrawler

WORKSPACE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                         "agent-workspace", "data-engineer", "data-schemas")
PROGRESS_FILE = os.path.join(WORKSPACE, "crawler_progress.json")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", required=True)
    parser.add_argument("--max", type=int, default=2000)
    parser.add_argument("--export", action="store_true", default=True)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    crawler = PatentCrawler(gui_callback=None)

    resume_file = PROGRESS_FILE if args.resume else None

    result = crawler.crawl(args.seed, max_visit=args.max, resume_file=resume_file)

    if args.export:
        crawler.export_json()

    print(f"\nFinal: visited={result['visited']} lowalt={result['lowalt']} saved={result['saved']} backlog={result['backlog']}")


if __name__ == "__main__":
    main()
