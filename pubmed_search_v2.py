#!/usr/bin/env python3
"""
BMAL1文献检索系统 - 优化版 v2.0
==================================
特性:
- 使用dataclass进行数据建模
- 健壮的文献解析（处理多种格式）
- SQLite数据库支持
- 多格式导出(JSON/MD/CSV)
- 完整的日志记录
- 为Streamlit可视化准备

作者: KOOI Research Assistant
日期: 2025-11-10
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime
from Bio import Entrez
import json
import sqlite3
from enum import Enum
import logging
import csv


# ==================== 配置日志 ====================
def setup_logging(log_dir: Path):
    """配置日志系统"""
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"pubmed_search_{datetime.now().strftime('%Y%m%d')}.log"

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)


# ==================== 数据模型 ====================
class SearchStrategy(Enum):
    """检索策略枚举"""
    CIRCADIAN = "BMAL1 AND (circadian OR clock)"
    ALZHEIMER = "BMAL1 AND Alzheimer"
    GLYMPHATIC = "BMAL1 AND (glymphatic OR clearance)"
    BBB = "BMAL1 AND (astrocyte OR BBB OR blood-brain barrier)"


@dataclass
class Author:
    """作者信息"""
    last_name: str
    first_name: str = ""
    initials: str = ""
    affiliation: str = ""

    def __str__(self):
        if self.initials:
            return f"{self.last_name} {self.initials}"
        return f"{self.last_name} {self.first_name}"


@dataclass
class PubDate:
    """发表日期"""
    year: str = ""
    month: str = ""
    day: str = ""

    def __str__(self):
        parts = [p for p in [self.year, self.month, self.day] if p]
        return "-".join(parts) if parts else "Unknown"

    @property
    def is_complete(self) -> bool:
        return bool(self.year)


@dataclass
class Paper:
    """文献信息完整模型"""
    pmid: str
    title: str
    abstract: str = ""
    journal: str = ""
    pub_date: PubDate = field(default_factory=PubDate)
    authors: List[Author] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    doi: str = ""
    mesh_terms: List[str] = field(default_factory=list)
    search_strategy: str = ""
    fetch_date: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def author_string(self) -> str:
        """获取作者字符串（前3位+et al）"""
        if not self.authors:
            return "No authors"

        authors_str = ", ".join(str(a) for a in self.authors[:3])
        if len(self.authors) > 3:
            authors_str += f" et al."
        return authors_str

    @property
    def pubmed_url(self) -> str:
        """PubMed链接"""
        return f"https://pubmed.ncbi.nlm.nih.gov/{self.pmid}/"

    @property
    def year(self) -> str:
        """发表年份"""
        return self.pub_date.year or "Unknown"

    @property
    def has_abstract(self) -> bool:
        """是否有摘要"""
        return bool(self.abstract and len(self.abstract) > 50)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于JSON导出和可视化）"""
        return {
            'pmid': self.pmid,
            'title': self.title,
            'abstract': self.abstract,
            'journal': self.journal,
            'year': self.year,
            'pub_date': str(self.pub_date),
            'authors': [str(a) for a in self.authors],
            'author_string': self.author_string,
            'keywords': self.keywords,
            'mesh_terms': self.mesh_terms,
            'doi': self.doi,
            'pubmed_url': self.pubmed_url,
            'search_strategy': self.search_strategy,
            'fetch_date': self.fetch_date,
            'has_abstract': self.has_abstract
        }


# ==================== 文献解析器 ====================
class PaperParser:
    """健壮的文献解析器 - 处理PubMed XML的各种格式"""

    def __init__(self, logger):
        self.logger = logger

    def parse_abstract(self, article: Dict) -> str:
        """
        解析摘要 - 处理多种格式

        AbstractText可能的格式:
        1. 字符串
        2. 字符串列表
        3. 带Label的结构化字典列表
        4. 空
        """
        if 'Abstract' not in article:
            return ""

        abstract_data = article['Abstract']
        if 'AbstractText' not in abstract_data:
            return ""

        abstract_text = abstract_data['AbstractText']

        # 空值检查
        if not abstract_text:
            return ""

        # 单个字符串
        if isinstance(abstract_text, str):
            return abstract_text.strip()

        # 列表格式
        if isinstance(abstract_text, list):
            parts = []
            for item in abstract_text:
                if isinstance(item, str):
                    # 简单字符串
                    parts.append(item.strip())
                elif isinstance(item, dict):
                    # 结构化摘要 (如 {'@Label': 'BACKGROUND', '#text': '...'})
                    label = item.get('@Label', '')
                    text = item.get('#text', '') or str(item)
                    if label and text:
                        parts.append(f"**{label}**: {text}")
                    elif text:
                        parts.append(text)
                else:
                    # 其他类型，转字符串
                    text = str(item).strip()
                    if text:
                        parts.append(text)

            return " ".join(parts)

        # 其他情况，尝试转字符串
        return str(abstract_text).strip()

    def parse_authors(self, article: Dict) -> List[Author]:
        """解析作者列表"""
        authors = []

        if 'AuthorList' not in article:
            return authors

        for author_data in article['AuthorList']:
            try:
                # 跳过集体作者
                if 'CollectiveName' in author_data:
                    self.logger.debug(f"跳过集体作者: {author_data.get('CollectiveName')}")
                    continue

                # 提取作者信息
                last_name = author_data.get('LastName', '')
                if not last_name:
                    continue

                # 提取机构信息
                affiliation = ""
                if 'AffiliationInfo' in author_data:
                    aff_list = author_data['AffiliationInfo']
                    if aff_list and isinstance(aff_list, list):
                        affiliation = aff_list[0].get('Affiliation', '')

                author = Author(
                    last_name=last_name,
                    first_name=author_data.get('ForeName', ''),
                    initials=author_data.get('Initials', ''),
                    affiliation=affiliation
                )
                authors.append(author)

            except Exception as e:
                self.logger.warning(f"解析作者时出错: {e}")
                continue

        return authors

    def parse_pub_date(self, article: Dict) -> PubDate:
        """解析发表日期 - 处理多种日期格式"""
        pub_date = PubDate()

        try:
            journal = article.get('Journal', {})
            journal_issue = journal.get('JournalIssue', {})
            date_data = journal_issue.get('PubDate', {})

            if not date_data:
                return pub_date

            # 优先使用标准格式
            if 'Year' in date_data:
                pub_date.year = str(date_data['Year'])
                pub_date.month = str(date_data.get('Month', ''))
                pub_date.day = str(date_data.get('Day', ''))

            # 处理MedlineDate (如 "2020 Jan-Feb", "2020 Spring")
            elif 'MedlineDate' in date_data:
                medline_date = str(date_data['MedlineDate'])
                parts = medline_date.split()
                if parts:
                    # 第一部分通常是年份
                    pub_date.year = parts[0]
                    if len(parts) > 1:
                        # 第二部分可能是月份或季节
                        pub_date.month = parts[1]

        except Exception as e:
            self.logger.warning(f"解析日期时出错: {e}")

        return pub_date

    def parse_keywords(self, record: Dict) -> List[str]:
        """解析关键词"""
        keywords = []

        try:
            citation = record.get('MedlineCitation', {})

            if 'KeywordList' in citation:
                for keyword_list in citation['KeywordList']:
                    for kw in keyword_list:
                        # 处理不同格式的关键词
                        if isinstance(kw, dict):
                            keyword_str = kw.get('#text', '') or str(kw)
                        else:
                            keyword_str = str(kw)

                        keyword_str = keyword_str.strip()
                        if keyword_str and keyword_str not in keywords:
                            keywords.append(keyword_str)

        except Exception as e:
            self.logger.warning(f"解析关键词时出错: {e}")

        return keywords

    def parse_mesh_terms(self, record: Dict) -> List[str]:
        """解析MeSH主题词"""
        mesh_terms = []

        try:
            citation = record.get('MedlineCitation', {})

            if 'MeshHeadingList' in citation:
                for mesh_heading in citation['MeshHeadingList']:
                    if 'DescriptorName' in mesh_heading:
                        descriptor = mesh_heading['DescriptorName']

                        # 提取主题词文本
                        if isinstance(descriptor, dict):
                            term = descriptor.get('#text', '') or str(descriptor)
                        else:
                            term = str(descriptor)

                        term = term.strip()
                        if term and term not in mesh_terms:
                            mesh_terms.append(term)

        except Exception as e:
            self.logger.warning(f"解析MeSH时出错: {e}")

        return mesh_terms

    def parse_doi(self, record: Dict) -> str:
        """解析DOI"""
        try:
            # 方法1: 从Article的ELocationID获取
            article = record.get('MedlineCitation', {}).get('Article', {})
            if 'ELocationID' in article:
                for elocation in article['ELocationID']:
                    if isinstance(elocation, dict):
                        if elocation.get('@EIdType') == 'doi':
                            return str(elocation.get('#text', ''))
                    else:
                        eloc_str = str(elocation)
                        if 'doi' in eloc_str.lower():
                            return eloc_str

            # 方法2: 从PubmedData的ArticleIdList获取
            pubmed_data = record.get('PubmedData', {})
            if 'ArticleIdList' in pubmed_data:
                for article_id in pubmed_data['ArticleIdList']:
                    if isinstance(article_id, dict):
                        if article_id.get('@IdType') == 'doi':
                            return str(article_id.get('#text', ''))

        except Exception as e:
            self.logger.warning(f"解析DOI时出错: {e}")

        return ""

    def parse_paper(self, record: Dict, search_strategy: str = "") -> Optional[Paper]:
        """解析单篇文献 - 主函数"""
        try:
            citation = record.get('MedlineCitation', {})
            article = citation.get('Article', {})

            # 必需字段检查
            if 'PMID' not in citation:
                self.logger.warning("缺少PMID，跳过此文献")
                return None

            pmid = str(citation['PMID'])

            if 'ArticleTitle' not in article:
                self.logger.warning(f"PMID {pmid} 缺少标题，跳过")
                return None

            # 创建Paper对象
            paper = Paper(
                pmid=pmid,
                title=str(article['ArticleTitle']).strip(),
                abstract=self.parse_abstract(article),
                journal=article.get('Journal', {}).get('Title', ''),
                pub_date=self.parse_pub_date(article),
                authors=self.parse_authors(article),
                keywords=self.parse_keywords(record),
                mesh_terms=self.parse_mesh_terms(record),
                doi=self.parse_doi(record),
                search_strategy=search_strategy
            )

            self.logger.debug(f"成功解析: PMID {pmid}")
            return paper

        except Exception as e:
            self.logger.error(f"解析文献时出错: {e}", exc_info=True)
            return None


# ==================== 数据库管理 ====================
class PaperDatabase:
    """SQLite数据库管理"""

    def __init__(self, db_path: Path, logger):
        self.db_path = db_path
        self.logger = logger
        self.conn = None
        self._init_db()

    def _init_db(self):
        """初始化数据库schema"""
        self.conn = sqlite3.connect(str(self.db_path))
        cursor = self.conn.cursor()

        # 创建papers表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS papers (
                pmid TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                abstract TEXT,
                journal TEXT,
                pub_year TEXT,
                pub_date TEXT,
                authors TEXT,
                keywords TEXT,
                mesh_terms TEXT,
                doi TEXT,
                search_strategy TEXT,
                fetch_date TEXT,
                pubmed_url TEXT,
                has_abstract INTEGER
            )
        ''')

        # 创建搜索历史表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS search_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_name TEXT,
                query TEXT,
                total_count INTEGER,
                fetched_count INTEGER,
                success_rate REAL,
                search_date TEXT
            )
        ''')

        # 创建索引提升查询性能
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pub_year ON papers(pub_year)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_strategy ON papers(search_strategy)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_journal ON papers(journal)')

        self.conn.commit()
        self.logger.info(f"数据库初始化完成: {self.db_path}")

    def save_paper(self, paper: Paper):
        """保存单篇文献"""
        cursor = self.conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO papers
            (pmid, title, abstract, journal, pub_year, pub_date,
             authors, keywords, mesh_terms, doi, search_strategy,
             fetch_date, pubmed_url, has_abstract)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            paper.pmid,
            paper.title,
            paper.abstract,
            paper.journal,
            paper.year,
            str(paper.pub_date),
            json.dumps([str(a) for a in paper.authors]),
            json.dumps(paper.keywords),
            json.dumps(paper.mesh_terms),
            paper.doi,
            paper.search_strategy,
            paper.fetch_date,
            paper.pubmed_url,
            1 if paper.has_abstract else 0
        ))

        self.conn.commit()

    def save_papers(self, papers: List[Paper]):
        """批量保存文献"""
        for paper in papers:
            self.save_paper(paper)
        self.logger.info(f"保存了 {len(papers)} 篇文献到数据库")

    def save_search_history(self, strategy_name: str, query: str,
                          total_count: int, fetched_count: int):
        """保存搜索历史"""
        cursor = self.conn.cursor()

        success_rate = (fetched_count / total_count * 100) if total_count > 0 else 0

        cursor.execute('''
            INSERT INTO search_history
            (strategy_name, query, total_count, fetched_count, success_rate, search_date)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            strategy_name,
            query,
            total_count,
            fetched_count,
            success_rate,
            datetime.now().isoformat()
        ))

        self.conn.commit()

    def get_all_papers(self) -> List[Dict]:
        """获取所有文献（用于可视化）"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM papers')

        columns = [desc[0] for desc in cursor.description]
        papers = []

        for row in cursor.fetchall():
            paper_dict = dict(zip(columns, row))
            # 解析JSON字段
            paper_dict['authors'] = json.loads(paper_dict['authors'])
            paper_dict['keywords'] = json.loads(paper_dict['keywords'])
            paper_dict['mesh_terms'] = json.loads(paper_dict['mesh_terms'])
            papers.append(paper_dict)

        return papers

    def get_statistics(self) -> Dict:
        """获取统计信息（用于Dashboard）"""
        cursor = self.conn.cursor()

        stats = {}

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

        return stats

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            self.logger.info("数据库连接已关闭")


# ==================== PubMed API接口 ====================
class PubMedAPI:
    """PubMed API封装"""

    def __init__(self, email: str, api_key: str, logger):
        self.email = email
        self.api_key = api_key
        self.logger = logger
        Entrez.email = email
        Entrez.api_key = api_key
        self.logger.info(f"PubMed API初始化: {email}")

    def search(self, query: str, max_results: int = 100) -> tuple:
        """搜索文献ID"""
        self.logger.info(f"开始搜索: {query}")

        try:
            handle = Entrez.esearch(
                db="pubmed",
                term=query,
                retmax=max_results,
                sort="relevance"
            )

            results = Entrez.read(handle)
            handle.close()

            id_list = results["IdList"]
            count = int(results["Count"])

            self.logger.info(f"✅ 找到 {count} 篇文献，获取前 {len(id_list)} 篇ID")
            return id_list, count

        except Exception as e:
            self.logger.error(f"❌ 搜索失败: {e}")
            return [], 0

    def fetch_details(self, id_list: List[str],
                     search_strategy: str = "",
                     batch_size: int = 20) -> List[Paper]:
        """批量获取文献详情"""
        papers = []
        total = len(id_list)
        parser = PaperParser(self.logger)

        for i in range(0, total, batch_size):
            batch_ids = id_list[i:i+batch_size]
            batch_num = i // batch_size + 1
            total_batches = (total + batch_size - 1) // batch_size

            self.logger.info(f"📖 获取第 {batch_num}/{total_batches} 批 ({len(batch_ids)} 篇)...")

            try:
                handle = Entrez.efetch(
                    db="pubmed",
                    id=batch_ids,
                    rettype="xml",
                    retmode="xml"
                )

                records = Entrez.read(handle)
                handle.close()

                # 解析每篇文献
                for record in records.get('PubmedArticle', []):
                    paper = parser.parse_paper(record, search_strategy)
                    if paper:
                        papers.append(paper)

                self.logger.info(f"✓ 批次 {batch_num} 完成，累计解析 {len(papers)} 篇")

            except Exception as e:
                self.logger.error(f"❌ 批次 {batch_num} 失败: {e}")
                continue

        success_rate = len(papers) / total * 100 if total > 0 else 0
        self.logger.info(f"🎯 总共成功 {len(papers)}/{total} 篇 ({success_rate:.1f}%)")

        return papers


# ==================== 文件导出器 ====================
class FileExporter:
    """多格式文件导出"""

    def __init__(self, logger):
        self.logger = logger

    def export_json(self, papers: List[Paper], filepath: Path, query: str = ""):
        """导出为JSON（用于程序间数据交换）"""
        data = {
            'metadata': {
                'query': query,
                'export_date': datetime.now().isoformat(),
                'total_papers': len(papers),
                'format_version': '2.0'
            },
            'papers': [p.to_dict() for p in papers]
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        self.logger.info(f"📄 导出JSON: {filepath} ({len(papers)} 篇)")

    def export_markdown(self, papers: List[Paper], filepath: Path, query: str = ""):
        """导出为Markdown（用于阅读和文档）"""
        with open(filepath, 'w', encoding='utf-8') as f:
            # 头部信息
            f.write(f"# 文献检索结果\n\n")
            f.write(f"**检索时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**检索策略**: {query}\n")
            f.write(f"**文献数量**: {len(papers)}\n\n")
            f.write("---\n\n")

            # 文献列表
            for idx, paper in enumerate(papers, 1):
                f.write(f"## {idx}. {paper.title}\n\n")

                # 基本信息
                f.write(f"- **PMID**: [{paper.pmid}]({paper.pubmed_url})\n")
                if paper.doi:
                    f.write(f"- **DOI**: {paper.doi}\n")
                f.write(f"- **期刊**: {paper.journal}\n")
                f.write(f"- **发表日期**: {paper.pub_date}\n")

                # 作者
                if paper.authors:
                    f.write(f"- **作者**: {paper.author_string}\n")

                # 关键词
                if paper.keywords:
                    kw_str = ", ".join(paper.keywords[:10])
                    if len(paper.keywords) > 10:
                        kw_str += f" (共{len(paper.keywords)}个)"
                    f.write(f"- **关键词**: {kw_str}\n")

                # MeSH主题词
                if paper.mesh_terms:
                    mesh_str = ", ".join(paper.mesh_terms[:8])
                    if len(paper.mesh_terms) > 8:
                        mesh_str += f" (共{len(paper.mesh_terms)}个)"
                    f.write(f"- **MeSH主题词**: {mesh_str}\n")

                # 摘要
                if paper.abstract:
                    f.write(f"\n### 摘要\n\n{paper.abstract}\n")

                f.write("\n---\n\n")

        self.logger.info(f"📝 导出Markdown: {filepath} ({len(papers)} 篇)")

    def export_csv(self, papers: List[Paper], filepath: Path):
        """导出为CSV（用于Excel和数据分析）"""
        with open(filepath, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)

            # 表头
            writer.writerow([
                'PMID', '标题', '期刊', '发表年份', '发表日期',
                '作者', '关键词数量', '关键词', 'MeSH主题词数量',
                'MeSH主题词', 'DOI', '有摘要', 'PubMed链接', '摘要预览'
            ])

            # 数据行
            for paper in papers:
                writer.writerow([
                    paper.pmid,
                    paper.title,
                    paper.journal,
                    paper.year,
                    str(paper.pub_date),
                    paper.author_string,
                    len(paper.keywords),
                    "; ".join(paper.keywords),
                    len(paper.mesh_terms),
                    "; ".join(paper.mesh_terms),
                    paper.doi,
                    "是" if paper.has_abstract else "否",
                    paper.pubmed_url,
                    (paper.abstract[:200] + '...') if len(paper.abstract) > 200 else paper.abstract
                ])

        self.logger.info(f"📊 导出CSV: {filepath} ({len(papers)} 篇)")


# ==================== 配置管理 ====================
def load_env(env_path: Path) -> Dict[str, str]:
    """从.env文件加载配置"""
    config = {}

    if not env_path.exists():
        print(f"⚠️  .env文件不存在: {env_path}")
        return config

    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and ':' in line:
                key, value = line.split(":", 1)
                config[key.strip()] = value.strip()

    return config


# ==================== 主函数 ====================
def main():
    """主函数 - 执行完整检索流程"""
    print("=" * 70)
    print("🧬 BMAL1文献检索系统 v2.0 - 优化版")
    print("=" * 70)
    print()

    # 1. 初始化
    script_dir = Path(__file__).parent
    output_dir = script_dir / "results"
    output_dir.mkdir(exist_ok=True)

    # 设置日志
    logger = setup_logging(output_dir)

    # 2. 加载配置
    env_path = script_dir.parent / ".env"
    config = load_env(env_path)

    email = config.get('pubmed_email')
    api_key = config.get('api_key')

    if not email or not api_key:
        logger.error("❌ 配置错误: 未找到邮箱或API密钥")
        print("请检查 .env 文件配置")
        return

    # 3. 初始化组件
    api = PubMedAPI(email, api_key, logger)
    db_path = output_dir / "bmal1_papers.db"
    db = PaperDatabase(db_path, logger)
    exporter = FileExporter(logger)

    # 4. 执行检索
    all_results = {}

    for strategy in SearchStrategy:
        print(f"\n{'='*70}")
        print(f"📚 检索策略: {strategy.name}")
        print(f"🔍 查询语句: {strategy.value}")
        print(f"{'='*70}\n")

        # 搜索ID
        id_list, total_count = api.search(strategy.value, max_results=50)

        if not id_list:
            logger.warning(f"⚠️  未找到文献: {strategy.value}")
            continue

        # 获取详情
        papers = api.fetch_details(id_list, search_strategy=strategy.name)

        if not papers:
            logger.warning(f"⚠️  未成功解析任何文献")
            continue

        # 保存到数据库
        db.save_papers(papers)
        db.save_search_history(strategy.name, strategy.value, total_count, len(papers))

        # 导出文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"bmal1_{strategy.name.lower()}_{timestamp}"

        json_file = output_dir / f"{base_name}.json"
        md_file = output_dir / f"{base_name}.md"
        csv_file = output_dir / f"{base_name}.csv"

        exporter.export_json(papers, json_file, strategy.value)
        exporter.export_markdown(papers, md_file, strategy.value)
        exporter.export_csv(papers, csv_file)

        # 记录结果
        all_results[strategy.name] = {
            'query': strategy.value,
            'total_count': total_count,
            'fetched_count': len(papers),
            'success_rate': f"{len(papers)/len(id_list)*100:.1f}%",
            'files': {
                'json': json_file.name,
                'markdown': md_file.name,
                'csv': csv_file.name
            }
        }

        logger.info(f"✅ {strategy.name} 完成\n")

    # 5. 生成总结报告
    summary_file = output_dir / f"search_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    summary_data = {
        'metadata': {
            'search_date': datetime.now().isoformat(),
            'database_path': str(db_path),
            'version': '2.0'
        },
        'statistics': db.get_statistics(),
        'search_results': all_results
    }

    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary_data, f, ensure_ascii=False, indent=2)

    logger.info(f"📊 检索摘要: {summary_file}")

    # 6. 清理
    db.close()

    # 7. 输出总结
    print(f"\n{'='*70}")
    print("✅ 所有检索任务完成！")
    print(f"{'='*70}")
    print(f"\n📊 统计信息:")
    stats = summary_data['statistics']
    print(f"  - 总文献数: {stats['total_papers']}")
    print(f"  - 有摘要: {stats['with_abstract']}")
    print(f"  - 数据库: {db_path}")
    print(f"  - 输出目录: {output_dir}")
    print(f"\n💡 下一步: 运行 Streamlit 可视化界面查看结果")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
