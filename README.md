# BMAL1文献检索工作流程

## 项目信息
- **研究主题**: BMAL1 (Brain and Muscle ARNT-Like 1)
- **创建时间**: 2025-11-10
- **目的**: 深入研究BMAL1在昼夜节律和阿尔茨海默病中的作用

## 工作流程

### 第一阶段：文献检索

#### 检索策略
1. **BMAL1与昼夜节律**: `BMAL1 AND (circadian OR clock)`
2. **BMAL1与阿尔茨海默病**: `BMAL1 AND Alzheimer`
3. **BMAL1与类淋巴系统**: `BMAL1 AND (glymphatic OR clearance)`
4. **BMAL1与血脑屏障**: `BMAL1 AND (astrocyte OR BBB OR blood-brain barrier)`

#### 工具
- **数据源**: PubMed/NCBI
- **语言**: Python 3
- **包管理**: uv
- **主要依赖**: Biopython

#### 脚本说明

**v1脚本** - `pubmed_search_bmal1.py` (已废弃)
- 初始版本，存在解析错误问题

**v2脚本** - `pubmed_search_v2.py` ⭐ (当前版本)
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

#### 输出结构
```
workflow/
├── pubmed_search_bmal1.py      # v1检索脚本（已废弃）
├── pubmed_search_v2.py         # v2检索脚本（优化版）⭐
├── streamlit_app.py            # Streamlit可视化应用 🎨
├── STREAMLIT_GUIDE.md          # 可视化使用指南
├── results/                    # 结果目录
│   ├── bmal1_*.json            # JSON格式结果
│   ├── bmal1_*.md              # Markdown格式结果
│   ├── bmal1_*.csv             # CSV格式结果
│   ├── search_summary_*.json   # 检索摘要
│   ├── bmal1_papers.db         # SQLite数据库 💾
│   └── pubmed_search_*.log     # 日志文件
└── README.md                   # 本文件
```

## ✅ 已完成工作

### 第一阶段：文献检索 ✓
- [x] 编写Python检索脚本(v1)
- [x] 使用PubMed API检索文献
- [x] 共检索3,688篇相关文献
- [x] v1获取124篇文献详情（71.3%成功率）
- [x] 生成JSON和Markdown格式结果
- [x] 创建初步分析报告

### 第二阶段：代码优化与可视化 ✓ (2025-11-10)
- [x] **重构文献解析代码** - 创建v2版本
  - 使用dataclass进行数据建模
  - 健壮的多格式XML解析（处理字符串、列表、结构化字典）
  - SQLite数据库支持（带索引优化）
  - 完整的日志系统
  - 成功率提升至100% 🎯

- [x] **v2检索测试成功** - 154篇文献
  - CIRCADIAN: 50/50篇 (100% ✅)
  - ALZHEIMER: 50/50篇 (100% ✅)
  - GLYMPHATIC: 17/17篇 (100% ✅)
  - BBB: 50/50篇 (100% ✅)

- [x] **创建Streamlit可视化应用** 🎨
  - Dashboard统计概览（卡片、饼图、柱状图）
  - 文献浏览器（筛选、搜索、分页、详情展开）
  - 数据分析（年份趋势、期刊分布、词频树状图）
  - 数据导出（CSV/Excel）
  - 应用已成功启动: http://localhost:8501

- [x] **文档编写**
  - 创建详细的Streamlit使用指南
  - 更新工作流程README

### 检索成果对比

#### v1版本（初始）
📊 **检索统计**:
- BMAL1与昼夜节律: 3,527篇 (获取31篇, 62%)
- BMAL1与阿尔茨海默病: 74篇 (获取41篇, 82%)
- BMAL1与类淋巴系统: 17篇 (获取11篇, 65%)
- BMAL1与血脑屏障: 70篇 (获取41篇, 82%)
- **总计**: 124篇，平均成功率71.3%

#### v2版本（优化后）⭐
📊 **检索统计**:
- BMAL1与昼夜节律: 3,527篇 (获取50篇, 100% ✅)
- BMAL1与阿尔茨海默病: 74篇 (获取50篇, 100% ✅)
- BMAL1与类淋巴系统: 17篇 (获取17篇, 100% ✅)
- BMAL1与血脑屏障: 70篇 (获取50篇, 100% ✅)
- **总计**: 154篇，成功率100% 🎯

📄 **生成文件**:
- 4个JSON结果文件
- 4个Markdown结果文件
- 4个CSV结果文件 (新增)
- 1个SQLite数据库 (新增)
- 1个检索摘要文件
- 1个综合分析报告
- 完整的日志文件 (新增)

🔍 **关键发现**:
- 发现了星形胶质细胞BMAL1-BAG3保护轴（重大发现）
- 揭示了BMAL1作用的双面性（时间和细胞类型依赖）
- 识别了BMAL1与肠道菌群的新联系
- 发现BMAL1与类淋巴系统研究空白（仅17篇文献）

## 下一步计划

### 第三阶段：深度文献阅读 (待开始)
- [ ] 精读Top 5必读文献
  - PMID: 37315555 (BMAL1-BAG3轴)
  - PMID: 36056774 (BMAL1在AD中的重要性)
  - PMID: 34668266 (睡眠剥夺与BMAL1)
  - PMID: 33114015 (BMAL1升高的负面效应)
  - PMID: 37823531 (BMAL1与肠道菌群)
- [ ] 提取详细机制信息
- [ ] 构建信号通路图
- [ ] 识别矛盾和争议点

### 第四阶段：机制整合
- [ ] BMAL1-BAG3轴详细分析
- [ ] AhR-BMAL1相互作用
- [ ] BMAL1与类淋巴系统关联
- [ ] 构建综合作用模型

### 第五阶段：治疗策略
- [ ] 评估现有干预方法
- [ ] 提出创新治疗策略
- [ ] 设计验证实验
- [ ] 撰写研究提案

### 可视化增强计划 (可选)
- [ ] 添加全文下载链接
- [ ] 增加文献相似度分析
- [ ] 支持自定义检索策略
- [ ] 添加引用网络可视化
- [ ] 集成词云图展示

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

### 运行检索脚本 (v2优化版)
```bash
# 使用uv运行v2脚本
uv run python pubmed_search_v2.py

# 脚本会自动：
# 1. 执行4个检索策略
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
```

详细使用指南请参考: [STREAMLIT_GUIDE.md](STREAMLIT_GUIDE.md)

### 配置要求
- `.env` 文件（位于项目根目录）包含:
  - `pubmed_email`: PubMed注册邮箱
  - `api_key`: NCBI API密钥

## 研究背景

基于论文《Aryl hydrocarbon receptor impairs circadian regulation in Alzheimer's disease》的发现:

1. **BMAL1是核心时钟蛋白**: 与CLOCK形成异源二聚体，调控昼夜节律基因表达
2. **AD中BMAL1功能受损**:
   - DNA甲基化异常
   - 蛋白降解增加
   - 与AhR信号通路相互作用
3. **BMAL1与BBB功能**: 调节血脑屏障完整性和周细胞功能
4. **BMAL1与类淋巴系统**: 调控废物清除的昼夜节律

## 参考文献
- Salminen, A. (2024). Aryl hydrocarbon receptor impairs circadian regulation in Alzheimer's disease: Potential impact on glymphatic system dysfunction. European Journal of Neuroscience, 60(2), 3901–3920.
