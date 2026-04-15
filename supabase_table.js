[
  {
    "table_schema": "public",
    "table_name": "article_comments",
    "column_name": "id",
    "data_type": "bigint",
    "character_maximum_length": null,
    "is_nullable": "NO",
    "column_default": null,
    "column_comment": null
  },
  {
    "table_schema": "public",
    "table_name": "article_comments",
    "column_name": "user_id",
    "data_type": "uuid",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": null
  },
  {
    "table_schema": "public",
    "table_name": "article_comments",
    "column_name": "user_email",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": null
  },
  {
    "table_schema": "public",
    "table_name": "article_comments",
    "column_name": "target_table",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "NO",
    "column_default": null,
    "column_comment": "目标表 (news/policies/tech)"
  },
  {
    "table_schema": "public",
    "table_name": "article_comments",
    "column_name": "target_id",
    "data_type": "bigint",
    "character_maximum_length": null,
    "is_nullable": "NO",
    "column_default": null,
    "column_comment": "目标文章ID"
  },
  {
    "table_schema": "public",
    "table_name": "article_comments",
    "column_name": "content",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "NO",
    "column_default": null,
    "column_comment": "评论内容"
  },
  {
    "table_schema": "public",
    "table_name": "article_comments",
    "column_name": "created_at",
    "data_type": "timestamp with time zone",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "now()",
    "column_comment": null
  },
  {
    "table_schema": "public",
    "table_name": "companies",
    "column_name": "id",
    "data_type": "bigint",
    "character_maximum_length": null,
    "is_nullable": "NO",
    "column_default": null,
    "column_comment": "企业ID"
  },
  {
    "table_schema": "public",
    "table_name": "companies",
    "column_name": "name",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "NO",
    "column_default": null,
    "column_comment": "企业全称 (中文)"
  },
  {
    "table_schema": "public",
    "table_name": "companies",
    "column_name": "name_en",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "英文名称"
  },
  {
    "table_schema": "public",
    "table_name": "companies",
    "column_name": "ticker_symbol",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "股票代码 (如 EH, JOBY)"
  },
  {
    "table_schema": "public",
    "table_name": "companies",
    "column_name": "country_code",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "'CN'::text",
    "column_comment": "国家代码 (ISO二字码, 如 CN, US)"
  },
  {
    "table_schema": "public",
    "table_name": "companies",
    "column_name": "logo_url",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "Logo图片链接"
  },
  {
    "table_schema": "public",
    "table_name": "companies",
    "column_name": "website_url",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "官网链接"
  },
  {
    "table_schema": "public",
    "table_name": "companies",
    "column_name": "industry_chain",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "产业链位置 (upstream, midstream, downstream)"
  },
  {
    "table_schema": "public",
    "table_name": "companies",
    "column_name": "primary_category",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "主营赛道 (eVTOL, Drone, Battery等)"
  },
  {
    "table_schema": "public",
    "table_name": "companies",
    "column_name": "tags",
    "data_type": "ARRAY",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "企业标签 (数组, 如: 独角兽, 专精特新)"
  },
  {
    "table_schema": "public",
    "table_name": "companies",
    "column_name": "description",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "企业简介"
  },
  {
    "table_schema": "public",
    "table_name": "companies",
    "column_name": "location",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "总部所在地 (城市)"
  },
  {
    "table_schema": "public",
    "table_name": "companies",
    "column_name": "total_funding_est_usd",
    "data_type": "numeric",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "累计融资估算 (单位: 美元)"
  },
  {
    "table_schema": "public",
    "table_name": "companies",
    "column_name": "is_listed",
    "data_type": "boolean",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "false",
    "column_comment": "是否上市"
  },
  {
    "table_schema": "public",
    "table_name": "companies",
    "column_name": "status",
    "data_type": "USER-DEFINED",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "'published'::content_status",
    "column_comment": "记录状态 (published/archived)"
  },
  {
    "table_schema": "public",
    "table_name": "companies",
    "column_name": "draft",
    "data_type": "boolean",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "false",
    "column_comment": "草稿标记 (true=前端不可见)"
  },
  {
    "table_schema": "public",
    "table_name": "companies",
    "column_name": "created_at",
    "data_type": "timestamp with time zone",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "now()",
    "column_comment": "收录时间"
  },
  {
    "table_schema": "public",
    "table_name": "companies",
    "column_name": "website",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "官网 (冗余字段，建议用 website_url)"
  },
  {
    "table_schema": "public",
    "table_name": "companies",
    "column_name": "founded_year",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "成立年份"
  },
  {
    "table_schema": "public",
    "table_name": "companies",
    "column_name": "industry_sector",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "行业板块细分"
  },
  {
    "table_schema": "public",
    "table_name": "companies",
    "column_name": "updated_at",
    "data_type": "timestamp with time zone",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "now()",
    "column_comment": null
  },
  {
    "table_schema": "public",
    "table_name": "cooperation_leads",
    "column_name": "id",
    "data_type": "bigint",
    "character_maximum_length": null,
    "is_nullable": "NO",
    "column_default": null,
    "column_comment": null
  },
  {
    "table_schema": "public",
    "table_name": "cooperation_leads",
    "column_name": "contact_name",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "NO",
    "column_default": null,
    "column_comment": "联系人姓名"
  },
  {
    "table_schema": "public",
    "table_name": "cooperation_leads",
    "column_name": "company_name",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "企业名称"
  },
  {
    "table_schema": "public",
    "table_name": "cooperation_leads",
    "column_name": "contact_email",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "NO",
    "column_default": null,
    "column_comment": "联系邮箱"
  },
  {
    "table_schema": "public",
    "table_name": "cooperation_leads",
    "column_name": "contact_phone",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "电话"
  },
  {
    "table_schema": "public",
    "table_name": "cooperation_leads",
    "column_name": "service_type",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "意向服务类型"
  },
  {
    "table_schema": "public",
    "table_name": "cooperation_leads",
    "column_name": "message",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "需求留言"
  },
  {
    "table_schema": "public",
    "table_name": "cooperation_leads",
    "column_name": "status",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "'pending'::text",
    "column_comment": "跟进状态 (pending/contacted/closed)"
  },
  {
    "table_schema": "public",
    "table_name": "cooperation_leads",
    "column_name": "created_at",
    "data_type": "timestamp with time zone",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "now()",
    "column_comment": "提交时间"
  },
  {
    "table_schema": "public",
    "table_name": "deep_reports",
    "column_name": "id",
    "data_type": "bigint",
    "character_maximum_length": null,
    "is_nullable": "NO",
    "column_default": null,
    "column_comment": "报告ID"
  },
  {
    "table_schema": "public",
    "table_name": "deep_reports",
    "column_name": "title",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "NO",
    "column_default": null,
    "column_comment": "报告标题"
  },
  {
    "table_schema": "public",
    "table_name": "deep_reports",
    "column_name": "author",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "作者/机构"
  },
  {
    "table_schema": "public",
    "table_name": "deep_reports",
    "column_name": "publish_date",
    "data_type": "date",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "发布日期"
  },
  {
    "table_schema": "public",
    "table_name": "deep_reports",
    "column_name": "image_url",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "封面图"
  },
  {
    "table_schema": "public",
    "table_name": "deep_reports",
    "column_name": "summary",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "报告摘要"
  },
  {
    "table_schema": "public",
    "table_name": "deep_reports",
    "column_name": "content",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "报告正文 (或大纲)"
  },
  {
    "table_schema": "public",
    "table_name": "deep_reports",
    "column_name": "is_pro_only",
    "data_type": "boolean",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "true",
    "column_comment": "是否需要付费/会员解锁"
  },
  {
    "table_schema": "public",
    "table_name": "deep_reports",
    "column_name": "draft",
    "data_type": "boolean",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "true",
    "column_comment": "是否草稿"
  },
  {
    "table_schema": "public",
    "table_name": "deep_reports",
    "column_name": "created_at",
    "data_type": "timestamp with time zone",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "now()",
    "column_comment": "创建时间"
  },
  {
    "table_schema": "public",
    "table_name": "forum_comments",
    "column_name": "id",
    "data_type": "bigint",
    "character_maximum_length": null,
    "is_nullable": "NO",
    "column_default": null,
    "column_comment": null
  },
  {
    "table_schema": "public",
    "table_name": "forum_comments",
    "column_name": "topic_id",
    "data_type": "bigint",
    "character_maximum_length": null,
    "is_nullable": "NO",
    "column_default": null,
    "column_comment": "所属帖子ID"
  },
  {
    "table_schema": "public",
    "table_name": "forum_comments",
    "column_name": "user_id",
    "data_type": "uuid",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "评论人ID"
  },
  {
    "table_schema": "public",
    "table_name": "forum_comments",
    "column_name": "user_email",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "评论人邮箱"
  },
  {
    "table_schema": "public",
    "table_name": "forum_comments",
    "column_name": "content",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "NO",
    "column_default": null,
    "column_comment": "评论内容"
  },
  {
    "table_schema": "public",
    "table_name": "forum_comments",
    "column_name": "created_at",
    "data_type": "timestamp with time zone",
    "character_maximum_length": null,
    "is_nullable": "NO",
    "column_default": "timezone('utc'::text, now())",
    "column_comment": "评论时间"
  },
  {
    "table_schema": "public",
    "table_name": "forum_topics",
    "column_name": "id",
    "data_type": "bigint",
    "character_maximum_length": null,
    "is_nullable": "NO",
    "column_default": null,
    "column_comment": "帖子ID"
  },
  {
    "table_schema": "public",
    "table_name": "forum_topics",
    "column_name": "user_id",
    "data_type": "uuid",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "发帖用户ID"
  },
  {
    "table_schema": "public",
    "table_name": "forum_topics",
    "column_name": "user_email",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "发帖人邮箱 (冗余)"
  },
  {
    "table_schema": "public",
    "table_name": "forum_topics",
    "column_name": "title",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "帖子标题"
  },
  {
    "table_schema": "public",
    "table_name": "forum_topics",
    "column_name": "content",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "帖子内容"
  },
  {
    "table_schema": "public",
    "table_name": "forum_topics",
    "column_name": "category",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "板块分类"
  },
  {
    "table_schema": "public",
    "table_name": "forum_topics",
    "column_name": "likes",
    "data_type": "integer",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "0",
    "column_comment": "点赞数"
  },
  {
    "table_schema": "public",
    "table_name": "forum_topics",
    "column_name": "heat_score",
    "data_type": "integer",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "0",
    "column_comment": "热度值 (算法计算)"
  },
  {
    "table_schema": "public",
    "table_name": "forum_topics",
    "column_name": "created_at",
    "data_type": "timestamp with time zone",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "now()",
    "column_comment": "发帖时间"
  },
  {
    "table_schema": "public",
    "table_name": "forum_topics",
    "column_name": "is_expert",
    "data_type": "boolean",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "false",
    "column_comment": "是否专家贴 (高亮)"
  },
  {
    "table_schema": "public",
    "table_name": "forum_topics",
    "column_name": "author_role",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "作者头衔 (快照)"
  },
  {
    "table_schema": "public",
    "table_name": "forum_topics",
    "column_name": "author_avatar_text",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "头像文字"
  },
  {
    "table_schema": "public",
    "table_name": "forum_topics",
    "column_name": "source_news_link",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "引用新闻链接"
  },
  {
    "table_schema": "public",
    "table_name": "forum_topics",
    "column_name": "source_news_title",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "引用新闻标题"
  },
  {
    "table_schema": "public",
    "table_name": "forum_topics",
    "column_name": "comments_count",
    "data_type": "integer",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "0",
    "column_comment": "评论数"
  },
  {
    "table_schema": "public",
    "table_name": "funding_events",
    "column_name": "id",
    "data_type": "uuid",
    "character_maximum_length": null,
    "is_nullable": "NO",
    "column_default": "uuid_generate_v4()",
    "column_comment": "事件ID (UUID)"
  },
  {
    "table_schema": "public",
    "table_name": "funding_events",
    "column_name": "company_id",
    "data_type": "bigint",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "被投公司ID"
  },
  {
    "table_schema": "public",
    "table_name": "funding_events",
    "column_name": "company_name",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "被投公司名称 (冗余快照)"
  },
  {
    "table_schema": "public",
    "table_name": "funding_events",
    "column_name": "funding_round",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "轮次 (Seed, A, B...)"
  },
  {
    "table_schema": "public",
    "table_name": "funding_events",
    "column_name": "funding_amount",
    "data_type": "numeric",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "融资金额 (原币种数值)"
  },
  {
    "table_schema": "public",
    "table_name": "funding_events",
    "column_name": "funding_currency",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "'USD'::text",
    "column_comment": "币种 (USD/CNY/EUR)"
  },
  {
    "table_schema": "public",
    "table_name": "funding_events",
    "column_name": "valuation",
    "data_type": "numeric",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "投后估值"
  },
  {
    "table_schema": "public",
    "table_name": "funding_events",
    "column_name": "funding_date",
    "data_type": "date",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "融资日期"
  },
  {
    "table_schema": "public",
    "table_name": "funding_events",
    "column_name": "announcement_date",
    "data_type": "date",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "官宣日期"
  },
  {
    "table_schema": "public",
    "table_name": "funding_events",
    "column_name": "lead_investor",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "领投方 (文本描述)"
  },
  {
    "table_schema": "public",
    "table_name": "funding_events",
    "column_name": "participating_investors",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "跟投方 (文本描述)"
  },
  {
    "table_schema": "public",
    "table_name": "funding_events",
    "column_name": "investor_count",
    "data_type": "integer",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "0",
    "column_comment": "投资方数量"
  },
  {
    "table_schema": "public",
    "table_name": "funding_events",
    "column_name": "use_of_proceeds",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "资金用途"
  },
  {
    "table_schema": "public",
    "table_name": "funding_events",
    "column_name": "status",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "'confirmed'::text",
    "column_comment": "交易状态 (confirmed/rumored)"
  },
  {
    "table_schema": "public",
    "table_name": "funding_events",
    "column_name": "data_source",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "数据来源"
  },
  {
    "table_schema": "public",
    "table_name": "funding_events",
    "column_name": "source_url",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "来源链接"
  },
  {
    "table_schema": "public",
    "table_name": "funding_events",
    "column_name": "notes",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "备注"
  },
  {
    "table_schema": "public",
    "table_name": "funding_events",
    "column_name": "draft",
    "data_type": "boolean",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "false",
    "column_comment": "草稿"
  },
  {
    "table_schema": "public",
    "table_name": "funding_events",
    "column_name": "created_at",
    "data_type": "timestamp with time zone",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "now()",
    "column_comment": "创建时间"
  },
  {
    "table_schema": "public",
    "table_name": "funding_events",
    "column_name": "updated_at",
    "data_type": "timestamp with time zone",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "now()",
    "column_comment": "更新时间"
  },
  {
    "table_schema": "public",
    "table_name": "funding_investors",
    "column_name": "id",
    "data_type": "uuid",
    "character_maximum_length": null,
    "is_nullable": "NO",
    "column_default": "uuid_generate_v4()",
    "column_comment": null
  },
  {
    "table_schema": "public",
    "table_name": "funding_investors",
    "column_name": "funding_event_id",
    "data_type": "uuid",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "关联融资事件ID"
  },
  {
    "table_schema": "public",
    "table_name": "funding_investors",
    "column_name": "investor_id",
    "data_type": "uuid",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "关联投资机构ID"
  },
  {
    "table_schema": "public",
    "table_name": "funding_investors",
    "column_name": "investment_amount",
    "data_type": "numeric",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "该机构的具体出资额 (如已知)"
  },
  {
    "table_schema": "public",
    "table_name": "funding_investors",
    "column_name": "investor_role",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "角色 (Lead/Follow)"
  },
  {
    "table_schema": "public",
    "table_name": "funding_investors",
    "column_name": "created_at",
    "data_type": "timestamp with time zone",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "now()",
    "column_comment": null
  },
  {
    "table_schema": "public",
    "table_name": "funding_round_definitions",
    "column_name": "id",
    "data_type": "uuid",
    "character_maximum_length": null,
    "is_nullable": "NO",
    "column_default": "gen_random_uuid()",
    "column_comment": null
  },
  {
    "table_schema": "public",
    "table_name": "funding_round_definitions",
    "column_name": "round_name",
    "data_type": "character varying",
    "character_maximum_length": 50,
    "is_nullable": "NO",
    "column_default": null,
    "column_comment": "轮次名称"
  },
  {
    "table_schema": "public",
    "table_name": "funding_round_definitions",
    "column_name": "display_order",
    "data_type": "integer",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "排序权重"
  },
  {
    "table_schema": "public",
    "table_name": "funding_round_definitions",
    "column_name": "min_amount",
    "data_type": "numeric",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "典型最小金额"
  },
  {
    "table_schema": "public",
    "table_name": "funding_round_definitions",
    "column_name": "max_amount",
    "data_type": "numeric",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "典型最大金额"
  },
  {
    "table_schema": "public",
    "table_name": "funding_round_definitions",
    "column_name": "description",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": null
  },
  {
    "table_schema": "public",
    "table_name": "funding_round_definitions",
    "column_name": "created_at",
    "data_type": "timestamp without time zone",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "now()",
    "column_comment": null
  },
  {
    "table_schema": "public",
    "table_name": "funding_trends",
    "column_name": "id",
    "data_type": "uuid",
    "character_maximum_length": null,
    "is_nullable": "NO",
    "column_default": "gen_random_uuid()",
    "column_comment": null
  },
  {
    "table_schema": "public",
    "table_name": "funding_trends",
    "column_name": "period_type",
    "data_type": "character varying",
    "character_maximum_length": 20,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "统计周期 (month/quarter/year)"
  },
  {
    "table_schema": "public",
    "table_name": "funding_trends",
    "column_name": "period_date",
    "data_type": "date",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "统计时间点"
  },
  {
    "table_schema": "public",
    "table_name": "funding_trends",
    "column_name": "region",
    "data_type": "character varying",
    "character_maximum_length": 100,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "区域维度"
  },
  {
    "table_schema": "public",
    "table_name": "funding_trends",
    "column_name": "sector",
    "data_type": "character varying",
    "character_maximum_length": 100,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "赛道维度"
  },
  {
    "table_schema": "public",
    "table_name": "funding_trends",
    "column_name": "total_amount",
    "data_type": "numeric",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "总金额"
  },
  {
    "table_schema": "public",
    "table_name": "funding_trends",
    "column_name": "deal_count",
    "data_type": "integer",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "交易数量"
  },
  {
    "table_schema": "public",
    "table_name": "funding_trends",
    "column_name": "avg_deal_size",
    "data_type": "numeric",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "平均交易额"
  },
  {
    "table_schema": "public",
    "table_name": "funding_trends",
    "column_name": "median_deal_size",
    "data_type": "numeric",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "中位数交易额"
  },
  {
    "table_schema": "public",
    "table_name": "funding_trends",
    "column_name": "top_deals",
    "data_type": "jsonb",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "Top交易列表 (JSON)"
  },
  {
    "table_schema": "public",
    "table_name": "funding_trends",
    "column_name": "amount_change_percent",
    "data_type": "numeric",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "金额环比变化"
  },
  {
    "table_schema": "public",
    "table_name": "funding_trends",
    "column_name": "deal_count_change",
    "data_type": "integer",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "数量环比变化"
  },
  {
    "table_schema": "public",
    "table_name": "funding_trends",
    "column_name": "created_at",
    "data_type": "timestamp without time zone",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "now()",
    "column_comment": null
  },
  {
    "table_schema": "public",
    "table_name": "funding_trends",
    "column_name": "updated_at",
    "data_type": "timestamp without time zone",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "now()",
    "column_comment": null
  },
  {
    "table_schema": "public",
    "table_name": "investors",
    "column_name": "id",
    "data_type": "uuid",
    "character_maximum_length": null,
    "is_nullable": "NO",
    "column_default": "uuid_generate_v4()",
    "column_comment": "机构ID"
  },
  {
    "table_schema": "public",
    "table_name": "investors",
    "column_name": "name",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "NO",
    "column_default": null,
    "column_comment": "机构名称"
  },
  {
    "table_schema": "public",
    "table_name": "investors",
    "column_name": "type",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "机构类型 (VC, PE, Angel, Govt)"
  },
  {
    "table_schema": "public",
    "table_name": "investors",
    "column_name": "country",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "所属国家"
  },
  {
    "table_schema": "public",
    "table_name": "investors",
    "column_name": "website",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "官网"
  },
  {
    "table_schema": "public",
    "table_name": "investors",
    "column_name": "description",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "简介"
  },
  {
    "table_schema": "public",
    "table_name": "investors",
    "column_name": "focus_areas",
    "data_type": "ARRAY",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "关注领域数组"
  },
  {
    "table_schema": "public",
    "table_name": "investors",
    "column_name": "investment_stages",
    "data_type": "ARRAY",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "投资阶段偏好"
  },
  {
    "table_schema": "public",
    "table_name": "investors",
    "column_name": "total_investments",
    "data_type": "integer",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "0",
    "column_comment": "累计投资次数"
  },
  {
    "table_schema": "public",
    "table_name": "investors",
    "column_name": "total_amount",
    "data_type": "numeric",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "0",
    "column_comment": "累计投资金额"
  },
  {
    "table_schema": "public",
    "table_name": "investors",
    "column_name": "draft",
    "data_type": "boolean",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "false",
    "column_comment": "草稿"
  },
  {
    "table_schema": "public",
    "table_name": "investors",
    "column_name": "created_at",
    "data_type": "timestamp with time zone",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "now()",
    "column_comment": "创建时间"
  },
  {
    "table_schema": "public",
    "table_name": "investors",
    "column_name": "updated_at",
    "data_type": "timestamp with time zone",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "now()",
    "column_comment": "更新时间"
  },
  {
    "table_schema": "public",
    "table_name": "media_requests",
    "column_name": "id",
    "data_type": "bigint",
    "character_maximum_length": null,
    "is_nullable": "NO",
    "column_default": null,
    "column_comment": null
  },
  {
    "table_schema": "public",
    "table_name": "media_requests",
    "column_name": "contact_name",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "NO",
    "column_default": null,
    "column_comment": null
  },
  {
    "table_schema": "public",
    "table_name": "media_requests",
    "column_name": "contact_email",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "NO",
    "column_default": null,
    "column_comment": null
  },
  {
    "table_schema": "public",
    "table_name": "media_requests",
    "column_name": "organization",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "机构名称"
  },
  {
    "table_schema": "public",
    "table_name": "media_requests",
    "column_name": "position",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": null
  },
  {
    "table_schema": "public",
    "table_name": "media_requests",
    "column_name": "request_type",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "请求类型 (收录/报道/融资)"
  },
  {
    "table_schema": "public",
    "table_name": "media_requests",
    "column_name": "project_name",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "项目/产品名称"
  },
  {
    "table_schema": "public",
    "table_name": "media_requests",
    "column_name": "summary",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": null
  },
  {
    "table_schema": "public",
    "table_name": "media_requests",
    "column_name": "material_link",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "资料链接 (BP/网盘)"
  },
  {
    "table_schema": "public",
    "table_name": "media_requests",
    "column_name": "status",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "'pending'::text",
    "column_comment": "审核状态"
  },
  {
    "table_schema": "public",
    "table_name": "media_requests",
    "column_name": "created_at",
    "data_type": "timestamp with time zone",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "now()",
    "column_comment": null
  },
  {
    "table_schema": "public",
    "table_name": "news",
    "column_name": "id",
    "data_type": "bigint",
    "character_maximum_length": null,
    "is_nullable": "NO",
    "column_default": null,
    "column_comment": "新闻ID"
  },
  {
    "table_schema": "public",
    "table_name": "news",
    "column_name": "title",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "NO",
    "column_default": null,
    "column_comment": "标题"
  },
  {
    "table_schema": "public",
    "table_name": "news",
    "column_name": "category",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "分类 (Market, Capital, Regulation)"
  },
  {
    "table_schema": "public",
    "table_name": "news",
    "column_name": "publish_date",
    "data_type": "date",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "发布日期"
  },
  {
    "table_schema": "public",
    "table_name": "news",
    "column_name": "source",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "来源媒体"
  },
  {
    "table_schema": "public",
    "table_name": "news",
    "column_name": "source_url",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "原文链接"
  },
  {
    "table_schema": "public",
    "table_name": "news",
    "column_name": "image_url",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "封面图"
  },
  {
    "table_schema": "public",
    "table_name": "news",
    "column_name": "summary",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "摘要"
  },
  {
    "table_schema": "public",
    "table_name": "news",
    "column_name": "content",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "正文内容 (Markdown)"
  },
  {
    "table_schema": "public",
    "table_name": "news",
    "column_name": "embedding",
    "data_type": "USER-DEFINED",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "向量数据 (用于AI搜索)"
  },
  {
    "table_schema": "public",
    "table_name": "news",
    "column_name": "draft",
    "data_type": "boolean",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "true",
    "column_comment": "是否草稿"
  },
  {
    "table_schema": "public",
    "table_name": "news",
    "column_name": "created_at",
    "data_type": "timestamp with time zone",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "now()",
    "column_comment": "创建时间"
  },
  {
    "table_schema": "public",
    "table_name": "news",
    "column_name": "tags",
    "data_type": "ARRAY",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "'{}'::text[]",
    "column_comment": "标签数组"
  },
  {
    "table_schema": "public",
    "table_name": "news",
    "column_name": "mentioned_company_ids",
    "data_type": "ARRAY",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": null
  },
  {
    "table_schema": "public",
    "table_name": "patents",
    "column_name": "id",
    "data_type": "uuid",
    "character_maximum_length": null,
    "is_nullable": "NO",
    "column_default": "gen_random_uuid()",
    "column_comment": "专利记录ID (UUID)"
  },
  {
    "table_schema": "public",
    "table_name": "patents",
    "column_name": "title",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "NO",
    "column_default": null,
    "column_comment": "专利标题"
  },
  {
    "table_schema": "public",
    "table_name": "patents",
    "column_name": "patent_number",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "专利号/授权号"
  },
  {
    "table_schema": "public",
    "table_name": "patents",
    "column_name": "patent_type",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "'发明专利'::text",
    "column_comment": "专利类型 (发明, 实用新型, 外观)"
  },
  {
    "table_schema": "public",
    "table_name": "patents",
    "column_name": "application_number",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "申请号"
  },
  {
    "table_schema": "public",
    "table_name": "patents",
    "column_name": "publication_number",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "公开号"
  },
  {
    "table_schema": "public",
    "table_name": "patents",
    "column_name": "applicant",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "NO",
    "column_default": null,
    "column_comment": "申请人 (公司或个人)"
  },
  {
    "table_schema": "public",
    "table_name": "patents",
    "column_name": "applicant_type",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "'企业'::text",
    "column_comment": "申请人类型 (企业, 高校, 研究院)"
  },
  {
    "table_schema": "public",
    "table_name": "patents",
    "column_name": "applicant_country",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "'中国'::text",
    "column_comment": "申请人国家"
  },
  {
    "table_schema": "public",
    "table_name": "patents",
    "column_name": "applicant_city",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "申请人城市"
  },
  {
    "table_schema": "public",
    "table_name": "patents",
    "column_name": "inventors",
    "data_type": "ARRAY",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "'{}'::text[]",
    "column_comment": "发明人列表 (数组)"
  },
  {
    "table_schema": "public",
    "table_name": "patents",
    "column_name": "inventor_count",
    "data_type": "integer",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "1",
    "column_comment": "发明人数量"
  },
  {
    "table_schema": "public",
    "table_name": "patents",
    "column_name": "ipc_class",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "IPC国际专利分类号"
  },
  {
    "table_schema": "public",
    "table_name": "patents",
    "column_name": "cpc_class",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "CPC联合专利分类号"
  },
  {
    "table_schema": "public",
    "table_name": "patents",
    "column_name": "technical_categories",
    "data_type": "ARRAY",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "'{}'::text[]",
    "column_comment": "技术分类标签 (数组)"
  },
  {
    "table_schema": "public",
    "table_name": "patents",
    "column_name": "industry_chain_position",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "产业链归属 (上/中/下游)"
  },
  {
    "table_schema": "public",
    "table_name": "patents",
    "column_name": "application_fields",
    "data_type": "ARRAY",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "'{}'::text[]",
    "column_comment": "应用领域 (物流, 载人, 巡检)"
  },
  {
    "table_schema": "public",
    "table_name": "patents",
    "column_name": "application_date",
    "data_type": "date",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "申请日期"
  },
  {
    "table_schema": "public",
    "table_name": "patents",
    "column_name": "publication_date",
    "data_type": "date",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "公开日期"
  },
  {
    "table_schema": "public",
    "table_name": "patents",
    "column_name": "grant_date",
    "data_type": "date",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "授权日期"
  },
  {
    "table_schema": "public",
    "table_name": "patents",
    "column_name": "priority_date",
    "data_type": "date",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "优先权日"
  },
  {
    "table_schema": "public",
    "table_name": "patents",
    "column_name": "abstract",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "专利摘要"
  },
  {
    "table_schema": "public",
    "table_name": "patents",
    "column_name": "claims",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "权利要求书概要"
  },
  {
    "table_schema": "public",
    "table_name": "patents",
    "column_name": "description_summary",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "说明书摘要"
  },
  {
    "table_schema": "public",
    "table_name": "patents",
    "column_name": "technical_field",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "技术领域描述"
  },
  {
    "table_schema": "public",
    "table_name": "patents",
    "column_name": "background_art",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "背景技术描述"
  },
  {
    "table_schema": "public",
    "table_name": "patents",
    "column_name": "legal_status",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "'审中'::text",
    "column_comment": "法律状态 (有效, 审中, 失效)"
  },
  {
    "table_schema": "public",
    "table_name": "patents",
    "column_name": "legal_status_date",
    "data_type": "date",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "法律状态更新日期"
  },
  {
    "table_schema": "public",
    "table_name": "patents",
    "column_name": "citation_count",
    "data_type": "integer",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "0",
    "column_comment": "被引用次数 (重要指标)"
  },
  {
    "table_schema": "public",
    "table_name": "patents",
    "column_name": "family_size",
    "data_type": "integer",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "1",
    "column_comment": "同族专利数量"
  },
  {
    "table_schema": "public",
    "table_name": "patents",
    "column_name": "forward_citations",
    "data_type": "integer",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "0",
    "column_comment": "前向引用数"
  },
  {
    "table_schema": "public",
    "table_name": "patents",
    "column_name": "backward_citations",
    "data_type": "integer",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "0",
    "column_comment": "后向引用数"
  },
  {
    "table_schema": "public",
    "table_name": "patents",
    "column_name": "estimated_value_usd",
    "data_type": "numeric",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "AI估算市场价值 (美元)"
  },
  {
    "table_schema": "public",
    "table_name": "patents",
    "column_name": "licensing_status",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "'未许可'::text",
    "column_comment": "许可状态 (已许可/未许可)"
  },
  {
    "table_schema": "public",
    "table_name": "patents",
    "column_name": "has_commercialization",
    "data_type": "boolean",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "false",
    "column_comment": "是否已转化/商用"
  },
  {
    "table_schema": "public",
    "table_name": "patents",
    "column_name": "related_projects",
    "data_type": "ARRAY",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "'{}'::text[]",
    "column_comment": "关联项目/产品名称"
  },
  {
    "table_schema": "public",
    "table_name": "patents",
    "column_name": "technology_maturity_level",
    "data_type": "integer",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "技术成熟度 (TRL 1-9)"
  },
  {
    "table_schema": "public",
    "table_name": "patents",
    "column_name": "innovation_level",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "创新等级 (High/Medium/Low)"
  },
  {
    "table_schema": "public",
    "table_name": "patents",
    "column_name": "technical_advantages",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "技术优势分析"
  },
  {
    "table_schema": "public",
    "table_name": "patents",
    "column_name": "data_source",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "'人工录入'::text",
    "column_comment": "数据来源渠道"
  },
  {
    "table_schema": "public",
    "table_name": "patents",
    "column_name": "data_quality_score",
    "data_type": "integer",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "80",
    "column_comment": "数据质量评分 (0-100)"
  },
  {
    "table_schema": "public",
    "table_name": "patents",
    "column_name": "is_verified",
    "data_type": "boolean",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "false",
    "column_comment": "是否经人工核验"
  },
  {
    "table_schema": "public",
    "table_name": "patents",
    "column_name": "verified_by",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "核验人"
  },
  {
    "table_schema": "public",
    "table_name": "patents",
    "column_name": "verified_date",
    "data_type": "date",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "核验日期"
  },
  {
    "table_schema": "public",
    "table_name": "patents",
    "column_name": "tags",
    "data_type": "ARRAY",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "'{}'::text[]",
    "column_comment": "自定义标签"
  },
  {
    "table_schema": "public",
    "table_name": "patents",
    "column_name": "notes",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "内部备注"
  },
  {
    "table_schema": "public",
    "table_name": "patents",
    "column_name": "created_at",
    "data_type": "timestamp with time zone",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "now()",
    "column_comment": "入库时间"
  },
  {
    "table_schema": "public",
    "table_name": "patents",
    "column_name": "updated_at",
    "data_type": "timestamp with time zone",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "now()",
    "column_comment": "更新时间"
  },
  {
    "table_schema": "public",
    "table_name": "patents",
    "column_name": "created_by",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "'system'::text",
    "column_comment": "创建人"
  },
  {
    "table_schema": "public",
    "table_name": "patents",
    "column_name": "updated_by",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "最后修改人"
  },
  {
    "table_schema": "public",
    "table_name": "patents",
    "column_name": "related_company_id",
    "data_type": "bigint",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": null
  },
  {
    "table_schema": "public",
    "table_name": "patents",
    "column_name": "draft",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": null
  },
  {
    "table_schema": "public",
    "table_name": "patents",
    "column_name": "related_company_ids",
    "data_type": "ARRAY",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": null
  },
  {
    "table_schema": "public",
    "table_name": "policies",
    "column_name": "id",
    "data_type": "bigint",
    "character_maximum_length": null,
    "is_nullable": "NO",
    "column_default": null,
    "column_comment": "政策ID"
  },
  {
    "table_schema": "public",
    "table_name": "policies",
    "column_name": "title",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "NO",
    "column_default": null,
    "column_comment": "政策标题"
  },
  {
    "table_schema": "public",
    "table_name": "policies",
    "column_name": "country_code",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "'CN'::text",
    "column_comment": "国家代码"
  },
  {
    "table_schema": "public",
    "table_name": "policies",
    "column_name": "department",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "发文部门 (如 CAAC, FAA)"
  },
  {
    "table_schema": "public",
    "table_name": "policies",
    "column_name": "level",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "层级 (国家级/地方级/国际)"
  },
  {
    "table_schema": "public",
    "table_name": "policies",
    "column_name": "region_type",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "区域类型"
  },
  {
    "table_schema": "public",
    "table_name": "policies",
    "column_name": "publish_date",
    "data_type": "date",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "发布日期"
  },
  {
    "table_schema": "public",
    "table_name": "policies",
    "column_name": "summary",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "政策解读/摘要"
  },
  {
    "table_schema": "public",
    "table_name": "policies",
    "column_name": "content",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "政策全文内容"
  },
  {
    "table_schema": "public",
    "table_name": "policies",
    "column_name": "file_url",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "原文件下载链接"
  },
  {
    "table_schema": "public",
    "table_name": "policies",
    "column_name": "source_url",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "来源网址"
  },
  {
    "table_schema": "public",
    "table_name": "policies",
    "column_name": "related_city",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "关联城市 (用于地图统计)"
  },
  {
    "table_schema": "public",
    "table_name": "policies",
    "column_name": "draft",
    "data_type": "boolean",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "true",
    "column_comment": "是否草稿"
  },
  {
    "table_schema": "public",
    "table_name": "policies",
    "column_name": "created_at",
    "data_type": "timestamp with time zone",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "now()",
    "column_comment": "创建时间"
  },
  {
    "table_schema": "public",
    "table_name": "policies",
    "column_name": "image_url",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "封面图链接"
  },
  {
    "table_schema": "public",
    "table_name": "products",
    "column_name": "id",
    "data_type": "bigint",
    "character_maximum_length": null,
    "is_nullable": "NO",
    "column_default": null,
    "column_comment": "产品ID"
  },
  {
    "table_schema": "public",
    "table_name": "products",
    "column_name": "company_id",
    "data_type": "bigint",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "所属厂商ID (关联 companies.id)"
  },
  {
    "table_schema": "public",
    "table_name": "products",
    "column_name": "name",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "NO",
    "column_default": null,
    "column_comment": "产品型号名称"
  },
  {
    "table_schema": "public",
    "table_name": "products",
    "column_name": "type",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "构型类型 (Multicopter, Lift+Cruise等)"
  },
  {
    "table_schema": "public",
    "table_name": "products",
    "column_name": "specs",
    "data_type": "jsonb",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "'{}'::jsonb",
    "column_comment": "性能参数JSON (航程, 载重, 速度等)"
  },
  {
    "table_schema": "public",
    "table_name": "products",
    "column_name": "image_url",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "产品图片链接"
  },
  {
    "table_schema": "public",
    "table_name": "products",
    "column_name": "certification_status",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "适航取证状态 (Concept, Prototype, Certified)"
  },
  {
    "table_schema": "public",
    "table_name": "products",
    "column_name": "status",
    "data_type": "USER-DEFINED",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "'published'::content_status",
    "column_comment": "发布状态"
  },
  {
    "table_schema": "public",
    "table_name": "products",
    "column_name": "created_at",
    "data_type": "timestamp with time zone",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "now()",
    "column_comment": "创建时间"
  },
  {
    "table_schema": "public",
    "table_name": "products",
    "column_name": "draft",
    "data_type": "boolean",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "false",
    "column_comment": "是否草稿"
  },
  {
    "table_schema": "public",
    "table_name": "products",
    "column_name": "manufacturer_name",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": null
  },
  {
    "table_schema": "public",
    "table_name": "products",
    "column_name": "updated_at",
    "data_type": "timestamp with time zone",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "now()",
    "column_comment": null
  },
  {
    "table_schema": "public",
    "table_name": "profiles",
    "column_name": "id",
    "data_type": "uuid",
    "character_maximum_length": null,
    "is_nullable": "NO",
    "column_default": null,
    "column_comment": "用户ID (关联 auth.users)"
  },
  {
    "table_schema": "public",
    "table_name": "profiles",
    "column_name": "email",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "登录邮箱"
  },
  {
    "table_schema": "public",
    "table_name": "profiles",
    "column_name": "full_name",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "真实姓名"
  },
  {
    "table_schema": "public",
    "table_name": "profiles",
    "column_name": "username",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "用户名/昵称 (用于社区显示)"
  },
  {
    "table_schema": "public",
    "table_name": "profiles",
    "column_name": "company_name",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "所属公司名称"
  },
  {
    "table_schema": "public",
    "table_name": "profiles",
    "column_name": "job_title",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "职位头衔"
  },
  {
    "table_schema": "public",
    "table_name": "profiles",
    "column_name": "phone",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "联系电话"
  },
  {
    "table_schema": "public",
    "table_name": "profiles",
    "column_name": "is_admin",
    "data_type": "boolean",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "false",
    "column_comment": "是否为管理员 (true=有后台权限)"
  },
  {
    "table_schema": "public",
    "table_name": "profiles",
    "column_name": "role",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "'user'::text",
    "column_comment": "系统角色 (user/editor/admin)"
  },
  {
    "table_schema": "public",
    "table_name": "profiles",
    "column_name": "tier",
    "data_type": "USER-DEFINED",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "'free'::member_tier",
    "column_comment": "会员等级 (枚举: free, pro, enterprise)"
  },
  {
    "table_schema": "public",
    "table_name": "profiles",
    "column_name": "subscription_status",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "'inactive'::text",
    "column_comment": "订阅状态 (active/inactive/past_due)"
  },
  {
    "table_schema": "public",
    "table_name": "profiles",
    "column_name": "current_period_end",
    "data_type": "timestamp with time zone",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "当前订阅到期时间"
  },
  {
    "table_schema": "public",
    "table_name": "profiles",
    "column_name": "created_at",
    "data_type": "timestamp with time zone",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "now()",
    "column_comment": "注册时间"
  },
  {
    "table_schema": "public",
    "table_name": "profiles",
    "column_name": "updated_at",
    "data_type": "timestamp with time zone",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "now()",
    "column_comment": "资料更新时间"
  },
  {
    "table_schema": "public",
    "table_name": "profiles",
    "column_name": "gender",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "性别"
  },
  {
    "table_schema": "public",
    "table_name": "profiles",
    "column_name": "age_range",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "年龄段"
  },
  {
    "table_schema": "public",
    "table_name": "profiles",
    "column_name": "industry_role",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "行业角色 (如: 投资人, 工程师)"
  },
  {
    "table_schema": "public",
    "table_name": "profiles",
    "column_name": "linkedin_url",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "领英主页链接"
  },
  {
    "table_schema": "public",
    "table_name": "profiles",
    "column_name": "wechat_id",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "微信号"
  },
  {
    "table_schema": "public",
    "table_name": "profiles",
    "column_name": "work_years",
    "data_type": "integer",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "工作年限"
  },
  {
    "table_schema": "public",
    "table_name": "profiles",
    "column_name": "interested_tags",
    "data_type": "ARRAY",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "感兴趣的标签/领域 (数组)"
  },
  {
    "table_schema": "public",
    "table_name": "profiles",
    "column_name": "is_expert",
    "data_type": "boolean",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "false",
    "column_comment": "是否为认证专家 (true=显示专家徽章)"
  },
  {
    "table_schema": "public",
    "table_name": "tech_trends",
    "column_name": "id",
    "data_type": "bigint",
    "character_maximum_length": null,
    "is_nullable": "NO",
    "column_default": null,
    "column_comment": "记录ID"
  },
  {
    "table_schema": "public",
    "table_name": "tech_trends",
    "column_name": "title",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "NO",
    "column_default": null,
    "column_comment": "标题"
  },
  {
    "table_schema": "public",
    "table_name": "tech_trends",
    "column_name": "type",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "类型 (Patent/Paper/Product)"
  },
  {
    "table_schema": "public",
    "table_name": "tech_trends",
    "column_name": "org",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "研发机构/实验室"
  },
  {
    "table_schema": "public",
    "table_name": "tech_trends",
    "column_name": "publish_date",
    "data_type": "date",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "发布日期"
  },
  {
    "table_schema": "public",
    "table_name": "tech_trends",
    "column_name": "summary",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "技术摘要"
  },
  {
    "table_schema": "public",
    "table_name": "tech_trends",
    "column_name": "content",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "详细解读"
  },
  {
    "table_schema": "public",
    "table_name": "tech_trends",
    "column_name": "image_url",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "配图"
  },
  {
    "table_schema": "public",
    "table_name": "tech_trends",
    "column_name": "source_url",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "来源链接"
  },
  {
    "table_schema": "public",
    "table_name": "tech_trends",
    "column_name": "related_company_id",
    "data_type": "bigint",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "关联企业ID"
  },
  {
    "table_schema": "public",
    "table_name": "tech_trends",
    "column_name": "is_pro_only",
    "data_type": "boolean",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "false",
    "column_comment": "是否Pro会员专享"
  },
  {
    "table_schema": "public",
    "table_name": "tech_trends",
    "column_name": "draft",
    "data_type": "boolean",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "true",
    "column_comment": "是否草稿"
  },
  {
    "table_schema": "public",
    "table_name": "tech_trends",
    "column_name": "created_at",
    "data_type": "timestamp with time zone",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "now()",
    "column_comment": "创建时间"
  },
  {
    "table_schema": "public",
    "table_name": "tech_trends",
    "column_name": "domain",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "技术领域 (电池/飞控/复材)"
  },
  {
    "table_schema": "public",
    "table_name": "user_articles",
    "column_name": "id",
    "data_type": "uuid",
    "character_maximum_length": null,
    "is_nullable": "NO",
    "column_default": "gen_random_uuid()",
    "column_comment": null
  },
  {
    "table_schema": "public",
    "table_name": "user_articles",
    "column_name": "user_id",
    "data_type": "uuid",
    "character_maximum_length": null,
    "is_nullable": "NO",
    "column_default": null,
    "column_comment": null
  },
  {
    "table_schema": "public",
    "table_name": "user_articles",
    "column_name": "title",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "NO",
    "column_default": null,
    "column_comment": null
  },
  {
    "table_schema": "public",
    "table_name": "user_articles",
    "column_name": "category",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "NO",
    "column_default": null,
    "column_comment": null
  },
  {
    "table_schema": "public",
    "table_name": "user_articles",
    "column_name": "cover_image",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": null
  },
  {
    "table_schema": "public",
    "table_name": "user_articles",
    "column_name": "content",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "NO",
    "column_default": null,
    "column_comment": null
  },
  {
    "table_schema": "public",
    "table_name": "user_articles",
    "column_name": "summary",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": null
  },
  {
    "table_schema": "public",
    "table_name": "user_articles",
    "column_name": "status",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "'pending'::text",
    "column_comment": null
  },
  {
    "table_schema": "public",
    "table_name": "user_articles",
    "column_name": "views",
    "data_type": "integer",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "0",
    "column_comment": null
  },
  {
    "table_schema": "public",
    "table_name": "user_articles",
    "column_name": "likes",
    "data_type": "integer",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "0",
    "column_comment": null
  },
  {
    "table_schema": "public",
    "table_name": "user_articles",
    "column_name": "created_at",
    "data_type": "timestamp with time zone",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "timezone('utc'::text, now())",
    "column_comment": null
  },
  {
    "table_schema": "public",
    "table_name": "user_articles",
    "column_name": "updated_at",
    "data_type": "timestamp with time zone",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "timezone('utc'::text, now())",
    "column_comment": null
  },
  {
    "table_schema": "public",
    "table_name": "user_follows",
    "column_name": "id",
    "data_type": "bigint",
    "character_maximum_length": null,
    "is_nullable": "NO",
    "column_default": null,
    "column_comment": null
  },
  {
    "table_schema": "public",
    "table_name": "user_follows",
    "column_name": "user_id",
    "data_type": "uuid",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": null,
    "column_comment": "用户ID"
  },
  {
    "table_schema": "public",
    "table_name": "user_follows",
    "column_name": "target_type",
    "data_type": "text",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "'company'::text",
    "column_comment": "关注对象类型 (company/topic)"
  },
  {
    "table_schema": "public",
    "table_name": "user_follows",
    "column_name": "target_id",
    "data_type": "bigint",
    "character_maximum_length": null,
    "is_nullable": "NO",
    "column_default": null,
    "column_comment": "关注对象ID"
  },
  {
    "table_schema": "public",
    "table_name": "user_follows",
    "column_name": "created_at",
    "data_type": "timestamp with time zone",
    "character_maximum_length": null,
    "is_nullable": "YES",
    "column_default": "now()",
    "column_comment": null
  }
]