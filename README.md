# 物流获客AI员工团队

物流行业智能获客系统，由6名专业AI员工组成的智能团队，覆盖内容创作、客户接待、意向分析的完整获客链路。

## 🤖 AI员工团队

| 员工 | 角色 | 职责 |
|------|------|------|
| **小调** | 调度主管 | 任务分配、流程协调、异常处理 |
| **小视** | 视频创作员 | 生成物流广告视频、产品展示视频 |
| **小文** | 文案策划 | 广告文案、朋友圈文案、视频脚本 |
| **小销** | 销售客服 | 首次接待、解答咨询、收集需求 |
| **小跟** | 跟进专员 | 老客户维护、意向客户跟进 |
| **小析** | 客户分析师 | 意向评分、客户画像、数据报表 |

## 🛠 技术栈

- **后端**: Python FastAPI
- **前端**: Next.js 14 + Tailwind CSS
- **数据库**: PostgreSQL
- **缓存**: Redis
- **AI**: Claude API / GPT-4
- **视频生成**: 可灵AI API
- **部署**: Docker + Nginx

## 📁 项目结构

```
物流获客AI/
├── backend/                 # FastAPI后端
│   ├── app/
│   │   ├── api/            # API路由
│   │   ├── agents/         # AI员工引擎
│   │   ├── core/           # 核心配置
│   │   ├── models/         # 数据模型
│   │   ├── schemas/        # Pydantic模型
│   │   └── services/       # 业务服务
│   └── requirements.txt
├── frontend/               # Next.js前端
│   ├── app/               # 页面
│   ├── components/        # 组件
│   └── lib/               # 工具库
├── database/              # 数据库脚本
├── docker-compose.yml     # Docker编排
└── nginx.conf             # Nginx配置
```

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone <repo-url>
cd 物流获客AI
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，填入你的API密钥
```

### 3. 使用Docker启动

```bash
docker-compose up -d
```

### 4. 访问系统

- 前端: http://localhost:80
- API文档: http://localhost:8000/api/docs

## ⚙️ 环境变量

| 变量 | 说明 |
|------|------|
| `POSTGRES_DB` | 数据库名 |
| `POSTGRES_USER` | 数据库用户 |
| `POSTGRES_PASSWORD` | 数据库密码 |
| `OPENAI_API_KEY` | OpenAI API密钥 |
| `ANTHROPIC_API_KEY` | Claude API密钥 |
| `KELING_API_KEY` | 可灵视频API密钥 |
| `WECHAT_CORP_ID` | 企业微信企业ID |
| `WECHAT_SECRET` | 企业微信密钥 |
| `COS_SECRET_ID` | 腾讯云COS密钥ID |
| `COS_SECRET_KEY` | 腾讯云COS密钥 |

## 📊 客户意向评分

| 行为 | 分数 |
|------|------|
| 主动询价 | +25 |
| 提供货物信息 | +20 |
| 询问时效/航线 | +15 |
| 多次互动(3次+) | +30 |
| 留下联系方式 | +50 |
| 表达合作意愿 | +40 |
| 只是随便问问 | -10 |

**意向等级**:
- S级 (80+分): 高意向，立即通知
- A级 (60-79分): 较高意向，重点跟进
- B级 (30-59分): 中等意向，定期跟进
- C级 (<30分): 低意向，存档

## 🎨 UI设计

采用赛博朋克高科技风格:
- 深色主题 + 霓虹色点缀
- 毛玻璃效果卡片
- 发光边框和动画效果
- Orbitron科技感字体

## 📝 开发说明

### 本地开发

```bash
# 后端
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# 前端
cd frontend
npm install
npm run dev
```

### 数据库迁移

```bash
# 初始化数据库
docker exec -i logistics-ai-db psql -U admin -d logistics_ai < database/init.sql
```

## 📄 License

MIT License
