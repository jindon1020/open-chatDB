# OpenChatDB

开源的 AI 数据库客户端，通过自然语言与数据库对话，自动生成并执行查询语句。支持 MySQL、MongoDB、Elasticsearch。

## 功能特性

- **AI 对话生成查询** — 用自然语言描述需求，AI 自动生成 SQL / MongoDB / Elasticsearch 查询语句，可一键执行
- **多数据库支持** — MySQL、MongoDB、Elasticsearch，统一的操作界面
- **数据库浏览** — 树形结构浏览连接、数据库、表/集合/索引，查看表结构与数据
- **查询编辑器** — 手动编写并执行查询，支持结果表格展示
- **智能引用** — 在对话中使用 `@表名` 和 `#字段名` 快速引用，支持自动补全
- **写操作保护** — 自动识别 INSERT/UPDATE/DELETE 等写操作，执行前需二次确认
- **SSH 隧道** — 支持通过 SSH 隧道连接远程数据库
- **连接管理** — 保存、编辑、测试数据库连接配置
- **深色/浅色主题** — 支持主题切换
- **兼容多种 LLM** — 支持任何 OpenAI 兼容接口（OpenAI、通义千问、DeepSeek、本地模型等）

## 快速开始

### 环境要求

- Python 3.10+

### 安装

```bash
git clone https://github.com/jindon1020/open-chatDB.git
cd open-chatDB
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 配置

在项目根目录创建 `.env` 文件：

```env
LLM_API_KEY=your-api-key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o
LLM_MAX_TOKENS=4096
LLM_TEMPERATURE=0
FLASK_SECRET_KEY=your-secret-key
```

**LLM 配置示例：**

| 提供商 | `LLM_BASE_URL` | `LLM_MODEL` |
|--------|----------------|-------------|
| OpenAI | `https://api.openai.com/v1` | `gpt-4o` |
| 通义千问 | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-plus` |
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat` |
| 本地 Ollama | `http://localhost:11434/v1` | `llama3` |

### 启动

```bash
uvicorn app:asgi_app --host 0.0.0.0 --port 5001
```

浏览器访问 `http://localhost:5001`

## 使用说明

1. 点击左侧栏 **+** 按钮添加数据库连接（支持 MySQL / MongoDB / Elasticsearch）
2. 点击连接名称进行连接，展开后浏览数据库和表
3. 选中表后可查看 **Data**（数据）、**Structure**（结构）、**Query**（查询）三个标签页
4. 点击右上角 **Show AI Chat** 打开 AI 助手面板
5. 用自然语言描述查询需求，AI 生成查询后可直接执行或编辑

## 项目结构

```
OpenChatDB/
├── app.py                  # 应用入口
├── config.py               # 配置（从 .env 读取）
├── requirements.txt        # Python 依赖
├── routes/                 # API 路由
│   ├── api_chat.py         #   AI 对话 & 查询执行
│   ├── api_connections.py  #   连接管理
│   ├── api_database.py     #   数据库/表浏览
│   ├── api_query.py        #   查询执行
│   └── api_schema.py       #   Schema 检索 & 自动补全
├── services/               # 业务逻辑
│   ├── connection_manager.py  # 连接管理器（SSH 隧道）
│   ├── llm_service.py         # LLM 调用 & 查询提取
│   ├── schema_indexer.py      # Schema 缓存 & 搜索
│   ├── mysql_service.py       # MySQL 操作
│   ├── mongo_service.py       # MongoDB 操作
│   └── elasticsearch_service.py # Elasticsearch 操作
├── templates/
│   └── index.html          # 前端页面（Vue 3）
└── static/
    ├── css/style.css        # 样式
    └── js/
        ├── api.js           # API 请求封装
        └── app.js           # Vue 应用逻辑
```

## 技术栈

- **后端**: Flask + Uvicorn (ASGI)
- **前端**: Vue 3 (CDN)，无需构建工具
- **数据库驱动**: PyMySQL / PyMongo / elasticsearch-py
- **LLM**: OpenAI 兼容接口 (HTTP API)

## License

[MIT](LICENSE)
