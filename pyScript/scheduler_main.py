"""
AeroScope 数据采集调度器
定时执行全量数据采集任务，支持阿里云 FC 环境
"""
import os
import sys
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("scheduler")


def run_all_collectors():
    """执行全部采集任务"""
    results = {}
    start_time = datetime.now()
    logger.info("=" * 50)
    logger.info("AeroScope 数据采集任务开始")
    logger.info(f"启动时间: {start_time.isoformat()}")

    # 1. 新闻采集（每小时）
    try:
        from collector_news import NewsCollector
        c = NewsCollector()
        count = c.collect_from_rss()
        results["news"] = count
        logger.info(f"[news] 入库 {count} 条")
    except Exception as e:
        logger.error(f"[news] 失败: {e}")
        results["news"] = f"FAIL: {e}"

    # 2. 政策采集（每天）
    try:
        from collector_policy import PolicyCollector
        c = PolicyCollector()
        count = c.collect_all()
        results["policies"] = count
        logger.info(f"[policies] 入库 {count} 条")
    except Exception as e:
        logger.error(f"[policies] 失败: {e}")
        results["policies"] = f"FAIL: {e}"

    # 3. 融资事件采集（每天）
    try:
        from collector_funding import FundingCollector
        c = FundingCollector()
        count = c.collect_from_sources()
        results["funding_events"] = count
        logger.info(f"[funding_events] 入库 {count} 条")
    except Exception as e:
        logger.error(f"[funding_events] 失败: {e}")
        results["funding_events"] = f"FAIL: {e}"

    # 4. 专利日常采集（每天）
    try:
        from patent_daily_collector import PatentDailyCollector
        c = PatentDailyCollector()
        stats = c.run(days_back=1, max_results=20)
        results["patents"] = stats
        logger.info(f"[patents] 搜索 {stats.get('searched',0)} | 入库 {stats.get('saved',0)}")
    except Exception as e:
        logger.error(f"[patents] 失败: {e}")
        results["patents"] = f"FAIL: {e}"

    # 5. 企业采集（每周 / 按需）
    try:
        from collector_company import CompanyCollector
        c = CompanyCollector()
        count = c.collect_all()
        results["companies"] = count
        logger.info(f"[companies] 入库 {count} 条")
    except Exception as e:
        logger.error(f"[companies] 失败: {e}")
        results["companies"] = f"FAIL: {e}"

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    logger.info(f"采集完成，耗时 {duration:.1f}s")
    logger.info(f"结果: {results}")
    logger.info("=" * 50)
    return results


# 阿里云 FC handler
def handler(event, context):
    """阿里云 FC 入口函数"""
    return run_all_collectors()


if __name__ == "__main__":
    run_all_collectors()
