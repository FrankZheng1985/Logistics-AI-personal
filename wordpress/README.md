# Sysafari Logistics WordPress网站

专业物流公司官网，DHL风格设计，与物流获客AI系统深度集成。

## 📁 项目结构

```
wordpress/
├── docker-compose.yml          # Docker开发环境配置
├── themes/
│   └── sysafari-logistics/     # 自定义主题
│       ├── style.css           # 主样式表 (DHL黄色主题)
│       ├── functions.php       # 主题函数
│       ├── header.php          # 页头模板
│       ├── footer.php          # 页脚模板
│       ├── front-page.php      # 首页模板
│       ├── page.php            # 默认页面模板
│       ├── single.php          # 文章详情模板
│       ├── index.php           # 博客列表模板
│       ├── 404.php             # 404错误页面
│       ├── page-tracking.php   # 货物追踪页面
│       ├── page-quote.php      # 报价请求页面
│       ├── page-services.php   # 服务介绍页面
│       ├── page-contact.php    # 联系我们页面
│       └── assets/
│           ├── css/
│           ├── js/
│           │   └── main.js     # 前端交互脚本
│           └── images/
├── plugins/
│   └── sysafari-logistics-integration/  # API对接插件
│       ├── sysafari-integration.php     # 插件主文件
│       ├── includes/
│       │   ├── class-api-client.php     # API客户端
│       │   ├── class-tracking.php       # 货物追踪
│       │   ├── class-quote.php          # 报价请求
│       │   └── class-customer-sync.php  # 客户同步
│       ├── admin/
│       │   └── views/                   # 管理后台视图
│       └── assets/
│           ├── css/admin.css
│           └── js/admin.js
└── uploads/                    # 媒体文件目录
```

## 🚀 快速开始

### 1. 启动本地开发环境

```bash
cd wordpress
docker-compose up -d
```

访问地址：
- WordPress: http://localhost:8080
- phpMyAdmin: http://localhost:8081

### 2. 初始配置

1. 访问 http://localhost:8080 完成WordPress安装向导
2. 登录后台 → 外观 → 主题 → 启用 "Sysafari Logistics"
3. 插件 → 已安装插件 → 启用 "Sysafari Logistics Integration"
4. 物流集成 → 设置 → 配置API连接

### 3. 创建页面

需要手动创建以下页面并选择对应模板：

| 页面名称 | 页面Slug | 页面模板 |
|---------|---------|---------|
| 货物追踪 | tracking | 货物追踪页面 |
| 获取报价 | quote | 获取报价页面 |
| 服务介绍 | services | 服务页面 |
| 联系我们 | contact | 联系我们页面 |

### 4. 配置导航菜单

外观 → 菜单 → 创建主导航菜单，添加以下页面：
- 追踪
- 寄件 (服务)
- 顾客服务
- 获取报价
- 关于我们
- 联系我们

## 🎨 设计风格

### 主色调

- **主色 (DHL黄)**: `#FFCC00`
- **辅助色 (DHL红)**: `#D40511`
- **深色文字**: `#333333`
- **浅灰背景**: `#F5F5F5`

### 响应式断点

- **桌面**: > 1024px
- **平板**: 768px - 1024px
- **手机**: < 768px

## 🔌 API对接

### 后端API端点

| 端点 | 方法 | 说明 |
|------|-----|------|
| `/api/website/tracking` | POST | 货物追踪查询 |
| `/api/website/quote-request` | POST | 提交报价请求 |
| `/api/website/services` | GET | 获取服务列表 |
| `/api/website/contact` | POST | 提交联系消息 |
| `/api/website/company-info` | GET | 获取公司信息 |

### 插件设置

在WordPress后台 → 物流集成 → 设置 中配置：

- **API基础URL**: 物流AI系统的API地址 (如 `http://localhost:8000/api/v1`)
- **API密钥**: 用于认证的密钥
- **功能开关**: 启用/禁用各项功能

## 📝 短代码

主题提供以下短代码：

```php
// 追踪表单
[sysafari_tracking title="追踪货件"]

// 报价表单
[sysafari_quote title="获取报价"]

// 服务卡片
[sysafari_services columns="3"]
```

## 🔧 自定义设置

在WordPress后台 → 外观 → 自定义 中可配置：

- **公司信息**: 名称、电话、邮箱、地址
- **API设置**: API地址和密钥
- **社交媒体**: 微信、微博、LinkedIn、Facebook链接

## 🚢 部署到生产环境

### 方案A: 与AI系统同服务器 (推荐)

```bash
# 在腾讯云服务器上
cd /home/ubuntu/logistics-ai/wordpress
docker-compose -f docker-compose.prod.yml up -d
```

### 方案B: 独立WordPress托管

1. 导出主题和插件文件
2. 上传到托管服务器 (如 SiteGround、阿里云虚拟主机)
3. 在WordPress后台安装主题和插件
4. 配置API连接

### 域名配置

1. 添加A记录指向服务器IP
2. 配置Nginx反向代理
3. 申请SSL证书 (推荐使用Let's Encrypt)

## 🔐 安全建议

1. 修改WordPress默认登录地址
2. 安装安全插件 (Wordfence)
3. 定期备份数据库
4. 使用强密码
5. 保持WordPress和插件更新

## 📊 推荐插件

- **Elementor**: 可视化页面构建
- **Contact Form 7**: 联系表单
- **Yoast SEO**: 搜索引擎优化
- **WP Super Cache**: 页面缓存
- **Wordfence**: 安全防护
- **WPML**: 多语言支持

## 📞 技术支持

如有问题，请联系开发团队或查看物流获客AI系统文档。
