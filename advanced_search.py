#!/usr/bin/env python3
"""
高级PubMed搜索引擎
==================
支持灵活配置的文献检索系统

作者: KOOI Research Assistant
日期: 2025-11-10
"""

from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime
from Bio import Entrez
import logging

from config_manager import ConfigManager, SearchParams, PubMedConfig

# 从v2导入现有的解析器和数据模型
import sys
sys.path.insert(0, str(Path(__file__).parent))

try:
    from pubmed_search_v2 import (
        PaperParser, Paper, PaperDatabase,
        FileExporter, setup_logging
    )
except ImportError:
    print("警告: 无法导入pubmed_search_v2模块")
    PaperParser = None
    Paper = None


class AdvancedPubMedSearchEngine:
    """高级PubMed搜索引擎"""

    def __init__(self, config: Optional[PubMedConfig] = None,
                 logger: Optional[logging.Logger] = None):
        """
        初始化搜索引擎

        Args:
            config: PubMed配置，如果为None则从ConfigManager加载
            logger: 日志记录器
        """
        self.config_manager = ConfigManager()

        if config is None:
            self.config = self.config_manager.get_pubmed_config()
        else:
            self.config = config

        self.logger = logger or logging.getLogger(__name__)

        # 设置Entrez
        if self.config.email:
            Entrez.email = self.config.email
        if self.config.api_key:
            Entrez.api_key = self.config.api_key

        self.parser = PaperParser(self.logger) if PaperParser else None

    def validate_config(self) -> tuple[bool, str]:
        """
        验证配置

        Returns:
            (是否有效, 错误信息)
        """
        if not self.config.email:
            return False, "未配置邮箱地址"

        if not self.config.api_key:
            return False, "未配置API密钥"

        if '@' not in self.config.email:
            return False, "邮箱格式无效"

        return True, ""

    def search(self, search_params: SearchParams) -> tuple[List[str], int]:
        """
        搜索文献ID

        Args:
            search_params: 搜索参数

        Returns:
            (ID列表, 总数量)
        """
        # 验证配置
        valid, error_msg = self.validate_config()
        if not valid:
            self.logger.error(f"配置验证失败: {error_msg}")
            raise ValueError(f"配置验证失败: {error_msg}")

        self.logger.info(f"开始搜索: {search_params.name}")
        self.logger.info(f"查询: {search_params.query}")

        try:
            # 构建搜索参数
            esearch_params = search_params.to_esearch_params()

            handle = Entrez.esearch(**esearch_params)
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
                     batch_size: Optional[int] = None) -> List[Paper]:
        """
        批量获取文献详情

        Args:
            id_list: 文献ID列表
            search_strategy: 搜索策略名称
            batch_size: 批次大小，如果为None则使用配置值

        Returns:
            文献列表
        """
        if not self.parser:
            self.logger.error("解析器未初始化")
            return []

        papers = []
        total = len(id_list)

        if batch_size is None:
            batch_size = self.config.batch_size

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
                    paper = self.parser.parse_paper(record, search_strategy)
                    if paper:
                        papers.append(paper)

                self.logger.info(f"✓ 批次 {batch_num} 完成，累计解析 {len(papers)} 篇")

            except Exception as e:
                self.logger.error(f"❌ 批次 {batch_num} 失败: {e}")
                continue

        success_rate = len(papers) / total * 100 if total > 0 else 0
        self.logger.info(f"🎯 总共成功 {len(papers)}/{total} 篇 ({success_rate:.1f}%)")

        return papers

    def execute_search(self, search_params: SearchParams,
                      db_path: Optional[Path] = None,
                      export_dir: Optional[Path] = None,
                      save_to_db: bool = True,
                      export_formats: List[str] = None) -> Dict[str, Any]:
        """
        执行完整的搜索流程

        Args:
            search_params: 搜索参数
            db_path: 数据库路径
            export_dir: 导出目录
            save_to_db: 是否保存到数据库
            export_formats: 导出格式列表 ['json', 'md', 'csv']

        Returns:
            搜索结果字典
        """
        if export_formats is None:
            export_formats = ['json', 'md', 'csv']

        # 搜索ID
        id_list, total_count = self.search(search_params)

        if not id_list:
            self.logger.warning(f"⚠️  未找到文献: {search_params.query}")
            return {
                'success': False,
                'error': '未找到文献',
                'total_count': 0,
                'fetched_count': 0
            }

        # 获取详情
        papers = self.fetch_details(id_list, search_strategy=search_params.name)

        if not papers:
            self.logger.warning(f"⚠️  未成功解析任何文献")
            return {
                'success': False,
                'error': '解析失败',
                'total_count': total_count,
                'fetched_count': 0
            }

        # 保存到数据库
        if save_to_db and db_path and PaperDatabase:
            db = PaperDatabase(db_path, self.logger)
            db.save_papers(papers)
            db.save_search_history(
                search_params.name,
                search_params.query,
                total_count,
                len(papers)
            )
            db.close()

        # 导出文件
        exported_files = {}
        if export_dir and FileExporter:
            export_dir.mkdir(exist_ok=True)
            exporter = FileExporter(self.logger)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = "".join(c if c.isalnum() or c in ('-', '_') else '_'
                               for c in search_params.name)
            base_name = f"{safe_name}_{timestamp}"

            if 'json' in export_formats:
                json_file = export_dir / f"{base_name}.json"
                exporter.export_json(papers, json_file, search_params.query)
                exported_files['json'] = str(json_file)

            if 'md' in export_formats:
                md_file = export_dir / f"{base_name}.md"
                exporter.export_markdown(papers, md_file, search_params.query)
                exported_files['md'] = str(md_file)

            if 'csv' in export_formats:
                csv_file = export_dir / f"{base_name}.csv"
                exporter.export_csv(papers, csv_file)
                exported_files['csv'] = str(csv_file)

        # 添加到搜索历史
        self.config_manager.add_search_to_history(
            search_params,
            len(id_list),
            len(papers)
        )

        return {
            'success': True,
            'total_count': total_count,
            'fetched_count': len(papers),
            'success_rate': f"{len(papers)/len(id_list)*100:.1f}%",
            'papers': papers,
            'exported_files': exported_files
        }

    def build_query(self, keywords: List[str],
                   logic: str = "AND",
                   filters: Optional[Dict[str, Any]] = None) -> str:
        """
        构建PubMed查询字符串

        Args:
            keywords: 关键词列表
            logic: 逻辑运算符 (AND/OR/NOT)
            filters: 其他过滤器 {'journal': 'Nature', 'author': 'Smith'}

        Returns:
            查询字符串
        """
        # 基础关键词查询
        if not keywords:
            return ""

        query_parts = [f" {logic} ".join(keywords)]

        # 添加过滤器
        if filters:
            for field, value in filters.items():
                if value:
                    query_parts.append(f"{value}[{field}]")

        return " AND ".join(query_parts)

    @staticmethod
    def get_field_tags() -> Dict[str, str]:
        """
        获取PubMed字段标签

        Returns:
            字段标签字典
        """
        return {
            'Title': 'Title',
            'Abstract': 'Abstract',
            'Author': 'Author',
            'Journal': 'Journal',
            'Affiliation': 'Affiliation',
            'MeSH Terms': 'MeSH Terms',
            'All Fields': 'All Fields',
            'Publication Date': 'Publication Date',
            'Publication Type': 'Publication Type'
        }


def create_search_engine(config: Optional[PubMedConfig] = None) -> AdvancedPubMedSearchEngine:
    """
    创建搜索引擎实例

    Args:
        config: PubMed配置

    Returns:
        搜索引擎实例
    """
    # 设置日志
    logger = logging.getLogger("PubMedSearch")
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return AdvancedPubMedSearchEngine(config, logger)


if __name__ == "__main__":
    # 测试搜索引擎
    print("=== 测试高级PubMed搜索引擎 ===\n")

    # 创建搜索引擎
    engine = create_search_engine()

    # 验证配置
    valid, error_msg = engine.validate_config()
    print(f"配置验证: {'✅ 有效' if valid else f'❌ {error_msg}'}\n")

    if valid:
        # 测试查询构建
        query = engine.build_query(
            keywords=['BMAL1', 'Alzheimer'],
            logic='AND'
        )
        print(f"构建的查询: {query}\n")

        # 创建搜索参数
        search_params = SearchParams(
            query=query,
            name="Test Search",
            max_results=5
        )

        # 执行搜索
        print("执行测试搜索（仅前5篇）...\n")
        result = engine.execute_search(
            search_params,
            save_to_db=False,
            export_formats=[]
        )

        print(f"\n搜索结果:")
        print(f"  总数: {result['total_count']}")
        print(f"  获取: {result['fetched_count']}")
        print(f"  成功率: {result.get('success_rate', 'N/A')}")
