"""
AeroScope 专利技术分类与产业链划分规则
低空经济专利分类体系 v2.0
参考: 雪球《低空经济产业链全景深度解析》
"""

# ============================================================
# 一、技术分类体系 (technical_categories) —— 一级分类 + 二级子类
# ============================================================
TECH_CATEGORIES = {
    "飞行器构型设计": {
        "sub": ["多旋翼技术", "复合翼技术", "倾转旋翼技术", "涵道风扇技术",
                "气动外形设计", "结构轻量化", "飞行汽车构型"],
        "keywords": ["多旋翼", "复合翼", "倾转旋翼", "涵道风扇", "气动外形",
                      "轻量化", "构型", "飞行汽车", "垂直起降", "VTOL", "eVTOL",
                      "multicopter", "tiltrotor", "ducted fan", "airframe"]
    },
    "动力系统": {
        "sub": ["动力电池", "高能量密度电池", "固态电池", "快充技术",
                "电池管理系统BMS", "电机系统", "永磁同步电机", "轮毂电机",
                "电机控制算法", "混合动力系统", "氢燃料电池"],
        "keywords": ["动力电池", "固态电池", "快充", "BMS", "电池管理", "电机",
                      "永磁同步", "轮毂电机", "混合动力", "氢燃料", "能量密度",
                      "动力系统", "推进系统", "battery", "motor", "propulsion",
                      "fuel cell", "energy storage", "PMSM"]
    },
    "飞行控制与导航": {
        "sub": ["飞控系统", "自主飞行", "导航定位", "避障感知",
                "冗余控制", "姿态控制", "轨迹规划"],
        "keywords": ["飞控", "飞行控制", "自主飞行", "自动驾驶", "导航", "定位",
                      "避障", "感知", "冗余", "姿态", "轨迹", "flight control",
                      "autonomous", "navigation", "obstacle avoidance", "sense and avoid"]
    },
    "通信与数据链": {
        "sub": ["低空通信", "5G/ATG通信", "卫星通信", "数据链技术", "频谱管理"],
        "keywords": ["通信", "数据链", "5G", "ATG", "卫星通信", "频谱", "低空通信",
                      "地面站", "通信链路", "communication", "data link",
                      "telemetry", "C2 link"]
    },
    "材料与制造工艺": {
        "sub": ["碳纤维复合材料", "钛合金", "铝合金", "航空涂料", "3D打印制造"],
        "keywords": ["碳纤维", "复合材料", "钛合金", "铝合金", "涂料", "3D打印",
                      "增材制造", "composite", "carbon fiber", "titanium",
                      "aluminum", "additive manufacturing"]
    },
    "航电系统": {
        "sub": ["综合航电", "座舱显示", "传感器系统", "健康管理PHM"],
        "keywords": ["航电", "座舱", "传感器", "健康管理", "PHM", "avionics",
                      "cockpit", "sensor", "prognostics"]
    },
    "空中交通管理": {
        "sub": ["空管系统UTM", "低空航路规划", "冲突检测与解决", "空域管理"],
        "keywords": ["空管", "UTM", "航路", "冲突", "空域", "流量管理",
                      "空中交通", "ATM", "air traffic", "UTM", "U-space",
                      "conflict detection"]
    },
    "适航与检测": {
        "sub": ["适航审定", "飞行测试", "可靠性测试", "环境适应性测试"],
        "keywords": ["适航", "审定", "飞行测试", "可靠性", "环境试验",
                      "airworthiness", "certification", "flight test", "reliability"]
    },
    "运营与应用技术": {
        "sub": ["物流配送", "载人交通", "巡检监测", "应急救援", "农业植保"],
        "keywords": ["物流", "配送", "载人", "巡检", "监测", "应急", "救援",
                      "植保", "喷洒", "logistics", "delivery", "inspection",
                      "emergency", "agricultural"]
    },
    "基础设施": {
        "sub": ["起降场设计", "充电换电设施", "气象监测", "反无人机系统",
                "低空监视设施"],
        "keywords": ["起降", "停机坪", "充电", "换电", "气象", "反无人机",
                      "监视", "vertiport", "charging", "weather", "counter-drone",
                      "surveillance"]
    },
    "其他-待审核": {
        "sub": ["待分类"],
        "keywords": []
    }
}

# ============================================================
# 二、产业链划分 (industry_chain_position) —— 6个细分环节
# ============================================================
INDUSTRY_CHAIN = {
    "上游-原材料": {
        "desc": "钛合金、碳纤维复合材料、铝合金、航空涂料等材料供应商",
        "keywords": ["钛合金", "碳纤维", "复合材料", "铝合金", "涂料", "原材料",
                      "titanium", "carbon fiber", "aluminum", "composite material",
                      "coating", "paint"]
    },
    "上游-核心零部件": {
        "desc": "电池、电机、电控、芯片、传感器、起落架、结构件等核心部件制造商",
        "keywords": ["电池", "电机", "电控", "芯片", "传感器", "起落架", "结构件",
                      "零部件", "核心部件", "battery", "motor", "actuator", "chip",
                      "landing gear", "structural", "component"]
    },
    "中游-分系统": {
        "desc": "动力系统、航电系统、飞控系统、导航系统、通信系统等子系统集成商",
        "keywords": ["航电", "飞控", "导航", "通信", "动力系统", "推进系统",
                      "avionics", "flight control", "navigation", "communication",
                      "propulsion", "subsystem"]
    },
    "中游-整机制造": {
        "desc": "eVTOL整机、无人机整机、飞行汽车等终端飞行器制造商",
        "keywords": ["eVTOL", "无人机", "飞行器", "飞行汽车", "整机", "总装",
                      "aircraft", "drone", "flying car", "VTOL", "UAV", "UAM"]
    },
    "下游-运营服务": {
        "desc": "低空物流、低空旅游、载人交通、巡检救援、农业植保等运营服务商",
        "keywords": ["物流", "配送", "旅游", "载人", "巡检", "救援", "植保",
                      "运营", "服务", "logistics", "delivery", "tourism",
                      "inspection", "rescue", "agriculture", "operation"]
    },
    "下游-飞行保障": {
        "desc": "空管系统、飞行审批、飞行培训、检测检验、维修保障等服务商",
        "keywords": ["空管", "审批", "培训", "检测", "检验", "维修", "保障",
                      "air traffic", "training", "testing", "maintenance",
                      "MRO", "certification"]
    },
    "其他-待审核": {
        "desc": "无法确定产业链位置的专利，供人工审核",
        "keywords": []
    }
}

# ============================================================
# 三、应用场景分类 (application_fields) —— 12个标准场景
# ============================================================
APP_FIELDS = [
    ("城市空中交通", ["UAM", "城市空中", "空中交通", "air taxi", "urban air mobility"]),
    ("低空物流配送", ["物流", "配送", "快递", "货运", "logistics", "delivery", "cargo", "freight"]),
    ("应急救援", ["应急", "救援", "救灾", "救护", "emergency", "rescue", "disaster"]),
    ("医疗运输", ["医疗", "血", "器官", "药品", "medical", "organ", "pharmaceutical", "ambulance"]),
    ("旅游观光", ["旅游", "观光", "游览", "景区", "tourism", "sightseeing"]),
    ("农业植保", ["植保", "农业", "农药", "喷洒", "施肥", "agriculture", "spray", "crop"]),
    ("巡检测绘", ["巡检", "检测", "测绘", "电力", "管道", "inspection", "survey", "mapping"]),
    ("消防灭火", ["消防", "灭火", "防火", "fire", "firefighting"]),
    ("安防监控", ["安防", "监控", "安保", "治安", "security", "surveillance", "monitoring"]),
    ("环境保护", ["环境", "污染", "监测", "生态", "environmental", "pollution", "ecology"]),
    ("科学考察", ["科研", "考察", "科考", "勘探", "scientific", "exploration", "research"]),
    ("载人交通", ["载人", "客运", "出行", "通勤", "passenger", "transport", "commute", "mobility"]),
    ("其他-待审核", [])
]

# ============================================================
# 四、创新等级 (innovation_level)
# ============================================================
INNOVATION_LEVELS = {
    "High": {
        "desc": "原创性技术突破，核心专利，高引用，首创",
        "indicators": ["首创", "突破", "原创", "发明", "首次", "first", "breakthrough", "novel"]
    },
    "Medium": {
        "desc": "改进性创新，在现有技术基础上的优化",
        "indicators": ["改进", "优化", "提升", "增强", "improved", "optimized", "enhanced"]
    },
    "Low": {
        "desc": "应用性/适应性创新，技术迁移或简单改造",
        "indicators": ["应用", "适用", "改造", "移植", "application", "adaptation", "modified"]
    }
}

# ============================================================
# 五、技术成熟度 TRL (technology_maturity_level)
# ============================================================
TRL_LEVELS = {
    1: "基础原理发现",
    2: "技术概念/应用设想",
    3: "概念验证与可行性分析",
    4: "实验室环境验证",
    5: "相关环境验证",
    6: "相关环境演示",
    7: "操作环境演示",
    8: "系统完成与认证",
    9: "实际运行验证"
}

# ============================================================
# 六、辅助函数
# ============================================================
def get_all_tech_categories():
    """返回所有一级技术分类名称列表"""
    return list(TECH_CATEGORIES.keys())

def get_all_tech_subcategories():
    """返回所有二级技术子类列表"""
    result = []
    for cat, info in TECH_CATEGORIES.items():
        for sub in info["sub"]:
            result.append(sub)
    return result

def get_all_chain_positions():
    """返回所有产业链环节"""
    return list(INDUSTRY_CHAIN.keys())

def get_all_app_fields():
    """返回所有应用场景"""
    return [f[0] for f in APP_FIELDS]

def get_tech_category_by_sub(sub_name):
    """根据二级子类反查一级分类"""
    for cat, info in TECH_CATEGORIES.items():
        if sub_name in info["sub"]:
            return cat
    return None

def match_keywords_to_categories(text):
    """基于关键词简单匹配技术分类（用于预筛，并非最终分类）"""
    text_lower = text.lower() if text else ""
    matched = []
    for cat, info in TECH_CATEGORIES.items():
        if cat == "其他-待审核":
            continue
        for kw in info["keywords"]:
            if kw.lower() in text_lower:
                matched.append(cat)
                break
    return list(set(matched))

def match_keywords_to_chain(text):
    """基于关键词简单匹配产业链位置"""
    text_lower = text.lower() if text else ""
    for pos, info in INDUSTRY_CHAIN.items():
        if pos == "其他-待审核":
            continue
        for kw in info["keywords"]:
            if kw.lower() in text_lower:
                return pos
    return "其他-待审核"

def match_keywords_to_app(text):
    """基于关键词简单匹配应用场景"""
    text_lower = text.lower() if text else ""
    matched = []
    for field_name, keywords in APP_FIELDS:
        if field_name == "其他-待审核":
            continue
        for kw in keywords:
            if kw.lower() in text_lower:
                matched.append(field_name)
                break
    return list(set(matched)) if matched else ["其他-待审核"]


if __name__ == "__main__":
    print("技术分类一级:", get_all_tech_categories())
    print("产业环节:", get_all_chain_positions())
    print("应用场景:", get_all_app_fields())
