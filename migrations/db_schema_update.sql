-- AeroScope Database Optimization SQL Script
-- 请在 Supabase 的 SQL Editor 中运行此脚本

-- 1. [关键] 修复 products 表缺少 description 字段的问题
-- fix: Could not find the 'description' column of 'products'
ALTER TABLE products ADD COLUMN description TEXT;

-- 2. [关键] 为 deep_reports 表添加文件存储字段
-- fix: 允许上传 PDF 报告到私有存储桶
ALTER TABLE deep_reports ADD COLUMN file_url TEXT;

-- 3. [建议] 将核心参数从 specs JSONB 字段提取为独立列
-- 目的：允许在数据库层面进行筛选（如 "航程 > 100km"），提高性能并规范数据结构
-- 注意：添加列后，现有的 JSON 数据需要迁移（可以使用 update 语句）

-- ALTER TABLE products ADD COLUMN range_km NUMERIC;
-- ALTER TABLE products ADD COLUMN speed_kmh NUMERIC;
-- ALTER TABLE products ADD COLUMN payload_kg NUMERIC;
-- ALTER TABLE products ADD COLUMN propulsion TEXT;
-- ALTER TABLE products ADD COLUMN piloting TEXT;

-- 数据迁移示例 (如果决定启用上述字段):
-- UPDATE products SET 
--   range_km = (specs->>'range_km')::numeric,
--   speed_kmh = (specs->>'speed_kmh')::numeric,
--   payload_kg = (specs->>'payload_kg')::numeric,
--   propulsion = specs->>'propulsion',
--   piloting = specs->>'piloting';

-- 4. [新增] 专利分类体系 v2.0 —— 新增二级分类字段
-- 目的：细化专利技术分类粒度，支持产业链细分环节标注
ALTER TABLE patents ADD COLUMN IF NOT EXISTS technical_subcategory TEXT;
COMMENT ON COLUMN patents.technical_subcategory IS '二级技术子类（如：倾转旋翼技术、固态电池）';
COMMENT ON COLUMN patents.technical_categories IS '一级技术分类（如：飞行器构型设计、动力系统）';

ALTER TABLE patents ADD COLUMN IF NOT EXISTS industry_chain_sub TEXT;
COMMENT ON COLUMN patents.industry_chain_sub IS '产业链细分环节（上游-原材料/上游-核心零部件/中游-分系统/中游-整机制造/下游-运营服务/下游-飞行保障/其他-待审核）';

ALTER TABLE patents ADD COLUMN IF NOT EXISTS classification_confidence FLOAT;
COMMENT ON COLUMN patents.classification_confidence IS '分类置信度 0.0-1.0，低于0.6的建议人工审核';

-- 5. [建议] 为 companies 表新增产业链细分字段，与专利体系对齐
ALTER TABLE companies ADD COLUMN IF NOT EXISTS industry_chain_sub TEXT;
COMMENT ON COLUMN companies.industry_chain_sub IS '产业链细分环节（与patents.industry_chain_sub对齐）';

-- 6. [新增] 专利PDF链接字段，用于前端 PDF 预览
ALTER TABLE patents ADD COLUMN IF NOT EXISTS pdf_url TEXT;
COMMENT ON COLUMN patents.pdf_url IS '专利PDF文件URL（OSS私有桶签名链接）';
