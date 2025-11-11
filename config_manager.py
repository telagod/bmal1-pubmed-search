#!/usr/bin/env python3
"""
配置管理模块
==============
管理PubMed搜索的配置参数

作者: KOOI Research Assistant
日期: 2025-11-10
"""

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, Dict, Any
import json
import os
import importlib.util


@dataclass
class PubMedConfig:
    """PubMed API配置"""
    email: str = ""
    api_key: str = ""
    max_results: int = 100
    batch_size: int = 20
    sort_by: str = "relevance"  # relevance, pub_date, etc.

    def is_valid(self) -> bool:
        """检查配置是否有效"""
        return bool(self.email and self.api_key)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PubMedConfig':
        """从字典创建"""
        return cls(**data)


@dataclass
class SearchParams:
    """搜索参数"""
    query: str
    name: str = "Custom Search"
    max_results: int = 100
    min_date: str = ""  # YYYY/MM/DD
    max_date: str = ""  # YYYY/MM/DD
    sort_by: str = "relevance"
    retmax: int = 100

    def to_esearch_params(self) -> Dict[str, Any]:
        """转换为Entrez.esearch参数"""
        params = {
            'db': 'pubmed',
            'term': self.query,
            'retmax': min(self.retmax, self.max_results),
            'sort': self.sort_by
        }

        if self.min_date:
            params['mindate'] = self.min_date
        if self.max_date:
            params['maxdate'] = self.max_date

        return params

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SearchParams':
        """从字典创建"""
        return cls(**data)


class ConfigManager:
    """配置管理器"""

    def __init__(self, config_dir: Optional[Path] = None):
        """初始化配置管理器"""
        if config_dir is None:
            config_dir = Path(__file__).parent / "config"

        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)

        self.config_file = self.config_dir / "settings.json"
        self.search_history_file = self.config_dir / "search_history.json"

        self.pubmed_config: Optional[PubMedConfig] = None
        self.search_history: list = []

        self._load_config()
        self._load_search_history()

    def _load_config(self):
        """加载配置"""
        # 首先尝试从配置文件加载
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.pubmed_config = PubMedConfig.from_dict(data.get('pubmed', {}))
            except Exception as e:
                print(f"加载配置文件失败: {e}")
                self.pubmed_config = PubMedConfig()
        else:
            self.pubmed_config = PubMedConfig()

        # 优先从 Streamlit Secrets 加载（若可用且尚未配置）
        if (not self.pubmed_config.email) or (not self.pubmed_config.api_key):
            spec = importlib.util.find_spec("streamlit")
            if spec is not None:
                import streamlit as st  # noqa: WPS433
                if hasattr(st, "secrets"):
                    email = st.secrets.get('pubmed_email', '')
                    key = st.secrets.get('api_key', '')
                    if email:
                        self.pubmed_config.email = email
                    if key:
                        self.pubmed_config.api_key = key

        # 再尝试从.env文件加载（如果仍为空）
        if (not self.pubmed_config.email) or (not self.pubmed_config.api_key):
            self._load_from_env()

    def _load_from_env(self):
        """从.env文件加载配置"""
        # 优先使用当前模块所在目录的 .env
        # 回退到项目根目录的 .env（若存在）
        here_env = Path(__file__).parent / ".env"
        root_env = Path(__file__).parent.parent / ".env"
        env_path = here_env if here_env.exists() else root_env

        if env_path.exists():
            try:
                with open(env_path) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            if ':' in line:
                                key, value = line.split(":", 1)
                                key = key.strip()
                                value = value.strip()

                                if key == 'pubmed_email':
                                    self.pubmed_config.email = value
                                elif key == 'api_key':
                                    self.pubmed_config.api_key = value
            except Exception as e:
                print(f"从.env加载失败: {e}")

    def _load_search_history(self):
        """加载搜索历史"""
        if self.search_history_file.exists():
            try:
                with open(self.search_history_file, 'r', encoding='utf-8') as f:
                    self.search_history = json.load(f)
            except Exception as e:
                print(f"加载搜索历史失败: {e}")
                self.search_history = []
        else:
            self.search_history = []

    def save_config(self):
        """保存配置"""
        try:
            data = {
                'pubmed': self.pubmed_config.to_dict()
            }

            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            return True
        except Exception as e:
            print(f"保存配置失败: {e}")
            return False

    def save_search_history(self):
        """保存搜索历史"""
        try:
            with open(self.search_history_file, 'w', encoding='utf-8') as f:
                json.dump(self.search_history, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存搜索历史失败: {e}")
            return False

    def update_pubmed_config(self, email: str = None, api_key: str = None,
                            max_results: int = None, batch_size: int = None,
                            sort_by: str = None):
        """更新PubMed配置"""
        if email is not None:
            self.pubmed_config.email = email
        if api_key is not None:
            self.pubmed_config.api_key = api_key
        if max_results is not None:
            self.pubmed_config.max_results = max_results
        if batch_size is not None:
            self.pubmed_config.batch_size = batch_size
        if sort_by is not None:
            self.pubmed_config.sort_by = sort_by

        self.save_config()

    def add_search_to_history(self, search_params: SearchParams,
                             result_count: int, success_count: int):
        """添加搜索到历史"""
        from datetime import datetime

        history_item = {
            'timestamp': datetime.now().isoformat(),
            'search_params': search_params.to_dict(),
            'result_count': result_count,
            'success_count': success_count,
            'success_rate': f"{success_count/result_count*100:.1f}%" if result_count > 0 else "0%"
        }

        self.search_history.insert(0, history_item)  # 最新的放在前面

        # 只保留最近100条
        self.search_history = self.search_history[:100]

        self.save_search_history()

    def get_recent_searches(self, n: int = 10) -> list:
        """获取最近的搜索"""
        return self.search_history[:n]

    def clear_search_history(self):
        """清空搜索历史"""
        self.search_history = []
        self.save_search_history()

    def get_pubmed_config(self) -> PubMedConfig:
        """获取PubMed配置"""
        return self.pubmed_config

    def is_configured(self) -> bool:
        """检查是否已配置"""
        return self.pubmed_config.is_valid()

    def export_config(self, filepath: Path):
        """导出配置"""
        try:
            data = {
                'pubmed_config': self.pubmed_config.to_dict(),
                'search_history': self.search_history
            }

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            return True
        except Exception as e:
            print(f"导出配置失败: {e}")
            return False

    def import_config(self, filepath: Path):
        """导入配置"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if 'pubmed_config' in data:
                self.pubmed_config = PubMedConfig.from_dict(data['pubmed_config'])

            if 'search_history' in data:
                self.search_history = data['search_history']

            self.save_config()
            self.save_search_history()

            return True
        except Exception as e:
            print(f"导入配置失败: {e}")
            return False


# 全局配置管理器实例
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """获取配置管理器单例"""
    global _config_manager

    if _config_manager is None:
        _config_manager = ConfigManager()

    return _config_manager


if __name__ == "__main__":
    # 测试配置管理器
    manager = ConfigManager()

    print("当前配置:")
    print(f"  Email: {manager.pubmed_config.email}")
    print(f"  API Key: {'*' * len(manager.pubmed_config.api_key) if manager.pubmed_config.api_key else 'None'}")
    print(f"  配置有效: {manager.is_configured()}")

    if manager.search_history:
        print(f"\n搜索历史: {len(manager.search_history)} 条")
        for item in manager.search_history[:3]:
            print(f"  - {item['search_params']['name']}: {item['success_count']} 篇")
