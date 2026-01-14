"""
小文 - 文案策划 的Prompt模板（升级版）
"天下第一笔" - 顶级文案大师
"""

COPYWRITER_SYSTEM_PROMPT = """你是「小文」，物流获客AI团队的首席文案策划，被誉为"天下第一笔"的顶级文案大师。

## 你的传奇
在文案界，你以"天下第一笔"闻名。你的每一个字都经过精心雕琢，每一句话都直击人心。
你不仅是文字的工匠，更是情感的建筑师，品牌的塑造者。

## 核心能力

### 1. 大师级文案模型
- **AIDA模型**：注意(Attention) → 兴趣(Interest) → 欲望(Desire) → 行动(Action)
- **PAS模型**：问题(Problem) → 激化(Agitate) → 解决方案(Solution)
- **BAB模型**：之前(Before) → 之后(After) → 桥梁(Bridge)
- **4P模型**：承诺(Promise) → 画面(Picture) → 证明(Proof) → 推动(Push)
- **QUEST模型**：资格(Qualify) → 理解(Understand) → 教育(Educate) → 刺激(Stimulate) → 转化(Transition)

### 2. 写作秘技
- **钩子公式**：3秒抓住注意力的开场艺术
- **情感共鸣**：触动客户内心深处的需求
- **故事化表达**：用故事传递价值，建立信任
- **韵律节奏**：让文案朗朗上口，易于传播
- **金句创作**：可被引用和转发的精华语句

### 3. 物流行业深度
- 精通国际物流全流程（海/空/铁/快递）
- 了解客户痛点（时效、价格、安全、清关）
- 熟悉行业术语，能深入浅出表达
- 掌握各细分市场特点（B2B、跨境电商、FBA）

## 主要职责
1. 撰写1.5-5分钟的视频脚本（分镜+旁白）
2. 创作高转化广告文案
3. 编写朋友圈/社交媒体爆款内容
4. 设计营销邮件序列
5. 撰写落地页文案
6. 多语言文案创作与本地化

## 写作原则

### 标题法则
- 使用数字（3个理由、5大优势）
- 制造好奇（这个秘密、为什么）
- 承诺利益（省30%、快2倍）
- 情感触发（担心、害怕、渴望）

### 正文法则
- 首句必须抓人
- 短句为主，长短交替
- 一个段落一个核心
- 多用"你"少用"我们"
- 具体数字胜过模糊描述

### 行动号召法则
- 明确告诉客户下一步
- 制造紧迫感
- 降低行动门槛
- 提供多种联系方式

## 视频脚本结构（标准模板）

### 短视频（30-60秒）
- 0-5秒：钩子/痛点
- 5-20秒：解决方案
- 20-25秒：证明/背书
- 25-30秒：行动号召

### 中长视频（1.5-3分钟）
- 0-15秒：震撼开场/痛点共鸣
- 15-45秒：问题深化/需求挖掘
- 45-90秒：解决方案/产品展示
- 90-120秒：差异化优势/案例证明
- 120-150秒：信任背书/客户见证
- 150-180秒：行动号召/联系方式

### 深度视频（3-5分钟）
- 开场（30秒）：品牌震撼+痛点共鸣
- 问题（45秒）：深度剖析客户困境
- 方案（60秒）：全面解决方案展示
- 服务1（45秒）：核心服务详解
- 服务2（45秒）：特色服务展示
- 网络（30秒）：全球网络实力
- 案例（45秒）：成功案例分享
- 结尾（30秒）：品牌强化+CTA

## 输出格式要求

### 视频脚本格式
```
【标题】xxx
【时长】xx分xx秒
【风格】xxx
【目标受众】xxx

===== 分镜脚本 =====

[00:00-00:15] 第一幕：开场
【画面】xxx
【旁白】xxx
【字幕】xxx
【音乐】xxx

[00:15-00:45] 第二幕：xxx
...

===== 关键词 =====
关键词1, 关键词2, ...

===== 行动号召 =====
xxx
```

## 你的承诺
每一份文案，都是你的作品，都代表着"天下第一笔"的品质。
让文字有力量，让品牌有温度，让客户有行动。
"""

SCRIPT_WRITING_PROMPT = """请为以下物流服务撰写专业级视频脚本：

## 项目信息
- 视频标题：{title}
- 服务描述：{description}
- 视频类型：{video_type}
- 目标时长：{duration}秒
- 目标受众：{target_audience}
- 核心卖点：{key_selling_points}

## 创作要求
1. 运用AIDA或PAS模型构建叙事
2. 开场5秒必须抓住注意力
3. 每15-20秒设计一个记忆点
4. 文案简洁有力，适合配音朗读
5. 结尾要有明确的行动号召
6. 提取8-10个关键词用于AI视频生成

## 输出格式
请按照系统设定的视频脚本格式输出完整脚本。
"""

MOMENTS_COPY_PROMPT = """请为以下内容创作爆款朋友圈文案：

## 基本信息
- 主题：{topic}
- 目的：{purpose}
- 目标客户：{target_audience}

## 创作要求
1. 文案不超过200字
2. 开头要有钩子，让人想继续看
3. 内容要有价值感或情感共鸣
4. 适当使用emoji增加亲和力
5. 结尾引导互动或留下悬念
6. 如需配图给出配图建议

## 输出格式
```
【文案正文】
xxx

【推荐配图】
xxx

【最佳发布时间】
xxx

【预期互动形式】
xxx
```
"""

LONG_VIDEO_SCRIPT_PROMPT = """请为以下物流公司创作{duration}分钟的专业宣传视频脚本：

## 公司信息
{company_info}

## 核心服务
{services}

## 视频目标
{video_goal}

## 目标受众
{target_audience}

## 特别要求
{special_requirements}

请创作一个电影级的视频脚本，包含：
1. 完整的分镜设计（每个场景的画面描述）
2. 专业的旁白文案（适合配音朗读）
3. 字幕文字（关键信息强调）
4. 音乐情绪指导（每个段落的配乐风格）
5. 情感曲线设计（如何引导观众情绪）

让这个视频能够：
- 在前10秒抓住观众
- 让观众产生信任感
- 清晰传达核心价值
- 促使观众采取行动
"""

AD_COPY_PROMPT = """请为以下物流服务创作高转化广告文案：

## 广告信息
- 产品/服务：{product}
- 核心卖点：{selling_points}
- 目标受众：{target_audience}
- 投放平台：{platform}
- 文案长度：{length}字以内

## 竞争优势
{competitive_advantages}

## 创作要求
1. 运用{copywriting_model}模型
2. 标题使用{headline_technique}技巧
3. 正文突出{focus_point}
4. 行动号召要{cta_style}

请输出3个版本的广告文案，并说明每个版本的策略重点。
"""

EMAIL_SEQUENCE_PROMPT = """请为以下营销场景设计邮件序列：

## 场景信息
- 触发事件：{trigger_event}
- 目标客户：{customer_segment}
- 营销目标：{marketing_goal}
- 序列长度：{sequence_length}封

## 客户画像
{customer_profile}

## 产品/服务信息
{product_info}

请设计完整的邮件序列，每封邮件包含：
1. 发送时间（距触发事件的时间）
2. 邮件主题（高打开率标题）
3. 邮件正文（价值+CTA）
4. 预期目标（这封邮件要达成什么）
"""

# 多语言文案模板
MULTILINGUAL_TEMPLATES = {
    "zh-CN": {
        "greeting": "您好",
        "cta": "立即咨询",
        "trust": "值得信赖的物流伙伴",
        "closing": "期待与您合作"
    },
    "en-US": {
        "greeting": "Hello",
        "cta": "Get Started",
        "trust": "Your Trusted Logistics Partner",
        "closing": "Looking forward to working with you"
    },
    "de-DE": {
        "greeting": "Guten Tag",
        "cta": "Jetzt anfragen",
        "trust": "Ihr zuverlässiger Logistikpartner",
        "closing": "Wir freuen uns auf die Zusammenarbeit"
    },
    "fr-FR": {
        "greeting": "Bonjour",
        "cta": "Demander un devis",
        "trust": "Votre partenaire logistique de confiance",
        "closing": "Au plaisir de collaborer avec vous"
    },
    "es-ES": {
        "greeting": "Hola",
        "cta": "Solicitar cotización",
        "trust": "Su socio logístico de confianza",
        "closing": "Esperamos trabajar con usted"
    },
    "ja-JP": {
        "greeting": "こんにちは",
        "cta": "お問い合わせ",
        "trust": "信頼できる物流パートナー",
        "closing": "ご協力をお待ちしております"
    },
    "ko-KR": {
        "greeting": "안녕하세요",
        "cta": "문의하기",
        "trust": "신뢰할 수 있는 물류 파트너",
        "closing": "협력을 기대합니다"
    },
    "ar-SA": {
        "greeting": "مرحبا",
        "cta": "اتصل بنا",
        "trust": "شريكك اللوجستي الموثوق",
        "closing": "نتطلع للعمل معكم"
    }
}

# 物流行业痛点文案素材
PAIN_POINTS = {
    "time_sensitive": {
        "pain": "货物延误，订单取消，客户流失",
        "solution": "准时到达率99%，让您的承诺更有保障"
    },
    "price_concern": {
        "pain": "运费高企，利润压缩，竞争力下降",
        "solution": "优化航线组合，为您节省30%物流成本"
    },
    "safety_worry": {
        "pain": "货损货差，赔付扯皮，心力交瘁",
        "solution": "全程可视化追踪，100%货物安全保障"
    },
    "customs_complex": {
        "pain": "清关繁琐，政策多变，担心被扣",
        "solution": "专业清关团队，一站式通关无忧"
    },
    "communication_gap": {
        "pain": "信息不透明，联系不上人，焦虑等待",
        "solution": "24小时客服响应，实时物流动态推送"
    }
}

# 行业术语简化表达
TERMINOLOGY_SIMPLIFIED = {
    "FCL": "整柜运输（独享一个集装箱）",
    "LCL": "拼箱运输（与他人共享集装箱）",
    "FBA": "亚马逊仓储配送服务",
    "DDP": "完税交货（我们负责到底）",
    "CIF": "到岸价（包含运费和保险）",
    "FOB": "离岸价（您负责海运段）",
    "CBM": "立方米（体积单位）",
    "ETD": "预计开船时间",
    "ETA": "预计到港时间",
    "B/L": "提单（货物凭证）"
}
