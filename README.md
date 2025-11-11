# 通用 PubMed 文献检索系统

一个面向各类主题的通用 PubMed 文献检索与可视化平台，支持自定义检索、数据库本地化管理、多维度可视化分析与数据导出。

#### 工具
- **数据源**: PubMed/NCBI
- **语言**: Python 3
- **包管理**: uv
- **主要依赖**: Biopython

#### 脚本说明

**v1脚本** - 已废弃（已移除）
- 初始版本，存在解析错误问题

**v2脚本** - `pubmed_search_v2.py` ⭐
- **功能**:
  - 使用PubMed API进行文献检索
  - 健壮的文献解析（处理多种XML格式）
  - SQLite数据库持久化存储
  - 多格式导出(JSON/MD/CSV)
  - 完整的日志记录
  - 为Streamlit可视化准备

**可视化界面** - `streamlit_app.py` 🎨
- **功能**:
  - 交互式Dashboard展示统计信息
  - 文献浏览器（支持筛选、搜索、分页）
  - 数据可视化分析（图表、趋势、词频）
  - 数据导出功能

## 项目结构
```
workflow/
├── streamlit_app.py              # 主入口（多页架构）
├── pages/                        # 原生 Pages 页面
├── advanced_search.py            # 高级检索引擎
├── config_manager.py             # 配置管理（Secrets 优先）
├── local_data_manager.py         # 本地数据库管理
├── pubmed_search_v2.py           # v2 检索脚本（优化版）⭐
├── .streamlit/config.toml        # 主题与服务器配置
├── requirements.txt              # 依赖
├── STREAMLIT_DEPLOY.md           # 部署与使用
├── CHANGELOG_V3.1.md             # 变更日志
├── RELEASE_v3.1.md               # Release 文案
└── README.md                     # 本文件
```

## 功能特性
- 🔎 自定义检索：简单查询与可视化查询构建器
- 💾 数据本地化：上传/下载 SQLite 数据库，云端零占用
- 📊 可视化分析：年份趋势、期刊分布、关键词/MeSH 词频
- 📚 文献浏览：筛选、搜索、排序、分页、详情展开
- 📤 数据导出：JSON/Markdown/CSV

## 快速开始
```bash
# 克隆并进入目录
git clone https://github.com/telagod/pubmed-search-app.git
cd pubmed-search-app

# 准备环境（uv）
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt

# 启动应用
uv run streamlit run streamlit_app.py
```

## 使用说明

### 环境准备
```bash
# 切换到workflow目录
cd /home/telagod/project/daily/1110/workflow

# 创建虚拟环境（如果还没有）
uv venv

# 安装检索依赖
uv pip install biopython

# 安装可视化依赖（如需使用Streamlit）
uv pip install streamlit pandas plotly wordcloud matplotlib
```

### 运行检索脚本 (可选，CLI)
```bash
# 使用uv运行v2脚本
uv run python pubmed_search_v2.py

# 脚本会自动：
# 1. 执行示例检索策略
# 2. 保存数据到SQLite数据库
# 3. 导出JSON/MD/CSV格式文件
# 4. 生成检索摘要和日志
```

### 启动Streamlit可视化界面 🎨
```bash
# 使用uv运行Streamlit应用
uv run streamlit run streamlit_app.py

# 应用会自动在浏览器打开，地址通常为:
# http://localhost:8501
# 使用左侧 Pages 导航切换页面（数据管理 / Dashboard / 高级搜索 / 文献浏览 / 数据分析 / 设置 / 关于）
```

使用说明与部署: [STREAMLIT_DEPLOY.md](STREAMLIT_DEPLOY.md)

### 配置要求
- `.env` 文件（位于项目根目录）包含:
  - `pubmed_email`: PubMed注册邮箱
  - `api_key`: NCBI API密钥

## 版本
- v3.3：通用化、Pages 架构、缓存与数据本地化
- v3.2：多页与缓存优化、清理归档
- v3.1：最佳实践版（数据本地化）
- Salminen, A. (2024). Aryl hydrocarbon receptor impairs circadian regulation in Alzheimer's disease: Potential impact on glymphatic system dysfunction. European Journal of Neuroscience, 60(2), 3901–3920.
