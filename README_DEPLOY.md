# 🧬 BMAL1文献检索系统 - 高级版

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.51.0-FF4B4B.svg)](https://streamlit.io/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**一个功能强大的PubMed文献检索和分析平台，专为BMAL1相关研究设计**

[在线演示](https://your-app.streamlit.app) | [使用文档](GUIDE_V3.md) | [版本历史](UPGRADE_V3_REPORT.md)

</div>

---

## ✨ 主要特性

- 🔧 **Web界面配置** - 无需编辑代码，直接在浏览器中配置PubMed API
- 🔍 **高级搜索** - 支持简单查询和可视化查询构建器
- 📜 **搜索历史** - 自动记录所有搜索，支持一键重新执行
- 📚 **文献浏览** - 强大的筛选、搜索、分页功能
- 📊 **数据分析** - 多维度可视化分析（年份趋势、期刊分布、词频分析）
- 💾 **数据管理** - SQLite数据库持久化存储，支持多格式导出
- 🎨 **美观界面** - 专业的渐变卡片设计和交互式图表

## 🚀 快速开始

### 在线使用（推荐）

访问我们的Streamlit Cloud部署：**[在线演示链接](https://your-app.streamlit.app)**

1. 点击左侧导航栏的 **"⚙️ 设置"**
2. 填写PubMed Email和API Key
3. 保存配置
4. 前往 **"🔍 高级搜索"** 开始检索

### 本地部署

#### 方式1：使用uv（推荐）

```bash
# 克隆仓库
git clone https://github.com/yourusername/bmal1-pubmed-search.git
cd bmal1-pubmed-search

# 使用uv安装依赖
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -r requirements.txt

# 运行应用
uv run streamlit run streamlit_app.py
```

#### 方式2：使用pip

```bash
# 克隆仓库
git clone https://github.com/yourusername/bmal1-pubmed-search.git
cd bmal1-pubmed-search

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 运行应用
streamlit run streamlit_app.py
```

应用将在 http://localhost:8501 启动。

## 📋 配置说明

### 获取PubMed API密钥

1. 访问 [NCBI账户设置](https://www.ncbi.nlm.nih.gov/account/settings/)
2. 创建或登录NCBI账户
3. 在"API Key Management"部分创建新的API密钥
4. 复制API密钥和注册邮箱

### 配置方式

#### 方式1：Web界面配置（推荐）

1. 启动应用
2. 进入"⚙️ 设置"页面
3. 填写Email和API Key
4. 保存配置

#### 方式2：环境变量配置

创建`.env`文件：

```env
pubmed_email:your-email@example.com
api_key:your-ncbi-api-key
```

#### 方式3：Streamlit Cloud Secrets

如果部署到Streamlit Cloud，在应用设置中添加Secrets：

```toml
pubmed_email = "your-email@example.com"
api_key = "your-ncbi-api-key"
```

## 📖 使用指南

### 基础搜索

**简单查询**：
```
BMAL1 AND Alzheimer
```

**高级查询**：
- 关键词：BMAL1, circadian, sleep
- 逻辑：AND
- 作者：Smith
- 日期：2020-2024

详细使用说明请参考：[GUIDE_V3.md](GUIDE_V3.md)

## 🗂️ 项目结构

```
bmal1-pubmed-search/
├── streamlit_app.py           # v3.0 Web界面
├── config_manager.py          # 配置管理模块
├── advanced_search.py         # 高级搜索引擎
├── pubmed_search_v2.py        # 基础搜索和解析
├── requirements.txt           # 依赖列表
├── .streamlit/
│   └── config.toml           # Streamlit配置
├── config/                    # 用户配置（gitignore）
├── results/                   # 搜索结果（gitignore）
├── GUIDE_V3.md               # 详细使用指南
├── UPGRADE_V3_REPORT.md      # 升级报告
└── README.md                 # 本文件
```

## 🔧 技术栈

- **后端**: Python 3.8+, Biopython, SQLite
- **前端**: Streamlit
- **可视化**: Plotly, Matplotlib, Pandas
- **数据库**: SQLite
- **包管理**: uv / pip

## 📊 版本历史

| 版本 | 发布日期 | 主要特性 |
|------|---------|---------|
| v3.0 | 2025-11-10 | Web配置、高级搜索、搜索历史 |
| v2.0 | 2025-11-10 | 健壮解析、数据库存储、100%成功率 |
| v1.0 | 2025-11-10 | 基础检索、可视化界面 |

详细升级记录：[UPGRADE_V3_REPORT.md](UPGRADE_V3_REPORT.md)

## 🎯 功能亮点

### Dashboard
- 📊 文献统计卡片
- 📈 年份趋势图
- 🥧 策略分布饼图
- 🏷️ 高频词汇分析

### 高级搜索
- 🔍 简单查询模式
- 🛠️ 可视化查询构建器
- 📅 日期范围筛选
- 👤 作者/期刊筛选
- 📜 搜索历史管理

### 文献浏览
- 🔎 关键词搜索
- 🏷️ 策略筛选
- 📅 年份范围筛选
- 📄 分页浏览
- 📖 详情展开

### 数据分析
- 📊 年份分析
- 📰 期刊统计
- 🌳 词频树状图
- 📥 数据导出

## 🌐 部署到Streamlit Cloud

### 步骤1：推送到GitHub

```bash
# 在项目目录下
git init
git add .
git commit -m "Initial commit: BMAL1 PubMed Search v3.0"
gh repo create bmal1-pubmed-search --public --source=. --push
```

### 步骤2：配置Streamlit Cloud

1. 访问 [Streamlit Cloud](https://share.streamlit.io/)
2. 使用GitHub账号登录
3. 点击"New app"
4. 选择仓库：`yourusername/bmal1-pubmed-search`
5. 主文件：`streamlit_app.py`
6. 点击"Advanced settings"
7. 在Secrets中添加：
   ```toml
   pubmed_email = "your-email@example.com"
   api_key = "your-ncbi-api-key"
   ```
8. 点击"Deploy"

几分钟后，应用将自动部署完成！

## 💡 常见问题

### Q: 如何获取NCBI API密钥？
A: 访问 https://www.ncbi.nlm.nih.gov/account/settings/ 创建账户并生成API密钥。

### Q: 为什么搜索失败？
A: 检查Email和API Key是否正确配置，确保网络连接正常。

### Q: 数据库文件在哪里？
A: 本地部署时在`results/bmal1_papers.db`，云端部署时存储在临时目录。

### Q: 如何导出数据？
A: 每次搜索会自动导出JSON/MD/CSV文件到`results/`目录。

更多问题请参考：[GUIDE_V3.md](GUIDE_V3.md)

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 👨‍💻 作者

**KOOI Research Assistant** ฅ'ω'ฅ

## 🙏 致谢

- PubMed/NCBI - 提供免费的文献数据库API
- Streamlit - 优秀的Web应用框架
- Biopython - 强大的生物信息学工具

---

<div align="center">

**享受高效的文献检索体验！** 📚✨

如果觉得有用，请给个 ⭐ Star 吧！

</div>
