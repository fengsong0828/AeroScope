-- AeroScope 企业别名表 + 去重辅助索引
-- 请在 Supabase SQL Editor 中运行

-- 1. 企业别名表
CREATE TABLE IF NOT EXISTS company_aliases (
    id          BIGSERIAL PRIMARY KEY,
    company_id  BIGINT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    alias_name  TEXT   NOT NULL,
    source      TEXT   DEFAULT 'manual',   -- patent_applicant / manual / llm / fuzzy_match
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_aliases_company_id ON company_aliases(company_id);
CREATE INDEX IF NOT EXISTS idx_aliases_name       ON company_aliases(alias_name);

-- 2. 给 companies.name 加索引（如果还没加），加速去重查询
CREATE INDEX IF NOT EXISTS idx_companies_name ON companies(name);

-- 3. 给 patents.applicant 加 trigram 索引（模糊匹配加速）
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX IF NOT EXISTS idx_patents_applicant_trgm ON patents USING gin (applicant gin_trgm_ops);

-- 4. 去重辅助函数：标准化企业名称（去除次要干扰，保留核心主干）
CREATE OR REPLACE FUNCTION normalize_company_name(raw text)
RETURNS text AS $$
DECLARE
    n text;
BEGIN
    n := trim(raw);
    -- 去除括号内容（地区、上市代码等）
    n := regexp_replace(n, '[（(].*?[）)]', '', 'g');
    -- 去除法人后缀（保留在别名表中，标准化只用于匹配）
    n := regexp_replace(n, '股份?有限公司$|有限(责任)?公司$|有限合伙$|（普通合伙）$|集团(有限)?公司$|企业$', '', 'g');
    -- 去除英文法人后缀
    n := regexp_replace(n, '\s+(Inc\.?|Ltd\.?|LLC|Corp\.?|GmbH|S\.?A\.?|Co\.,?\s*Ltd\.?|PLC|B\.?V\.?|KK)$', '', 'gi');
    -- 去除首尾空白和多余空格
    RETURN trim(regexp_replace(n, '\s+', ' ', 'g'));
END;
$$ LANGUAGE plpgsql IMMUTABLE;
