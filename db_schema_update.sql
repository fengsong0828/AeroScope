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
