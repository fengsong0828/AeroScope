import { serve } from "https://deno.land/std@0.168.0/http/server.ts"

// 定义模型提供商配置
const PROVIDERS = {
  // DeepSeek (高性价比)
  'deepseek': {
    url: 'https://api.deepseek.com/v1/chat/completions',
    key_env: 'DEEPSEEK_API_KEY'
  },
  // OpenAI (逻辑最强)
  'openai': {
    url: 'https://api.openai.com/v1/chat/completions',
    key_env: 'OPENAI_API_KEY'
  },
  // Qwen 通义千问 (兼容 OpenAI 协议)
  'qwen': {
    url: 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions',
    key_env: 'DASHSCOPE_API_KEY'
  }
}

// 系统提示词 (System Prompts)
const PROMPTS = {
  news: "你是一名低空经济产业分析师。请将用户输入的内容改写为一篇专业的行业新闻。要求：1. 标题简练有力。2. 摘要100字以内。3. 正文使用Markdown格式，逻辑清晰。返回JSON格式：{ title, summary, content }",
  
  policy: "你是一名政策解读专家。请分析用户提供的政策文件。要求：1. 标题格式为《XX政策》深度解读。2. 摘要指出对eVTOL行业的利好。3. 正文分点解读。返回JSON格式：{ title, summary, content }",
  
  tech: "你是一名航空技术工程师。请提取内容中的技术参数（续航、载重、电池密度等）。返回JSON格式：{ title, summary, content }",
  
  report: "你是一名FA财务顾问。请根据内容撰写简短的投研报告，包含市场分析与风险提示。返回JSON格式：{ title, summary, content }"
}

serve(async (req) => {
  // 1. 处理 CORS (允许前端跨域调用)
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: { 
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
    }})
  }

  try {
    const { content, model, category } = await req.json()

    // 2. 选择 API 提供商
    let providerConfig = PROVIDERS['openai']; // 默认
    
    if (model.startsWith('deepseek')) {
      providerConfig = PROVIDERS['deepseek'];
    } else if (model.startsWith('qwen')) {
      providerConfig = PROVIDERS['qwen'];
    }

    const apiKey = Deno.env.get(providerConfig.key_env);
    if (!apiKey) {
      throw new Error(`未配置 ${providerConfig.key_env} 环境变量 (请在 Supabase Secrets 中设置)`)
    }

    // 3. 准备 System Prompt
    const systemPrompt = PROMPTS[category] || PROMPTS['news'];

    // 4. 调用 AI API
    const aiResponse = await fetch(providerConfig.url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${apiKey}`
      },
      body: JSON.stringify({
        model: model, 
        messages: [
          { role: "system", content: systemPrompt },
          { role: "user", content: `请分析以下内容：\n${content}` }
        ],
        // 强制 JSON 返回 (大部分模型支持)
        response_format: { type: "json_object" }, 
        temperature: 0.7
      })
    })

    const aiData = await aiResponse.json()
    
    if (aiData.error) {
      throw new Error(`AI API Error: ${aiData.error.message || JSON.stringify(aiData)}`)
    }

    const rawContent = aiData.choices[0].message.content
    let parsedResult;
    try {
        parsedResult = JSON.parse(rawContent);
    } catch (e) {
        // 如果模型没返回标准JSON，尝试手动修复或直接返回文本
        parsedResult = { title: "解析错误", summary: "AI未返回标准JSON", content: rawContent };
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
