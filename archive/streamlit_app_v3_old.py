#!/usr/bin/env python3
# Archived: legacy v3.0 UI preserved for reference. Not used by app.
"""
BMAL1文献检索系统 - 高级版 Streamlit WebUI
==========================================
特性:
- 可配置的PubMed邮箱和API密钥
- 高级自定义搜索
- 搜索历史管理
- 交互式Dashboard
- 文献浏览与分析

作者: KOOI Research Assistant
日期: 2025-11-10
版本: v3.0
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sqlite3
import json
from collections import Counter
from datetime import datetime
from typing import Dict, List, Optional
import re

# 导入自定义模块
from config_manager import ConfigManager, SearchParams, PubMedConfig
from advanced_search import AdvancedPubMedSearchEngine, create_search_engine
from pubmed_search_v2 import PaperDatabase, setup_logging

# ==================== 页面配置 ====================
st.set_page_config(
    page_title="BMAL1高级文献检索系统",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== 自定义CSS ====================
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 1rem 0;
    }
    .stat-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .stat-number {
        font-size: 2.5rem;
        font-weight: bold;
        margin: 0.5rem 0;
    }
    .stat-label {
        font-size: 1rem;
        opacity: 0.9;
    }
    .paper-card {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 8px;
        border-left: 4px solid #1f77b4;
        margin-bottom: 1rem;
    }
    .paper-title {
        font-size: 1.2rem;
        font-weight: bold;
        color: #2c3e50;
        margin-bottom: 0.5rem;
    }
    .paper-meta {
        color: #7f8c8d;
        font-size: 0.9rem;
    }
    .keyword-tag {
        background: #e3f2fd;
        color: #1976d2;
        padding: 0.3rem 0.6rem;
        border-radius: 15px;
        font-size: 0.85rem;
        margin: 0.2rem;
        display: inline-block;
    }
    .success-box {
        background: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .error-box {
        background: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .warning-box {
        background: #fff3cd;
        border: 1px solid #ffeaa7;
        color: #856404;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .info-box {
        background: #d1ecf1;
        border: 1px solid #bee5eb;
        color: #0c5460;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)


# ==================== 数据库访问层 ====================
class PaperDB:
    """数据库访问类"""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = None
        self._connect()

    def _connect(self):
        """建立数据库连接"""
        if not self.db_path.exists():
            st.warning(f"⚠️ 数据库文件不存在: {self.db_path}")
            return
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)

    def get_all_papers(self) -> pd.DataFrame:
        """获取所有文献为DataFrame"""
        if not self.conn:
            return pd.DataFrame()

        query = "SELECT * FROM papers"
        df = pd.read_sql_query(query, self.conn)

        # 解析JSON字段
        df['authors'] = df['authors'].apply(lambda x: json.loads(x) if x else [])
        df['keywords'] = df['keywords'].apply(lambda x: json.loads(x) if x else [])
        df['mesh_terms'] = df['mesh_terms'].apply(lambda x: json.loads(x) if x else [])

        return df

    def get_statistics(self) -> Dict:
        """获取统计信息"""
        if not self.conn:
            return {}

        cursor = self.conn.cursor()
        stats = {}

        try:
            # 总文献数
            cursor.execute('SELECT COUNT(*) FROM papers')
            stats['total_papers'] = cursor.fetchone()[0]

            # 按年份统计
            cursor.execute('''
                SELECT pub_year, COUNT(*)
                FROM papers
                WHERE pub_year != '' AND pub_year != 'Unknown'
                GROUP BY pub_year
                ORDER BY pub_year DESC
            ''')
            stats['by_year'] = dict(cursor.fetchall())

            # 按检索策略统计
            cursor.execute('''
                SELECT search_strategy, COUNT(*)
                FROM papers
                GROUP BY search_strategy
            ''')
            stats['by_strategy'] = dict(cursor.fetchall())

            # 有摘要的文献数
            cursor.execute('SELECT COUNT(*) FROM papers WHERE has_abstract = 1')
            stats['with_abstract'] = cursor.fetchone()[0]

            # 独特期刊数
            cursor.execute('SELECT COUNT(DISTINCT journal) FROM papers WHERE journal != ""')
            stats['unique_journals'] = cursor.fetchone()[0]
        except Exception as e:
            st.error(f"获取统计信息失败: {e}")

        return stats

    def search_papers(self, keyword: str = "", strategy: str = "",
                     year_range: tuple = None) -> pd.DataFrame:
        """搜索文献"""
        df = self.get_all_papers()

        if df.empty:
            return df

        if keyword:
            keyword_lower = keyword.lower()
            df = df[
                df['title'].str.lower().str.contains(keyword_lower, na=False) |
                df['abstract'].str.lower().str.contains(keyword_lower, na=False) |
                df['keywords'].apply(lambda x: any(keyword_lower in k.lower() for k in x))
            ]

        if strategy and strategy != "全部":
            df = df[df['search_strategy'] == strategy]

        if year_range:
            df = df[
                (df['pub_year'].astype(str) >= str(year_range[0])) &
                (df['pub_year'].astype(str) <= str(year_range[1]))
            ]

        return df

    def get_top_keywords(self, n: int = 20) -> List[tuple]:
        """获取高频关键词"""
        df = self.get_all_papers()
        if df.empty:
            return []

        all_keywords = []
        for kw_list in df['keywords']:
            all_keywords.extend(kw_list)

        counter = Counter(all_keywords)
        return counter.most_common(n)

    def get_top_mesh_terms(self, n: int = 20) -> List[tuple]:
        """获取高频MeSH主题词"""
        df = self.get_all_papers()
        if df.empty:
            return []

        all_mesh = []
        for mesh_list in df['mesh_terms']:
            all_mesh.extend(mesh_list)

        counter = Counter(all_mesh)
        return counter.most_common(n)

    def close(self):
        """关闭连接"""
        if self.conn:
            self.conn.close()


# ==================== 初始化 ====================
@st.cache_resource
def init_config_manager():
    """初始化配置管理器（带缓存）"""
    return ConfigManager()


@st.cache_resource
def init_db():
    """初始化数据库连接（带缓存）"""
    db_path = Path(__file__).parent / "results" / "bmal1_papers.db"
    return PaperDB(db_path)


# ==================== 页面：设置 ====================
def page_settings():
    """设置页面"""
    st.markdown('<p class="main-header">⚙️ 系统设置</p>', unsafe_allow_html=True)

    config_manager = init_config_manager()
    pubmed_config = config_manager.get_pubmed_config()

    st.markdown("## 📧 PubMed API配置")

    st.markdown("""
    <div class="info-box">
    💡 <b>提示</b>: 配置PubMed邮箱和API密钥后，您可以直接在Web界面进行文献检索。
    <br>如果您已经在.env文件中配置，这里会自动加载。
    </div>
    """, unsafe_allow_html=True)

    # 配置表单
    with st.form("pubmed_config_form"):
        email = st.text_input(
            "📧 Email",
            value=pubmed_config.email,
            help="PubMed注册邮箱地址"
        )

        api_key = st.text_input(
            "🔑 API Key",
            value=pubmed_config.api_key,
            type="password",
            help="NCBI API密钥"
        )

        col1, col2 = st.columns(2)
        with col1:
            max_results = st.number_input(
                "📊 每次搜索最大结果数",
                min_value=10,
                max_value=500,
                value=pubmed_config.max_results,
                step=10,
                help="单次搜索最多获取的文献数量"
            )

        with col2:
            batch_size = st.number_input(
                "📦 批次大小",
                min_value=10,
                max_value=100,
                value=pubmed_config.batch_size,
                step=10,
                help="每批获取的文献数量"
            )

        sort_by = st.selectbox(
            "🔀 默认排序方式",
            options=["relevance", "pub_date"],
            index=0 if pubmed_config.sort_by == "relevance" else 1,
            help="relevance: 按相关性排序, pub_date: 按发表日期排序"
        )

        submitted = st.form_submit_button("💾 保存配置", use_container_width=True)

        if submitted:
            # 验证
            if not email or '@' not in email:
                st.markdown(
                    '<div class="error-box">❌ 请输入有效的邮箱地址</div>',
                    unsafe_allow_html=True
                )
            elif not api_key:
                st.markdown(
                    '<div class="error-box">❌ 请输入API密钥</div>',
                    unsafe_allow_html=True
                )
            else:
                # 更新配置
                config_manager.update_pubmed_config(
                    email=email,
                    api_key=api_key,
                    max_results=max_results,
                    batch_size=batch_size,
                    sort_by=sort_by
                )

                st.markdown(
                    '<div class="success-box">✅ 配置已成功保存！</div>',
                    unsafe_allow_html=True
                )
                st.rerun()

    # 显示当前配置状态
    st.markdown("---")
    st.markdown("## 📋 当前配置状态")

    col1, col2 = st.columns(2)
    with col1:
        if config_manager.is_configured():
            st.markdown(
                '<div class="success-box">✅ <b>配置状态</b>: 已配置</div>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                '<div class="warning-box">⚠️  <b>配置状态</b>: 未配置</div>',
                unsafe_allow_html=True
            )

    with col2:
        st.info(f"""
        **当前设置**:
        - Email: {pubmed_config.email if pubmed_config.email else '未设置'}
        - API Key: {'已设置 (' + '*' * 8 + ')' if pubmed_config.api_key else '未设置'}
        - 最大结果数: {pubmed_config.max_results}
        - 批次大小: {pubmed_config.batch_size}
        """)

    # 配置导入导出
    st.markdown("---")
    st.markdown("## 📤 配置管理")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("📥 导出配置", use_container_width=True):
            export_path = Path(__file__).parent / "config" / f"config_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            if config_manager.export_config(export_path):
                st.success(f"✅ 配置已导出: {export_path.name}")
            else:
                st.error("❌ 导出失败")

    with col2:
        uploaded_file = st.file_uploader("选择配置文件", type=['json'], label_visibility="collapsed")
        if uploaded_file:
            import_path = Path(__file__).parent / "config" / "temp_import.json"
            import_path.parent.mkdir(exist_ok=True)
            with open(import_path, 'wb') as f:
                f.write(uploaded_file.getbuffer())

            if config_manager.import_config(import_path):
                st.success("✅ 配置已导入")
                import_path.unlink()  # 删除临时文件
                st.rerun()
            else:
                st.error("❌ 导入失败")

    with col3:
        if st.button("🗑️ 清空搜索历史", use_container_width=True):
            config_manager.clear_search_history()
            st.success("✅ 搜索历史已清空")
            st.rerun()


# ==================== 页面：高级搜索 ====================
def page_advanced_search():
    """高级搜索页面"""
    st.markdown('<p class="main-header">🔍 高级搜索</p>', unsafe_allow_html=True)

    config_manager = init_config_manager()

    # 检查配置
    if not config_manager.is_configured():
        st.markdown(
            '<div class="warning-box">⚠️  请先在"设置"页面配置PubMed API</div>',
            unsafe_allow_html=True
        )
        st.stop()

    # 搜索表单
    st.markdown("## 🎯 构建查询")

    tab1, tab2, tab3 = st.tabs(["简单查询", "高级查询", "搜索历史"])

    with tab1:
        _simple_search_form(config_manager)

    with tab2:
        _advanced_search_form(config_manager)

    with tab3:
        _search_history(config_manager)


def _simple_search_form(config_manager):
    """简单搜索表单"""
    with st.form("simple_search_form"):
        search_name = st.text_input(
            "🏷️ 搜索名称",
            value="My Search",
            help="给本次搜索起个名字，便于管理"
        )

        query = st.text_area(
            "🔎 查询字符串",
            value="BMAL1 AND Alzheimer",
            height=100,
            help="输入PubMed查询字符串，例如: BMAL1 AND (circadian OR clock)"
        )

        col1, col2, col3 = st.columns(3)

        with col1:
            max_results = st.number_input(
                "📊 最大结果数",
                min_value=10,
                max_value=500,
                value=100,
                step=10
            )

        with col2:
            sort_by = st.selectbox(
                "🔀 排序方式",
                options=["relevance", "pub_date"],
                index=0
            )

        with col3:
            export_formats = st.multiselect(
                "📁 导出格式",
                options=["json", "md", "csv"],
                default=["json", "md", "csv"]
            )

        submitted = st.form_submit_button("🚀 开始搜索", use_container_width=True)

        if submitted:
            if not query.strip():
                st.error("❌ 请输入查询字符串")
            else:
                _execute_search(
                    config_manager,
                    query=query,
                    name=search_name,
                    max_results=max_results,
                    sort_by=sort_by,
                    export_formats=export_formats
                )


def _advanced_search_form(config_manager):
    """高级搜索表单"""
    st.markdown("使用查询构建器创建复杂的PubMed查询")

    with st.form("advanced_search_form"):
        search_name = st.text_input(
            "🏷️ 搜索名称",
            value="Advanced Search",
            help="给本次搜索起个名字"
        )

        # 关键词部分
        st.markdown("### 🔑 关键词")
        col1, col2 = st.columns([3, 1])

        with col1:
            keywords_input = st.text_input(
                "关键词（用逗号分隔）",
                value="BMAL1, circadian, clock",
                help="输入多个关键词，用逗号分隔"
            )

        with col2:
            logic_operator = st.selectbox(
                "逻辑运算符",
                options=["AND", "OR"],
                index=0
            )

        # 字段筛选
        st.markdown("### 📋 字段筛选（可选）")

        col1, col2 = st.columns(2)

        with col1:
            author = st.text_input("👤 作者", help="作者姓名")
            journal = st.text_input("📰 期刊", help="期刊名称")

        with col2:
            pub_type = st.text_input("📄 发表类型", help="例如: Review, Clinical Trial")
            affiliation = st.text_input("🏛️ 机构", help="作者所属机构")

        # 日期范围
        st.markdown("### 📅 日期范围（可选）")

        col1, col2 = st.columns(2)

        with col1:
            use_date_filter = st.checkbox("启用日期筛选")

        if use_date_filter:
            with col1:
                min_date = st.date_input("开始日期")
            with col2:
                max_date = st.date_input("结束日期")
        else:
            min_date = None
            max_date = None

        # 其他选项
        st.markdown("### ⚙️ 其他选项")

        col1, col2, col3 = st.columns(3)

        with col1:
            max_results = st.number_input(
                "📊 最大结果数",
                min_value=10,
                max_value=500,
                value=100,
                step=10
            )

        with col2:
            sort_by = st.selectbox(
                "🔀 排序方式",
                options=["relevance", "pub_date"],
                index=0
            )

        with col3:
            export_formats = st.multiselect(
                "📁 导出格式",
                options=["json", "md", "csv"],
                default=["json", "md", "csv"]
            )

        # 显示构建的查询
        st.markdown("### 📝 构建的查询")

        # 构建查询字符串
        keywords = [k.strip() for k in keywords_input.split(',') if k.strip()]
        query_parts = [f" {logic_operator} ".join(keywords)]

        if author:
            query_parts.append(f"{author}[Author]")
        if journal:
            query_parts.append(f"{journal}[Journal]")
        if pub_type:
            query_parts.append(f"{pub_type}[Publication Type]")
        if affiliation:
            query_parts.append(f"{affiliation}[Affiliation]")

        final_query = " AND ".join(query_parts)

        st.code(final_query, language="text")

        submitted = st.form_submit_button("🚀 开始搜索", use_container_width=True)

        if submitted:
            if not keywords:
                st.error("❌ 请输入至少一个关键词")
            else:
                _execute_search(
                    config_manager,
                    query=final_query,
                    name=search_name,
                    max_results=max_results,
                    min_date=min_date.strftime("%Y/%m/%d") if min_date else "",
                    max_date=max_date.strftime("%Y/%m/%d") if max_date else "",
                    sort_by=sort_by,
                    export_formats=export_formats
                )


def _search_history(config_manager):
    """搜索历史"""
    st.markdown("### 📜 最近搜索")

    history = config_manager.get_recent_searches(20)

    if not history:
        st.info("暂无搜索历史")
        return

    for idx, item in enumerate(history):
        with st.expander(
            f"🔍 {item['search_params']['name']} - "
            f"{item['timestamp'][:19]} - "
            f"成功率: {item['success_rate']}"
        ):
            st.markdown(f"**查询**: `{item['search_params']['query']}`")
            st.markdown(f"**结果数**: {item['result_count']}")
            st.markdown(f"**成功数**: {item['success_count']}")
            st.markdown(f"**时间**: {item['timestamp']}")

            if st.button(f"🔄 重新执行", key=f"rerun_{idx}"):
                params = SearchParams.from_dict(item['search_params'])
                _execute_search(
                    config_manager,
                    query=params.query,
                    name=params.name,
                    max_results=params.max_results,
                    sort_by=params.sort_by,
                    export_formats=["json", "md", "csv"]
                )


def _execute_search(config_manager, query: str, name: str,
                   max_results: int, min_date: str = "",
                   max_date: str = "", sort_by: str = "relevance",
                   export_formats: List[str] = None):
    """执行搜索"""
    if export_formats is None:
        export_formats = ["json", "md", "csv"]

    # 创建搜索参数
    search_params = SearchParams(
        query=query,
        name=name,
        max_results=max_results,
        min_date=min_date,
        max_date=max_date,
        sort_by=sort_by,
        retmax=max_results
    )

    # 创建搜索引擎
    engine = create_search_engine()

    # 显示进度
    with st.spinner("🔍 正在搜索..."):
        # 执行搜索
        db_path = Path(__file__).parent / "results" / "bmal1_papers.db"
        export_dir = Path(__file__).parent / "results"

        try:
            result = engine.execute_search(
                search_params,
                db_path=db_path,
                export_dir=export_dir,
                save_to_db=True,
                export_formats=export_formats
            )

            if result['success']:
                st.markdown(
                    f'<div class="success-box">'
                    f'✅ <b>搜索成功！</b><br>'
                    f'找到 {result["total_count"]} 篇文献，成功获取 {result["fetched_count"]} 篇 '
                    f'（成功率: {result["success_rate"]}）'
                    f'</div>',
                    unsafe_allow_html=True
                )

                # 显示导出的文件
                if result.get('exported_files'):
                    st.markdown("**📁 导出文件**:")
                    for format_type, filepath in result['exported_files'].items():
                        st.markdown(f"- {format_type.upper()}: `{Path(filepath).name}`")

                st.success("数据已保存到数据库，您可以在\"文献浏览器\"中查看结果")

            else:
                st.markdown(
                    f'<div class="error-box">'
                    f'❌ <b>搜索失败</b><br>'
                    f'{result.get("error", "未知错误")}'
                    f'</div>',
                    unsafe_allow_html=True
                )

        except Exception as e:
            st.markdown(
                f'<div class="error-box">'
                f'❌ <b>搜索过程中发生错误</b><br>'
                f'{str(e)}'
                f'</div>',
                unsafe_allow_html=True
            )


# ==================== 从v1导入其他页面 ====================
# 这些页面保持不变，从v1复制过来

def page_dashboard():
    """Dashboard页面 - 从v1复制"""
    st.markdown('<p class="main-header">🧬 BMAL1文献检索系统 Dashboard</p>',
                unsafe_allow_html=True)

    db = init_db()
    stats = db.get_statistics()

    if not stats:
        st.warning("⚠️  数据库为空或无法访问，请先执行搜索或检查数据库文件")
        return

    # 统计卡片
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-label">📚 总文献数</div>
            <div class="stat-number">{stats.get('total_papers', 0)}</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-label">✅ 有摘要</div>
            <div class="stat-number">{stats.get('with_abstract', 0)}</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-label">📰 独特期刊</div>
            <div class="stat-number">{stats.get('unique_journals', 0)}</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        strategy_count = len(stats.get('by_strategy', {}))
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-label">🔍 检索策略</div>
            <div class="stat-number">{strategy_count}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # 可视化图表
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("📊 按检索策略分布")
        if stats.get('by_strategy'):
            strategy_df = pd.DataFrame(
                list(stats['by_strategy'].items()),
                columns=['策略', '文献数']
            )
            fig = px.pie(
                strategy_df,
                values='文献数',
                names='策略',
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.subheader("📈 发表年份趋势")
        if stats.get('by_year'):
            year_df = pd.DataFrame(
                list(stats['by_year'].items()),
                columns=['年份', '文献数']
            ).sort_values('年份')

            fig = px.bar(
                year_df,
                x='年份',
                y='文献数',
                color='文献数',
                color_continuous_scale='Blues'
            )
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    # 高频词汇分析
    st.markdown("---")
    st.subheader("🏷️ 高频关键词与MeSH主题词")

    col_kw, col_mesh = st.columns(2)

    with col_kw:
        st.markdown("**Top 15 关键词**")
        top_keywords = db.get_top_keywords(15)
        if top_keywords:
            kw_df = pd.DataFrame(top_keywords, columns=['关键词', '频次'])
            fig = px.bar(
                kw_df,
                x='频次',
                y='关键词',
                orientation='h',
                color='频次',
                color_continuous_scale='Viridis'
            )
            fig.update_layout(showlegend=False, height=400)
            st.plotly_chart(fig, use_container_width=True)

    with col_mesh:
        st.markdown("**Top 15 MeSH主题词**")
        top_mesh = db.get_top_mesh_terms(15)
        if top_mesh:
            mesh_df = pd.DataFrame(top_mesh, columns=['MeSH主题词', '频次'])
            fig = px.bar(
                mesh_df,
                x='频次',
                y='MeSH主题词',
                orientation='h',
                color='频次',
                color_continuous_scale='Plasma'
            )
            fig.update_layout(showlegend=False, height=400)
            st.plotly_chart(fig, use_container_width=True)


def page_browser():
    """文献浏览器页面 - 从v1复制"""
    st.markdown('<p class="main-header">📚 文献浏览器</p>', unsafe_allow_html=True)

    db = init_db()
    stats = db.get_statistics()

    if not stats:
        st.warning("⚠️  数据库为空，请先执行搜索")
        return

    # 筛选器
    st.sidebar.header("🔍 筛选选项")

    # 检索策略筛选
    strategies = ["全部"] + list(stats.get('by_strategy', {}).keys())
    selected_strategy = st.sidebar.selectbox("检索策略", strategies)

    # 关键词搜索
    keyword = st.sidebar.text_input("关键词搜索", placeholder="输入关键词...")

    # 年份范围
    years = sorted([int(y) for y in stats.get('by_year', {}).keys() if y.isdigit()])
    if years:
        year_range = st.sidebar.slider(
            "发表年份",
            min_value=min(years),
            max_value=max(years),
            value=(min(years), max(years))
        )
    else:
        year_range = None

    # 每页显示数量
    per_page = st.sidebar.selectbox("每页显示", [10, 20, 50, 100], index=1)

    # 执行搜索
    df = db.search_papers(
        keyword=keyword,
        strategy=selected_strategy if selected_strategy != "全部" else "",
        year_range=year_range
    )

    # 显示结果统计
    st.info(f"🔍 找到 **{len(df)}** 篇文献")

    if len(df) == 0:
        st.warning("没有找到符合条件的文献")
        return

    # 排序选项
    sort_by = st.selectbox(
        "排序方式",
        ["发表年份(新→旧)", "发表年份(旧→新)", "标题(A→Z)", "期刊(A→Z)"]
    )

    if "新→旧" in sort_by:
        df = df.sort_values('pub_year', ascending=False)
    elif "旧→新" in sort_by:
        df = df.sort_values('pub_year', ascending=True)
    elif "标题" in sort_by:
        df = df.sort_values('title')
    else:
        df = df.sort_values('journal')

    # 分页
    total_pages = (len(df) - 1) // per_page + 1
    page = st.number_input("页码", min_value=1, max_value=total_pages, value=1)

    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    page_df = df.iloc[start_idx:end_idx]

    st.markdown(f"**第 {page}/{total_pages} 页**")
    st.markdown("---")

    # 显示文献卡片
    for idx, row in page_df.iterrows():
        display_paper_card(row)


def display_paper_card(paper):
    """显示单篇文献卡片"""
    with st.container():
        st.markdown(f"""
        <div class="paper-card">
            <div class="paper-title">{paper['title']}</div>
            <div class="paper-meta">
                📰 <b>{paper['journal']}</b> |
                📅 {paper['pub_date']} |
                🔗 <a href="{paper['pubmed_url']}" target="_blank">PMID: {paper['pmid']}</a>
                {f" | 🔬 DOI: {paper['doi']}" if paper['doi'] else ""}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 展开查看详情
        with st.expander("📖 查看详情"):
            # 作者信息
            if paper['authors']:
                authors = json.loads(paper['authors']) if isinstance(paper['authors'], str) else paper['authors']
                st.markdown(f"**作者**: {', '.join(authors[:5])}" +
                           (f" 等 ({len(authors)}位)" if len(authors) > 5 else ""))

            # 摘要
            if paper['abstract']:
                st.markdown("**摘要**:")
                st.write(paper['abstract'])

            # 关键词
            if paper['keywords']:
                keywords = json.loads(paper['keywords']) if isinstance(paper['keywords'], str) else paper['keywords']
                st.markdown("**关键词**:")
                kw_html = "".join([f'<span class="keyword-tag">{kw}</span>' for kw in keywords[:10]])
                st.markdown(kw_html, unsafe_allow_html=True)

            # MeSH主题词
            if paper['mesh_terms']:
                mesh = json.loads(paper['mesh_terms']) if isinstance(paper['mesh_terms'], str) else paper['mesh_terms']
                st.markdown("**MeSH主题词**:")
                mesh_html = "".join([f'<span class="keyword-tag">{m}</span>' for m in mesh[:10]])
                st.markdown(mesh_html, unsafe_allow_html=True)

            # 检索策略标签
            st.markdown(f"**检索策略**: `{paper['search_strategy']}`")


def page_analysis():
    """数据分析页面 - 简化版"""
    st.markdown('<p class="main-header">📈 数据分析</p>', unsafe_allow_html=True)

    db = init_db()
    df = db.get_all_papers()

    if df.empty:
        st.warning("⚠️  数据库为空，请先执行搜索")
        return

    # Tab导航
    tab1, tab2, tab3 = st.tabs([
        "📊 年份分析",
        "📰 期刊分析",
        "🏷️ 词频分析"
    ])

    with tab1:
        st.subheader("发表年份详细分析")

        # 按年份和策略交叉统计
        year_strategy = df.groupby(['pub_year', 'search_strategy']).size().reset_index(name='count')
        year_strategy = year_strategy[year_strategy['pub_year'] != 'Unknown']

        fig = px.bar(
            year_strategy,
            x='pub_year',
            y='count',
            color='search_strategy',
            title='各检索策略文献年份分布',
            labels={'pub_year': '发表年份', 'count': '文献数', 'search_strategy': '检索策略'},
            barmode='stack'
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader("期刊发表统计")

        # Top期刊
        top_journals = df[df['journal'] != ''].groupby('journal').size().reset_index(name='count')
        top_journals = top_journals.sort_values('count', ascending=False).head(20)

        fig = px.bar(
            top_journals,
            x='count',
            y='journal',
            orientation='h',
            title='Top 20 发表期刊',
            labels={'count': '文献数', 'journal': '期刊'},
            color='count',
            color_continuous_scale='Teal'
        )
        fig.update_layout(height=600, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with tab3:
        st.subheader("关键词与MeSH主题词分析")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**高频关键词（Top 30）**")
            top_kw = db.get_top_keywords(30)
            kw_df = pd.DataFrame(top_kw, columns=['关键词', '频次'])

            fig = go.Figure(data=[go.Treemap(
                labels=kw_df['关键词'],
                parents=[''] * len(kw_df),
                values=kw_df['频次'],
                textinfo='label+value',
                marker=dict(colorscale='Viridis')
            )])
            fig.update_layout(title='关键词树状图', height=500)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("**高频MeSH主题词（Top 30）**")
            top_mesh = db.get_top_mesh_terms(30)
            mesh_df = pd.DataFrame(top_mesh, columns=['MeSH主题词', '频次'])

            fig = go.Figure(data=[go.Treemap(
                labels=mesh_df['MeSH主题词'],
                parents=[''] * len(mesh_df),
                values=mesh_df['频次'],
                textinfo='label+value',
                marker=dict(colorscale='Plasma')
            )])
            fig.update_layout(title='MeSH主题词树状图', height=500)
            st.plotly_chart(fig, use_container_width=True)


def page_about():
    """关于页面"""
    st.markdown('<p class="main-header">ℹ️ 关于本系统</p>', unsafe_allow_html=True)

    st.markdown("""
    ## 🧬 BMAL1文献检索系统 - 高级版

    ### 📖 项目简介

    本系统是一个功能强大的PubMed文献检索和分析平台，专为BMAL1相关研究设计。

    ### ✨ 主要功能

    - **⚙️  灵活配置**: Web界面直接配置PubMed API
    - **🔍 高级搜索**: 支持复杂查询构建和自定义筛选
    - **📜 搜索历史**: 自动保存和管理搜索记录
    - **📚 文献浏览**: 强大的筛选、搜索、分页功能
    - **📊 数据分析**: 多维度可视化分析
    - **💾 数据管理**: SQLite数据库持久化存储

    ### 🆕 v3.0 新特性

    1. **可配置API**: 无需修改代码，直接在Web界面配置
    2. **高级查询构建器**: 简单模式和高级模式双重支持
    3. **搜索历史管理**: 自动记录，一键重新执行
    4. **配置导入导出**: 方便备份和迁移

    ### 🛠️ 技术栈

    - **后端**: Python 3 + Biopython + SQLite
    - **前端**: Streamlit
    - **可视化**: Plotly + Pandas
    - **包管理**: uv

    ### 👨‍💻 开发信息

    - **作者**: KOOI Research Assistant ฅ'ω'ฅ
    - **版本**: v3.0 (高级版)
    - **更新时间**: 2025-11-10
    - **数据来源**: PubMed/NCBI
    """)

    db = init_db()
    stats = db.get_statistics()

    if stats:
        st.markdown("### 📊 当前数据统计")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("总文献数", stats.get('total_papers', 0))
        with col2:
            st.metric("独特期刊", stats.get('unique_journals', 0))
        with col3:
            st.metric("检索策略", len(stats.get('by_strategy', {})))

    st.markdown("---")
    st.success("💡 使用左侧导航栏探索不同功能")


# ==================== 主应用 ====================
def main():
    """主应用入口"""

    # 侧边栏导航
    st.sidebar.title("🧬 BMAL1高级检索")
    st.sidebar.markdown("---")

    page = st.sidebar.radio(
        "导航菜单",
        [
            "📊 Dashboard",
            "🔍 高级搜索",
            "📚 文献浏览",
            "📈 数据分析",
            "⚙️ 设置",
            "ℹ️ 关于"
        ],
        label_visibility="collapsed"
    )

    # 检查配置状态
    config_manager = init_config_manager()
    if not config_manager.is_configured() and page != "⚙️ 设置":
        st.sidebar.markdown("---")
        st.sidebar.markdown(
            '<div class="warning-box">⚠️  请先配置API</div>',
            unsafe_allow_html=True
        )

    st.sidebar.markdown("---")
    st.sidebar.info("💡 **提示**: v3.0 高级版支持Web界面配置")

    # 页面路由
    if page == "📊 Dashboard":
        page_dashboard()
    elif page == "🔍 高级搜索":
        page_advanced_search()
    elif page == "📚 文献浏览":
        page_browser()
    elif page == "📈 数据分析":
        page_analysis()
    elif page == "⚙️ 设置":
        page_settings()
    else:
        page_about()

    # 页脚
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        '<p style="text-align: center; color: #999; font-size: 0.8rem;">'
        '© 2025 KOOI Research Assistant<br>BMAL1文献检索系统 v3.0'
        '</p>',
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
