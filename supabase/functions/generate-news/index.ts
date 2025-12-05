import { serve } from "https://deno.land/std@0.168.0/http/server.ts"

// 定义模型提供商配置
const PROVIDERS = {
  'deepseek': {
    url: 'https://api.deepseek.com/v1/chat/completions',
    key_env: 'DEEPSEEK_API_KEY'
  },
  'openai': {
    url: 'https://api.openai.com/v1/chat/completions',
    key_env: 'OPENAI_API_KEY'
  },
  'qwen': {
    url: 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions',
    key_env: 'DASHSCOPE_API_KEY'
  }
}

// 默认兜底提示词
const DEFAULT_PROMPTS = {
  news: "你是一名产业分析师。将输入内容改写为新闻。返回JSON: { title, summary, content, tags:[], category }",
  policy: "你是一名政策专家。分析政策文件。提取部门、层级、日期。返回JSON: { title, summary, content, department, level, publish_date, related_city, tags:[] }",
  tech: "你是技术专家。提取技术参数。返回JSON: { title, summary, content, type, org, tags:[] }",
  report: "你是分析师。撰写研报摘要。返回JSON: { title, summary, content, tags:[] }"
}

// ★★★ 优化 1: 更强大的 HTML 清洗函数 ★★★
// ★★★ 优化后的提取函数：针对中国政府网站优化 ★★★
function extractTextFromHtml(html: string): string {
  let text = html;

  // 1. 移除干扰项 (Head, Script, Style, Comments)
  text = text.replace(/<head[^>]*>[\s\S]*?<\/head>/gmi, "");
  text = text.replace(/<script[^>]*>[\s\S]*?<\/script>/gmi, "");
  text = text.replace(/<style[^>]*>[\s\S]*?<\/style>/gmi, "");
  text = text.replace(/<!--[\s\S]*?-->/g, "");

  // 2. ★★★ 核心升级：政府网站正文容器“指纹库” ★★★
  // 这是一个优先级列表，越靠前越可能是正文
  const contentSelectors = [
    // 1. 常见的 CMS 标记
    /<div[^>]*class="[^"]*TRS_Editor[^"]*"[^>]*>([\s\S]*?)<\/div>/i,  // 拓尔思系统
    /<div[^>]*id="[^"]*zoom[^"]*"[^>]*>([\s\S]*?)<\/div>/i,            // 老式缩放区
    /<div[^>]*class="[^"]*view[^"]*"[^>]*>([\s\S]*?)<\/div>/i,         // 常见视图区
    /<div[^>]*class="[^"]*article[^"]*"[^>]*>([\s\S]*?)<\/div>/i,
    
    // 2. 标准 HTML5 语义化标签
    /<article[^>]*>([\s\S]*?)<\/article>/i,
    /<main[^>]*>([\s\S]*?)<\/main>/i,
    
    // 3. 模糊匹配 (风险较大，放在最后)
    /<div[^>]*class="[^"]*content[^"]*"[^>]*>([\s\S]*?)<\/div>/i,
    /<div[^>]*id="[^"]*content[^"]*"[^>]*>([\s\S]*?)<\/div>/i
  ];

  // 尝试遍历指纹库，命中一个即停止
  let bestMatch = null;
  for (const regex of contentSelectors) {
    const match = text.match(regex);
    if (match && match[1].length > 100) { // 简单判断：正文应该至少有点长度
        console.log("命中正文规则:", regex);
        bestMatch = match[1];
        break;
    }
  }

  // 如果命中了特定区域，就只处理该区域；否则处理全文 (降级策略)
  if (bestMatch) {
    text = bestMatch;
  }

  // 3. 格式清洗 (转 Markdown 预处理)
  text = text.replace(/<\/p>/gi, "\n\n");
  text = text.replace(/<br\s*\/?>/gi, "\n");
  text = text.replace(/<\/div>/gi, "\n");
  text = text.replace(/<\/li>/gi, "\n");
  text = text.replace(/<h[1-6][^>]*>/gi, "\n### "); // 简单的标题保留
  
  // 4. 移除剩余标签
  text = text.replace(/<[^>]+>/g, "");
  
  // 5. 实体解码
  text = text.replace(/&nbsp;/g, " ").replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"');
  
  // 6. 压缩空行
  text = text.replace(/\n\s*\n/g, "\n\n").trim();
  
  return text;
}

// 清洗 JSON 字符串
function cleanJsonString(str: string): string {
  return str.replace(/^```json\s*/, "").replace(/^```\s*/, "").replace(/\s*```$/, "");
}

serve(async (req) => {
  // CORS
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: { 
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
    }})
  }

  try {
    const { content, model, category, systemPrompt } = await req.json()

    // 1. URL 抓取逻辑
    let finalContent = content;
    const urlRegex = /^(http|https):\/\/[^ "]+$/;
    let isUrlMode = false;
    
    if (urlRegex.test(content)) {
      isUrlMode = true;
      try {
        console.log(`正在抓取 URL: ${content}`);
        const res = await fetch(content, {
            headers: {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
        });
        if (res.ok) {
            const html = await res.text();
            finalContent = extractTextFromHtml(html);
            console.log(`抓取成功，清洗后长度: ${finalContent.length}`);
        } else {
            console.warn(`抓取失败: ${res.status}`);
        }
      } catch (e) {
        console.error("URL 抓取异常:", e);
      }
    }

    // ★★★ 优化 2: 智能长度截断与策略选择 ★★★
    // 设定阈值：如果清洗后的文本超过 8000 字符，可能导致输出截断
    const TEXT_LENGTH_THRESHOLD = 8000;
    const isTooLong = finalContent.length > TEXT_LENGTH_THRESHOLD;
    
    // 如果文章太长，我们截取前 15000 字发给 AI (用于提取元数据)，但我们保留 rawText 备用
    // 注意：DeepSeek V3 支持 64k/128k 上下文，这里可以适当放宽输入限制
    const inputForAI = finalContent.substring(0, 25000); 

    let providerConfig = PROVIDERS['openai']; 
    if (model.startsWith('deepseek')) providerConfig = PROVIDERS['deepseek'];
    else if (model.startsWith('qwen')) providerConfig = PROVIDERS['qwen'];

    const apiKey = Deno.env.get(providerConfig.key_env);
    if (!apiKey) throw new Error(`未配置 ${providerConfig.key_env} 环境变量`);

    // 准备 Prompt
    let finalSystemPrompt = systemPrompt || DEFAULT_PROMPTS[category] || DEFAULT_PROMPTS['news'];

    // ★★★ 优化 3: 动态 Prompt 调整 ★★★
    // 如果文章太长，告诉 AI 不要输出 content，或者只输出摘要和元数据
    // 这样可以避免输出 Token 溢出。
    if (isTooLong && category === 'policy') {
        console.log("文章过长，启用长文处理模式：AI仅提取元数据，正文使用原文。");
        finalSystemPrompt += "\n\n【特别注意】由于文章较长，JSON中的 'content' 字段请直接返回空字符串 (\"\")，不要输出正文，我将使用原文填充。请重点提取 title, summary, department, level 等元数据。";
    }

    // 调用 AI
    const aiResponse = await fetch(providerConfig.url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${apiKey}`
      },
      body: JSON.stringify({
        model: model, 
        messages: [
          { role: "system", content: finalSystemPrompt },
          { role: "user", content: `请基于以下内容生成数据：\n\n${inputForAI}` }
        ],
        temperature: 0.3
      })
    })

    const aiData = await aiResponse.json()
    if (aiData.error) throw new Error(`AI API Error: ${JSON.stringify(aiData.error)}`)

    const rawResult = aiData.choices[0].message.content;
    
    // 解析结果
    let parsedResult;
    try {
        parsedResult = JSON.parse(cleanJsonString(rawResult));
    } catch (e) {
        console.error("JSON 解析失败 (可能是被截断):", rawResult.substring(rawResult.length - 100));
        // 降级：解析失败也尽量返回一些信息
        parsedResult = { 
            title: "自动提取失败 (格式错误)", 
            summary: "AI 返回的数据格式不正确，可能是因为内容过长导致输出截断。",
            content: finalContent // 既然解析失败，直接把抓取的原文塞回去
        };
    }

    // ★★★ 优化 4: 结果回填逻辑 ★★★
    // 如果是长文模式（AI 返回的 content 是空的），或者解析失败，我们把抓取的 finalContent 塞进去
    if ((isTooLong && (!parsedResult.content || parsedResult.content.length < 100)) || !parsedResult.content) {
        parsedResult.content = finalContent; // 使用代码抓取的清洗版原文
    }

    // 确保 source_url 字段存在
    if (isUrlMode && !parsedResult.source_url) {
        parsedResult.source_url = content;
    }

    return new Response(JSON.stringify(parsedResult), {
      headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
    })

  } catch (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
    })
  }
})
