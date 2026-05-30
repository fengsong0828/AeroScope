"""
AeroScope 数据采集 — 核心模块
共享: Supabase 连接 / LLM 结构化 / Upsert / 日志
"""
import os
import json
import time
import logging
from datetime import datetime
from typing import Optional

import requests
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("aeroscope")


class CollectorCore:
    """采集器基类，提供 Supabase 连接、LLM 调用、upsert 等公共能力"""

    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_ANON_KEY")
        self.supabase_service_role = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        self.llm_api_key = os.getenv("LLM_API_KEY")
        self.llm_base_url = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
        self.llm_model = os.getenv("LLM_MODEL", "deepseek-chat")
        self._init_supabase()

    def _init_supabase(self):
        try:
            from supabase import create_client
            # 读操作用 anon key，写操作用 service_role
            self.db = create_client(self.supabase_url, self.supabase_key)
            if self.supabase_service_role:
                self.db_write = create_client(self.supabase_url, self.supabase_service_role)
            else:
                self.db_write = self.db
            logger.info("Supabase 连接成功")
        except Exception as e:
            logger.error(f"Supabase 连接失败: {e}")
            self.db = None
            self.db_write = None

    def call_llm(self, system_prompt: str, user_text: str, retries: int = 3) -> Optional[str]:
        """调用 DeepSeek API 进行文本结构化"""
        headers = {
            "Authorization": f"Bearer {self.llm_api_key}",
            "Content-Type": "application/json"
        }
        body = {
            "model": self.llm_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text}
            ],
            "temperature": 0.1,
            "max_tokens": 4000
        }
        for attempt in range(retries):
            try:
                resp = requests.post(
                    f"{self.llm_base_url}/chat/completions",
                    headers=headers, json=body, timeout=120
                )
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"]
            except Exception as e:
                logger.warning(f"LLM 调用失败 (尝试 {attempt+1}/{retries}): {e}")
                time.sleep(2 ** attempt)
        return None

    @staticmethod
    def _normalize_legal_status(raw):
        if not raw:
            return ""
        s = raw.strip().lower()
        if s in ("granted", "active", "valid", "patented case"):
            return "有效"
        if any(kw in s for kw in ("expired", "fee related", "lapsed", "abandoned",
                                    "withdrawn", "revoked", "ceased", "terminated",
                                    "rejected", "refused", "invalid")):
            return "无效"
        if any(kw in s for kw in ("pending", "application", "filed", "examination",
                                    "search report", "substantive examination")):
            return "审中"
        return ""

    def upsert(self, table: str, data: dict, unique_key: str) -> bool:
        """按唯一键 upsert 到 Supabase，自动填 draft=false 和 created_at，写入用 service_role 绕过 RLS"""
        dbw = self.db_write or self.db
        if not dbw:
            logger.error("数据库写客户端未连接，跳过 upsert")
            return False
        data.setdefault("draft", False)
        if "created_at" not in data:
            data["created_at"] = datetime.utcnow().isoformat()
        if table == "patents" and "legal_status" in data:
            raw = data["legal_status"]
            normalized = self._normalize_legal_status(raw)
            if normalized:
                data["legal_status"] = normalized
            else:
                del data["legal_status"]
        try:
            keys = data.get(unique_key)
            if not keys:
                logger.warning(f"数据缺少唯一键 {unique_key}，跳过: {data.get('title','')[:40]}")
                return False
            # 读操作用 anon key（查重）
            existing = self.db.table(table).select("id").eq(unique_key, keys).execute() if self.db else type('obj', (object,), {'data': []})()
            if existing.data:
                dbw.table(table).update(data).eq(unique_key, keys).execute()
                logger.info(f"[{table}] 更新: {keys}")
            else:
                dbw.table(table).insert(data).execute()
                logger.info(f"[{table}] 新增: {keys}")
            return True
        except Exception as e:
            logger.error(f"[{table}] upsert 失败: {e}")
            return False

    def parse_llm_json(self, raw: str) -> Optional[dict]:
        """从 LLM 返回中提取 JSON 对象"""
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            import re
            match = re.search(r'\{[\s\S]*\}', raw)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass
        logger.error(f"无法解析 LLM 输出为 JSON: {raw[:200]}")
        return None

    def log_collection(self, source: str, status: str, message: str = ""):
        """记录采集日志"""
        log_entry = f"[{source}] {status}: {message}" if message else f"[{source}] {status}"
        logger.info(log_entry)
