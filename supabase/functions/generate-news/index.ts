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

// 默认兜底提示词 (如果前端没传 customPrompt，用这个)
// 这里的结构必须与前端需要的字段对齐
const DEFAULT_PROMPTS = {
  news: "你是一名产业分析师。将输入内容改写为新闻。返回JSON: { title, summary, content, tags:[], category }",
  policy: "你是一名政策专家。分析政策文件。提取部门、层级、日期。返回JSON: { title, summary, content, department, level, publish_date, related_city, tags:[] }",
  tech: "你是技术专家。提取技术参数。返回JSON: { title, summary, content, type, org, tags:[] }",
  report: "你是分析师。撰写研报摘要。返回JSON: { title, summary, content, tags:[] }"
}

// 辅助函数：简单的 HTML 文本提取 (去除标签和样式)
function extractTextFromHtml(html: string): string {
  // 1. 去除脚本和样式
  let text = html.replace(/<script[^>]*>([\s\S]*?)<\/script>/gmi, "");
  text = text.replace(/<style[^>]*>([\s\S]*?)<\/style>/gmi, "");
  // 2. 去除 HTML 标签
  text = text.replace(/<[^>]+>/g, "\n");
  // 3. 处理多余空行和空白
  text = text.replace(/\n\s*\n/g, "\n").trim();
  // 4. 截取前 15000 个字符 (避免爆 Token)
  return text.substring(0, 15000);
}

// 辅助函数：清洗 AI 返回的 JSON 字符串 (去除 Markdown 标记)
function cleanJsonString(str: string): string {
  // 去除 ```json 和 ``` 
  return str.replace(/^```json\s*/, "").replace(/^```\s*/, "").replace(/\s*```$/, "");
}

serve(async (req) => {
  // 1. 处理 CORS
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: { 
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
    }})
  }

  try {
    // 获取前端传来的参数，增加了 systemPrompt
    const { content, model, category, systemPrompt } = await req.json()

    // 2. 判断 content 是否为 URL，如果是则进行抓取
    let finalContent = content;
    const urlRegex = /^(http|https):\/\/[^ "]+$/;
    
    if (urlRegex.test(content)) {
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
            console.log(`抓取成功，提取文本长度: ${finalContent.length}`);
        } else {
            console.warn(`抓取失败: ${res.status}`);
            // 如果抓取失败，依然把 URL 给 AI，让 AI 尝试（有些模型能联网，或者依靠 URL 猜测）
        }
      } catch (e) {
        console.error("URL 抓取异常:", e);
      }
    }

    // 3. 选择 API 提供商
    let providerConfig = PROVIDERS['openai']; 
    if (model.startsWith('deepseek')) providerConfig = PROVIDERS['deepseek'];
    else if (model.startsWith('qwen')) providerConfig = PROVIDERS['qwen'];

    const apiKey = Deno.env.get(providerConfig.key_env);
    if (!apiKey) throw new Error(`未配置 ${providerConfig.key_env} 环境变量`);

    // 4. 确定 System Prompt (优先使用前端传来的 customPrompt)
    const finalSystemPrompt = systemPrompt || DEFAULT_PROMPTS[category] || DEFAULT_PROMPTS['news'];

    // 5. 调用 AI API
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
          { role: "user", content: `请基于以下内容生成数据：\n\n${finalContent}` }
        ],
        // DeepSeek V3 和 Qwen Max 对 JSON 模式支持较好，但为了兼容性，不在 body 强加 response_format
        // 而是依靠 Prompt 中的 "请输出 JSON" 指令
        temperature: 0.3 // 降低温度，让 JSON 格式更稳定
      })
    })

    const aiData = await aiResponse.json()
    
    if (aiData.error) {
      throw new Error(`AI API Error: ${JSON.stringify(aiData.error)}`)
    }

    const rawResult = aiData.choices[0].message.content;
    
    // 6. 鲁棒的 JSON 解析
    let parsedResult;
    try {
        const cleanedJson = cleanJsonString(rawResult);
        parsedResult = JSON.parse(cleanedJson);
    } catch (e) {
        console.error("JSON 解析失败，原始返回:", rawResult);
        // 降级处理：如果解析失败，将原始内容放入 content
        parsedResult = { 
            title: "AI 生成格式错误", 
            summary: "请手动检查正文内容", 
            content: rawResult,
            tags: ["格式错误"]
        };
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
