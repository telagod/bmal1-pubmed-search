#!/usr/bin/env python3
# Archived: superseded by pubmed_search_v2.py. Not used by app.
"""
BMAL1文献检索脚本
使用PubMed API进行文献检索并保存结果
"""

import os
from pathlib import Path
from datetime import datetime
from Bio import Entrez
import json


def load_env():
    """从.env文件加载配置"""
    env_path = Path(__file__).parent.parent / ".env"
    config = {}
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                key, value = line.split(":", 1)
                config[key.strip()] = value.strip()
    return config


def search_pubmed(query, email, api_key, max_results=100):
    """
    在PubMed中搜索文献

    参数:
        query: 搜索关键词
        email: PubMed API邮箱
        api_key: PubMed API密钥
        max_results: 最大返回结果数

    返回:
        文献ID列表和搜索统计
    """
    Entrez.email = email
    Entrez.api_key = api_key

    print(f"\n🔍 正在搜索关键词: {query}")
    print(f"📊 最大返回结果数: {max_results}")

    # 执行搜索
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

    print(f"✅ 找到 {count} 篇相关文献")
    print(f"📥 获取前 {len(id_list)} 篇文献信息")

    return id_list, count


def fetch_details(id_list, email, api_key, batch_size=20):
    """
    获取文献详细信息

    参数:
        id_list: 文献ID列表
        email: PubMed API邮箱
        api_key: PubMed API密钥
        batch_size: 批量获取大小

    返回:
        文献详细信息列表
    """
    Entrez.email = email
    Entrez.api_key = api_key

    all_papers = []

    # 分批获取
    for i in range(0, len(id_list), batch_size):
        batch_ids = id_list[i:i+batch_size]
        print(f"📖 正在获取第 {i+1}-{min(i+batch_size, len(id_list))} 篇文献详情...")

        handle = Entrez.efetch(
            db="pubmed",
            id=batch_ids,
            rettype="xml",
            retmode="xml"
        )

        records = Entrez.read(handle)
        handle.close()

        # 提取关键信息
        for record in records['PubmedArticle']:
            try:
                article = record['MedlineCitation']['Article']

                paper_info = {
                    'pmid': str(record['MedlineCitation']['PMID']),
                    'title': article['ArticleTitle'],
                    'abstract': article.get('Abstract', {}).get('AbstractText', [''])[0] if 'Abstract' in article else '',
                    'journal': article['Journal']['Title'],
                    'pub_date': '',
                    'authors': [],
                    'keywords': []
                }

                # 获取发表日期
                if 'PubDate' in article['Journal']['JournalIssue']:
                    pub_date = article['Journal']['JournalIssue']['PubDate']
                    year = pub_date.get('Year', '')
                    month = pub_date.get('Month', '')
                    paper_info['pub_date'] = f"{year}-{month}" if month else year

                # 获取作者
                if 'AuthorList' in article:
                    for author in article['AuthorList'][:5]:  # 只取前5个作者
                        if 'LastName' in author and 'Initials' in author:
                            paper_info['authors'].append(
                                f"{author['LastName']} {author['Initials']}"
                            )

                # 获取关键词
                if 'KeywordList' in record['MedlineCitation']:
                    paper_info['keywords'] = [
                        str(kw) for kw in record['MedlineCitation']['KeywordList'][0][:10]
                    ]

                all_papers.append(paper_info)
            except Exception as e:
                print(f"⚠️ 处理文献时出错: {e}")
                continue

    return all_papers


def save_results(papers, query, output_dir):
    """
    保存检索结果

    参数:
        papers: 文献信息列表
        query: 搜索关键词
        output_dir: 输出目录
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 保存JSON格式
    json_file = output_dir / f"bmal1_search_{timestamp}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump({
            'query': query,
            'timestamp': timestamp,
            'total_papers': len(papers),
            'papers': papers
        }, f, ensure_ascii=False, indent=2)

    print(f"\n💾 JSON结果已保存至: {json_file}")

    # 保存Markdown格式
    md_file = output_dir / f"bmal1_search_{timestamp}.md"
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write(f"# BMAL1文献检索结果\n\n")
        f.write(f"**检索时间**: {timestamp}\n")
        f.write(f"**检索关键词**: {query}\n")
        f.write(f"**文献数量**: {len(papers)}\n\n")
        f.write("---\n\n")

        for idx, paper in enumerate(papers, 1):
            f.write(f"## {idx}. {paper['title']}\n\n")
            f.write(f"**PMID**: {paper['pmid']}\n")
            f.write(f"**期刊**: {paper['journal']}\n")
            f.write(f"**发表日期**: {paper['pub_date']}\n")

            if paper['authors']:
                f.write(f"**作者**: {', '.join(paper['authors'])}\n")

            if paper['keywords']:
                f.write(f"**关键词**: {', '.join(paper['keywords'])}\n")

            if paper['abstract']:
                f.write(f"\n**摘要**:\n{paper['abstract']}\n")

            f.write(f"\n**PubMed链接**: https://pubmed.ncbi.nlm.nih.gov/{paper['pmid']}/\n")
            f.write("\n---\n\n")

    print(f"📄 Markdown结果已保存至: {md_file}")

    return json_file, md_file


def main():
    """主函数"""
    print("=" * 60)
    print("🧬 BMAL1文献检索工具")
    print("=" * 60)

    # 加载配置
    config = load_env()
    email = config.get('pubmed_email')
    api_key = config.get('api_key')

    if not email or not api_key:
        print("❌ 错误: 未找到邮箱或API密钥")
        return

    print(f"📧 邮箱: {email}")
    print(f"🔑 API密钥: {api_key[:10]}...")

    # 定义搜索策略
    queries = [
        "BMAL1 AND (circadian OR clock)",
        "BMAL1 AND Alzheimer",
        "BMAL1 AND (glymphatic OR clearance)",
        "BMAL1 AND (astrocyte OR BBB OR blood-brain barrier)"
    ]

    output_dir = Path(__file__).parent / "results"
    output_dir.mkdir(exist_ok=True)

    all_results = {}

    for query in queries:
        print(f"\n{'='*60}")
        print(f"搜索策略: {query}")
        print(f"{'='*60}")

        # 搜索文献
        id_list, total_count = search_pubmed(query, email, api_key, max_results=50)

        if not id_list:
            print("⚠️ 未找到相关文献")
            continue

        # 获取详情
        papers = fetch_details(id_list, email, api_key)

        # 保存结果
        json_file, md_file = save_results(papers, query, output_dir)

        all_results[query] = {
            'total_count': total_count,
            'fetched_count': len(papers),
            'json_file': str(json_file),
            'md_file': str(md_file)
        }

    # 保存总结
    summary_file = output_dir / f"search_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print("✅ 所有检索完成！")
    print(f"📊 检索摘要已保存至: {summary_file}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
