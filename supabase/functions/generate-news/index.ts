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
