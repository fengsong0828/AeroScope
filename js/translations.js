
// AeroScope Insight Translation Map
// 中文映射字典与转义工具

const TRANSLATION_MAP = {
    // 产业链位置 (Upstream/Midstream/Downstream)
    'upstream': '上游供应链',
    'midstream': '整机制造',
    'downstream': '下游应用',
    'infrastructure': '基础设施',

    // 适航状态 (Certified, etc.)
    'certified': '已取证',
    'testing': '试飞中',
    'tc_application': 'TC受理',
    'tc_issued': 'TC颁发',
    'pc_issued': 'PC颁发',
    'oc_issued': 'OC颁发',
    'demonstrator': '验证机',
    'prototype': '原型机',
    'concept': '概念阶段',
    'tc granted': 'TC已取证',
    'authorized': '已授权',
    'terminated': '失效',
    'valid': '有效',
    'invalid': '无效',

    // 产品类型
    'evtol': 'eVTOL', 
    'drone': '无人机', // Admin Schema use 'Drone'
    'multicopter': '多旋翼',
    'vectored_thrust': '矢量推力',
    'vectored thrust': '矢量推力', // 兼容空格
    'lift_cruise': '复合翼',
    'lift+cruise': '复合翼',       // 兼容加号
    'fixed_wing': '固定翼',
    'fixed wing': '固定翼',
    'flyingcar': '飞行汽车',
    'helicopter': '直升机',
    'uav': '无人机',
    'service': '运营服务',

    // 动力与驾驶
    'electric': '纯电',
    'hybrid': '混动',
    'hydrogen': '氢能',
    'autonomous': '自动驾驶',
    'piloted': '有人驾驶',
    
    // 专利类型
    'utility model': '实用新型',
    'invention': '发明专利',
    'design': '外观设计',
    'patent': '专利',
    'paper': '学术论文',
    'product': '产品发布',
    
    // 技术领域
    'battery': '电池技术',
    'propulsion': '动力系统',
    'avionics': '航空电子',
    'materials': '复合材料',
    'regulation': '适航法规',
    'infrastructure': '基础设施',
    'ai': '人工智能',
    'safety': '安全系统',
    'flight_control': '飞控系统',
    'communication': '通信技术',
    'navigation': '导航技术',
    'energy': '能源管理',

    // 常见状态
    'active': '运营中',
    'inactive': '已停运',
    'draft': '草稿',
    'published': '已发布',
    'pending': '待处理',
    'contacted': '已联系',
    'closed': '已关闭',

    // 融资轮次
    'seed': '种子轮',
    'angel': '天使轮',
    'angel round': '天使轮',
    'pre-a': 'Pre-A轮',
    'series a': 'A轮',
    'series b': 'B轮',
    'series c': 'C轮',
    'series d': 'D轮',
    'series e': 'E轮',
    'pre-ipo': '上市前',
    'ipo': '上市',
    'strategic': '战略融资',
    'm&a': '并购',
    'private equity': '私募股权',
    'grant': '政府补助',
    'debt': '债务融资',
    'crowdfunding': '众筹',
    'undisclosed': '未披露',

    // 投资方类型
    'vc': '风险投资',
    'pe': '私募股权',
    'cvc': '企业创投',
    'angel_investor': '天使投资人',
    'government': '政府基金',
    'accelerator': '加速器',
    'family_office': '家族办公室',
    'bank': '银行',

    // 资讯分类 (News Categories)
    'market': '市场动态',
    'Market': '市场动态',
    'policy': '政策法规',
    'Policy': '政策法规',
    'capital': '资本融资',
    'Capital': '资本融资',
    'global': '全球',
    'Global': '全球',
    'technology': '技术前沿',
    'Technology': '技术前沿',
    'view': '观点',
    'View': '观点',
    'interview': '专访',
    'Interview': '专访',
    'company': '公司动态',
    'Company': '公司动态',
    
    // 政策层级
    'national': '国家部委',
    'provincial': '省市地方',
    'local': '地方政府',
    'international': '国际组织',
    'ministry': '部委规章',
    
    // 政策部门
    'caac': '中国民航局',
    'easa': '欧洲航空安全局',
    'faa': '美国联邦航空局',
    'miit': '工信部',
    'mot': '交通运输部',
    'ndrc': '发改委',
    'mof': '财政部',
    'samr': '市场监管总局',
    'state council': '国务院',

    // 地区
    'china': '中国',
    'cn': '中国',
    'usa': '美国',
    'us': '美国',
    'europe': '欧洲',
    'eu': '欧洲',
    'germany': '德国',
    'de': '德国',
    'uk': '英国',
    'gb': '英国',
    'france': '法国',
    'fr': '法国',
    
    // 价值评估与等级
    'high': '高',
    'medium': '中',
    'low': '低',
    'available': '可许可',
    'exclusive': '独家许可',
    'negotiable': '面议',
    'licensed': '已许可',

    // Admin / 通用
    'title': '标题',
    'date': '日期',
    'type': '类型',
    'status': '状态',
    'action': '操作',
    'edit': '编辑',
    'delete': '删除',
    'save': '保存',
    'cancel': '取消',
    'search': '搜索',
    'view': '查看',
};

/**
 * 翻译转换函数
 * @param {string} key - 英文 Key (数据库值)
 * @returns {string} - 对应的中文 Value，如果未找到则返回原值
 */
function t(key) {
    if (!key) return '';
    // 尝试匹配全小写 Key (忽略大小写差异)
    const lowerKey = String(key).trim().toLowerCase();
    
    if (TRANSLATION_MAP[lowerKey]) {
        return TRANSLATION_MAP[lowerKey];
    }
    
    // 如果没有精确匹配，尝试部分通用规则或返回原值
    return key;
}

// 导出供全局使用
window.t = t;
window.TRANSLATION_MAP = TRANSLATION_MAP;
