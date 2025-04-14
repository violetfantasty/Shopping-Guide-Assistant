# 🎁 智能话术生成平台（基于FastAPI + Gradio + 大模型）

## 📘 项目简介

本项目构建了一个集成 **FastAPI** 后端服务与 **Gradio** 前端交互界面的话术自动生成平台。项目结合了 **NVIDIA OpenAI 接口** 提供的大语言模型能力，实现针对三类业务场景的智能内容生成：

- 🎂 会员生日祝福
- 🌦️ 门店天气提醒
- 🎉 节日祝福推送

此外，项目还集成了异步MySQL数据库、实时天气接口以及大模型推理服务，具备较强的拓展性与实用性。

---

## 🔧 技术架构

- **后端框架**：FastAPI（异步接口）
- **前端界面**：Gradio（低代码交互）
- **大模型服务**：NVIDIA OpenAI API（qwen/qwen2.5-7b-instruct & qwq-32b）
- **数据库支持**：aiomysql（MySQL异步连接池）
- **HTTP客户端**：httpx（异步请求天气信息）
- **部署方式**：Uvicorn ASGI 服务

---

## 📦 功能模块说明

### 模式 0：生日祝福生成
- 根据会员编码（手机号）从数据库中查询 `姓名、性别、生日`
- 自动结合会员信息、当前日期与可选补充信息生成个性化生日祝福
- 内容可适配年龄性别偏好，加入 emoji、美化语言表达

### 模式 1：天气提醒生成
- 根据门店编码从数据库中获取对应的 `城市行政编码`
- 调用彩云天气 API 获取当前天气预警要点
- 自动生成具备安全、健康、出行提醒的个性化话术

### 模式 2：节日祝福生成
- 根据会员编码查询基础信息，结合用户输入的节日名称
- 自动分析节日风格与顾客特征，生成带节日氛围与emoji的祝福内容
- 支持无节日名称时默认生成近期节日问候

---

## 💡 系统流程图（简化）

```
Gradio界面输入
    │
    ▼
FastAPI 接口（/script）
    │
    ├─ 查询 MySQL 数据库
    ├─ 请求天气接口（如有）
    └─ 拼接 Prompt 给大模型
        │
        ▼
    大语言模型服务（Qwen）
        │
        ▼
   返回生成文本
        │
        ▼
Gradio 显示生成结果
```

---

## 📁 项目结构说明

```bash
├── main.py              # FastAPI 主程序，含所有业务逻辑和接口路由
├── gradio_ui.py         # Gradio 前端交互界面逻辑
├── requirements.txt     # 依赖包列表
├── README.md            # 项目说明文档（本文件）
└── .env / config        # API Key、数据库等敏感配置（建议使用环境变量管理）
```

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

或手动安装核心依赖：

```bash
pip install fastapi uvicorn httpx aiomysql openai pydantic gradio
```

### 2. 启动后端服务

```bash
python main.py
```

### 3. 启动 Gradio UI

```bash
python gradio_ui.py
```

访问地址通常为：`http://localhost:7860`（或控制台提示的URL）

---

## 🔐 环境变量说明（重要）

请配置以下环境变量或使用 `.env` 文件：

```bash
OPENAI_API_KEY=你的大模型API密钥
OPENAI_BASE_URL=https://integrate.api.nvidia.com/v1
MYSQL_HOST=数据库主机地址
MYSQL_USER=用户名
MYSQL_PASSWORD=密码
MYSQL_DB=数据库名
```

---

## 📌 注意事项

- 天气功能依赖彩云天气API，接口中已写入Key（测试用），若大规模部署建议申请商用Key
- 若大模型调用失败，请检查 `API Key` 与网络代理配置
- MySQL 数据库需预先建好以下表结构：
  - `ads_members_information(mem_code, real_name, sex, birthday)`
  - `new_shop_channel_expanding(shop_code, city)`

---

## 🧠 项目亮点与技术思考

1. **Prompt 设计具备高可控性**，通过明确的步骤和提示指令，增强生成内容的可解释性与一致性。
2. **异步架构保障响应速度**，即使数据库请求与大模型调用并发执行也能快速返回。
3. **多模态交互入口**，Gradio 接口可拓展为 Web H5、小程序或客服系统入口。
4. **可拓展性强**，未来可接入更多场景（如营销推荐语、投诉处理话术等），或支持多语言翻译等扩展功能。
