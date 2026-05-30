(function() {
    // ================= 样式注入 (保持高科技感) =================
    const style = document.createElement('style');
    style.textContent = `
        /* 1. 悬浮球按钮 */
        #ai-widget-btn {
            position: fixed; bottom: 30px; right: 30px;
            width: 60px; height: 60px;
            background: linear-gradient(135deg, #3b82f6, #2563eb); /* 品牌蓝 */
            border-radius: 50%;
            box-shadow: 0 4px 20px rgba(59, 130, 246, 0.5);
            cursor: pointer; z-index: 9999;
            display: flex; align-items: center; justify-content: center;
            transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            animation: pulse-blue 2s infinite;
        }
        #ai-widget-btn:hover { transform: scale(1.1); }
        #ai-widget-btn svg { width: 32px; height: 32px; color: white; }

        /* 呼吸动画 */
        @keyframes pulse-blue {
            0% { box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.7); }
            70% { box-shadow: 0 0 0 10px rgba(59, 130, 246, 0); }
            100% { box-shadow: 0 0 0 0 rgba(59, 130, 246, 0); }
        }

        /* 2. 聊天窗口容器 */
        #ai-widget-window {
            position: fixed; bottom: 100px; right: 30px;
            width: 360px; height: 520px;
            background: white;
            border-radius: 16px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            display: none; /* 默认隐藏 */
            flex-direction: column;
            z-index: 9999; overflow: hidden;
            border: 1px solid #e2e8f0;
            transform-origin: bottom right;
            animation: expandUp 0.3s ease forwards;
        }
        @keyframes expandUp { 
            from { opacity:0; transform: scale(0.8) translateY(20px); } 
            to { opacity:1; transform: scale(1) translateY(0); } 
        }

        /* Header */
        .ai-header {
            background: #0f172a; color: white; padding: 16px 20px;
            display: flex; justify-content: space-between; align-items: center;
            border-bottom: 1px solid #1e293b;
        }
        .ai-title { font-weight: 700; display: flex; align-items: center; gap: 10px; font-size: 1rem; }
        .ai-status-dot { width: 8px; height: 8px; background: #10b981; border-radius: 50%; display: inline-block; }
        .ai-close { cursor: pointer; opacity: 0.6; font-size: 1.5rem; line-height: 1; transition: 0.2s; }
        .ai-close:hover { opacity: 1; color: #ef4444; }

        /* Body (消息区) */
        .ai-body { 
            flex: 1; padding: 20px; overflow-y: auto; 
            background: #f8fafc; 
            display: flex; flex-direction: column; gap: 15px; 
            scroll-behavior: smooth;
        }
        
        /* 消息气泡 */
        .msg { max-width: 85%; padding: 12px 16px; border-radius: 12px; font-size: 0.9rem; line-height: 1.6; word-wrap: break-word; position: relative; }
        .msg-bot { 
            align-self: flex-start; 
            background: white; 
            border: 1px solid #e2e8f0; 
            color: #334155; 
            border-top-left-radius: 2px; 
            box-shadow: 0 2px 5px rgba(0,0,0,0.02);
        }
        .msg-user { 
            align-self: flex-end; 
            background: #3b82f6; 
            color: white; 
            border-top-right-radius: 2px; 
            box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3);
        }

        /* Footer (输入区) */
        .ai-footer { padding: 15px; background: white; border-top: 1px solid #e2e8f0; display: flex; gap: 10px; align-items: center; }
        .ai-input { flex: 1; padding: 12px 15px; border: 1px solid #cbd5e1; border-radius: 25px; outline: none; font-size: 0.9rem; background: #f8fafc; transition: 0.3s; }
        .ai-input:focus { border-color: #3b82f6; background: white; box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1); }
        .ai-send { 
            width: 40px; height: 40px; border-radius: 50%; border: none; 
            background: #3b82f6; color: white; cursor: pointer; 
            display: flex; align-items: center; justify-content: center; 
            transition: 0.2s; 
        }
        .ai-send:hover { background: #2563eb; transform: scale(1.05); }
        .ai-send:disabled { background: #e2e8f0; color: #94a3b8; cursor: not-allowed; transform: none; }
        
        /* 移动端适配 */
        @media (max-width: 480px) {
            #ai-widget-window { width: 90%; right: 5%; bottom: 100px; height: 60vh; }
        }
    `;
    document.head.appendChild(style);

    // ================= HTML 结构 =================
    const html = `
        <div id="ai-widget-btn" title="咨询 AI 助手">
            <!-- 机器人图标 -->
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a2 2 0 0 1 2 2v2a2 2 0 0 1-2 2 2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z"></path><path d="M4 11v2a8 8 0 0 0 16 0v-2"></path><rect x="8" y="9" width="8" height="8" rx="1"></rect><path d="M9 14h6"></path></svg>
        </div>

        <div id="ai-widget-window">
            <div class="ai-header">
                <div class="ai-title">
                    <span class="ai-status-dot"></span> AeroBot 智能助手
                </div>
                <div class="ai-close" id="ai-close-btn">×</div>
            </div>
            <div class="ai-body" id="ai-messages">
                <!-- 欢迎语 -->
                <div class="msg msg-bot">
                    👋 您好！我是 AeroBot，低空经济领域智能助手。<br><br>
                    我可以回答关于<b>企业信息、政策法规、技术专利、融资动态、eVTOL产品</b>等问题。<br><br>
                    试试问我："亿航智能最近有什么融资？""深圳出台了哪些低空政策？"
                </div>
            </div>
            <div class="ai-footer">
                <input type="text" id="ai-input" class="ai-input" placeholder="输入问题 (功能暂未开放)...">
                <button id="ai-send" class="ai-send">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
                </button>
            </div>
        </div>
    `;
    
    const wrapper = document.createElement('div');
    wrapper.innerHTML = html;
    document.body.appendChild(wrapper);

    // ================= 交互逻辑 =================
    const btn = document.getElementById('ai-widget-btn');
    const win = document.getElementById('ai-widget-window');
    const closeBtn = document.getElementById('ai-close-btn');
    const input = document.getElementById('ai-input');
    const sendBtn = document.getElementById('ai-send');
    const msgBox = document.getElementById('ai-messages');

    btn.onclick = () => { win.style.display = win.style.display === 'flex' ? 'none' : 'flex'; };
    closeBtn.onclick = () => win.style.display = 'none';

    async function sendMessage() {
        const text = input.value.trim();
        if(!text) return;

        appendMsg(text, 'user');
        input.value = '';
        sendBtn.disabled = true;
        
        const loadingId = appendMsg('<span style="animation:blink 1s infinite">●●●</span>', 'bot');
        
        try {
            const resp = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text })
            });
            const data = await resp.json();
            document.getElementById(loadingId).remove();

            let replyHtml = data.reply || data.error || '服务异常，请稍后重试。';
            if (data.sources && data.sources.length > 0) {
                replyHtml += '<br><br><small style="color:#94a3b8;">📎 来源：';
                replyHtml += data.sources.map(s => s.title).join('、');
                replyHtml += '</small>';
            }
            appendMsg(replyHtml, 'bot');
        } catch (e) {
            document.getElementById(loadingId).remove();
            appendMsg('网络连接失败，请检查服务器是否启动。', 'bot');
        }
        sendBtn.disabled = false;
        input.focus();
    }

    function appendMsg(text, role) {
        const div = document.createElement('div');
        div.className = `msg msg-${role}`;
        div.id = 'msg-' + Date.now();
        div.innerHTML = text;
        msgBox.appendChild(div);
        msgBox.scrollTop = msgBox.scrollHeight;
        return div.id;
    }

    sendBtn.onclick = sendMessage;
    input.onkeypress = (e) => { if(e.key === 'Enter') sendMessage(); };
    input.placeholder = '问我低空经济相关问题...';
    input.disabled = false;
    sendBtn.disabled = false;
    
    const animStyle = document.createElement('style');
    animStyle.textContent = `@keyframes blink { 0% {opacity:0.2} 50% {opacity:1} 100% {opacity:0.2} }`;
    document.head.appendChild(animStyle);

})();
