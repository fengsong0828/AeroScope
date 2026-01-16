# 🚁 AeroScope Insight | 低空经济产业情报平台

> **构建低空经济时代的数字大脑与决策引擎**  
> Connecting Policy, Capital, and Technology for the Low-Altitude Economy.

![Project Status](https://img.shields.io/badge/Status-Active_Development-blue)
![Tech Stack](https://img.shields.io/badge/Stack-Supabase_|_Aliyun_|_VanillaJS-green)
![AI Powered](https://img.shields.io/badge/AI-LLM_Integrated-purple)

## 📖 项目简介 (Introduction)

**AeroScope Insight** 是一个垂直于低空经济（eVTOL、无人机、飞行汽车）领域的综合数据情报平台。

作为一个独立开发项目，本平台旨在解决行业信息分散、数据结构化程度低的问题。通过 **"Serverless 架构 + AI 智能采编"** 的模式，以极低的成本实现了从数据采集、清洗、关联到展示的全流程闭环。

核心价值在于通过构建**行业知识图谱**，打破政策、专利、资本和企业之间的信息孤岛，为投资者、政府和从业者提供决策辅助。

## ✨ 核心功能 (Features)

### 📊 数据可视化与图谱
- **全球产业链图谱**：基于 ECharts 的交互式地图与关系网，展示上下游企业（上游材料、中游整机、下游运营）的分布与关联。
- **融资趋势看板**：实时统计全球 eVTOL 领域的融资热度、事件及活跃投资机构。
- **技术专利库**：收录并分析核心技术专利，通过 AI 评估技术成熟度 (TRL) 与创新等级。

### 🧠 AI 驱动的智能采编系统 (Admin Console)
- **多源信息聚合**：支持 URL 链接智能解析与文本粘贴。
- **LLM 结构化清洗**：内置 Prompt 模板，调用大模型（DeepSeek/Qwen）自动提取新闻摘要、企业工商信息、专利关键点，并输出为标准 JSON 入库。
- **自动化标签体系**：自动为内容打上“技术领域”、“产业链位置”等标签，建立语义关联。

### 🗂️ 垂直数据库
- **政策法规库**：覆盖发改委、民航局及地方政府的最新低空经济政策。
- **产品与机型库**：收录全球主流 eVTOL 机型参数（航程、载重、适航状态）。
- **企业图谱**：深度整合企业融资历程、专利布局与相关新闻。

## 🛠️ 技术栈 (Tech Stack)

本项目采用 **极简主义 + 云原生** 架构，最大化开发效率与系统性能。

| 模块 | 技术选型 | 说明 |
| :--- | :--- | :--- |
| **Frontend** | HTML5, CSS3, Vanilla JS | 无框架依赖，极致轻量，加载速度快，SEO 友好 |
| **Backend / DB** | **Supabase** | 提供 PostgreSQL 数据库、Auth 认证、Edge Functions |
| **Storage** | **阿里云 OSS** | 存储高清图片、PDF 研报及大文件 |
| **Infrastructure** | **阿里云 ECS / FC** | 部署自动化爬虫脚本与定时任务 |
| **AI / LLM** | OpenAI API Standard | 兼容 DeepSeek V3 / 通义千问，用于数据清洗与 RAG |
| **Visualization** | ECharts | 高性能数据图表渲染 |

## 🏗️ 系统架构与数据流 (Architecture)

```mermaid
graph TD
    A[外部数据源<br>News/Gov/Patents] -->|Python Agent<br>阿里云 FC| B(AI 智能清洗层<br>LLM Parsing)
    B -->|结构化 JSON| C[(Supabase<br>PostgreSQL)]
    
    subgraph "Data Enhancement"
    C <-->|Vector Embedding| D[pgvector<br>语义索引]
    end
    
    C -->|REST/Socket| E[前端客户端<br>AeroScope Web]
    F[管理员<br>Admin Console] -->|人工审核/录入| C
    E -->|读取图片| G[阿里云 OSS]

