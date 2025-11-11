#!/usr/bin/env python3
"""
本地数据管理模块
================
管理用户的本地数据（数据库上传/下载，不占用云端资源）

作者: KOOI Research Assistant
日期: 2025-11-10
"""

import streamlit as st
from pathlib import Path
import sqlite3
import tempfile
import shutil
from typing import Optional
import io
from datetime import datetime


class LocalDataManager:
    """本地数据管理器"""

    def __init__(self):
        """初始化数据管理器"""
        # 使用session_state存储临时数据库路径
        if 'db_path' not in st.session_state:
            st.session_state['db_path'] = None

        if 'db_initialized' not in st.session_state:
            st.session_state['db_initialized'] = False

    def get_db_path(self) -> Optional[Path]:
        """
        获取当前数据库路径

        Returns:
            数据库路径，如果没有则返回None
        """
        p = st.session_state.get('db_path')
        return Path(p) if p else None

    def has_database(self) -> bool:
        """检查是否有可用的数据库"""
        p = st.session_state.get('db_path')
        return bool(p) and Path(p).exists()

    def create_temp_database(self) -> Path:
        """
        创建临时数据库

        Returns:
            临时数据库路径
        """
        # 创建临时文件
        temp_file = tempfile.NamedTemporaryFile(
            delete=False,
            suffix='.db',
            prefix='bmal1_'
        )
        temp_path = Path(temp_file.name)
        temp_file.close()

        # 初始化数据库结构
        self._init_database_schema(temp_path)

        # 保存到session_state
        st.session_state['db_path'] = str(temp_path)
        st.session_state['db_initialized'] = True

        return temp_path

    def _init_database_schema(self, db_path: Path):
        """初始化数据库结构"""
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

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

        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pub_year ON papers(pub_year)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_strategy ON papers(search_strategy)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_journal ON papers(journal)')

        conn.commit()
        conn.close()

    def upload_database(self, uploaded_file) -> bool:
        """
        上传数据库文件

        Args:
            uploaded_file: Streamlit上传的文件对象

        Returns:
            是否成功
        """
        try:
            # 创建临时文件
            temp_file = tempfile.NamedTemporaryFile(
                delete=False,
                suffix='.db',
                prefix='bmal1_uploaded_'
            )
            temp_path = Path(temp_file.name)

            # 写入上传的数据
            temp_file.write(uploaded_file.getvalue())
            temp_file.close()

            # 验证是否为有效的数据库文件
            if self._validate_database(temp_path):
                st.session_state['db_path'] = str(temp_path)
                st.session_state['db_initialized'] = True
                st.session_state['db_token'] = datetime.now().isoformat()
                return True
            else:
                # 删除无效文件
                temp_path.unlink()
                return False

        except Exception as e:
            st.error(f"上传失败: {e}")
            return False

    def _validate_database(self, db_path: Path) -> bool:
        """验证数据库文件是否有效"""
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # 检查必需的表是否存在
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name IN ('papers', 'search_history')
            """)
            tables = [row[0] for row in cursor.fetchall()]

            conn.close()

            return 'papers' in tables

        except Exception:
            return False

    def download_database(self) -> Optional[bytes]:
        """
        下载数据库文件

        Returns:
            数据库文件的字节内容，如果没有则返回None
        """
        if not self.has_database():
            return None

        try:
            p = st.session_state.get('db_path')
            if not p:
                return None
            db_path = Path(p)
            with open(db_path, 'rb') as f:
                return f.read()
        except Exception as e:
            st.error(f"下载失败: {e}")
            return None

    def get_database_info(self) -> dict:
        """获取数据库信息"""
        if not self.has_database():
            return {
                'exists': False,
                'paper_count': 0,
                'search_count': 0,
                'size': 0
            }

        try:
            p = st.session_state.get('db_path')
            db_path = Path(p) if p else None
            if not db_path:
                return {
                    'exists': False,
                    'paper_count': 0,
                    'search_count': 0,
                    'size': 0
                }
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # 获取文献数
            cursor.execute('SELECT COUNT(*) FROM papers')
            paper_count = cursor.fetchone()[0]

            # 获取搜索历史数
            cursor.execute('SELECT COUNT(*) FROM search_history')
            search_count = cursor.fetchone()[0]

            conn.close()

            # 获取文件大小
            size = db_path.stat().st_size if db_path.exists() else 0

            return {
                'exists': True,
                'paper_count': paper_count,
                'search_count': search_count,
                'size': size,
                'size_mb': round(size / 1024 / 1024, 2)
            }

        except Exception as e:
            return {
                'exists': False,
                'error': str(e)
            }

    def clear_database(self):
        """清空当前数据库"""
        if self.has_database():
            try:
                p = st.session_state.get('db_path')
                if p:
                    Path(p).unlink()
            except Exception:
                pass

        st.session_state['db_path'] = None
        st.session_state['db_initialized'] = False
        st.session_state['db_token'] = datetime.now().isoformat()

    def ensure_database(self) -> Path:
        """
        确保有可用的数据库

        Returns:
            数据库路径
        """
        if not self.has_database():
            return self.create_temp_database()
        p = st.session_state.get('db_path')
        return Path(p) if p else None


# 全局数据管理器实例
_local_data_manager: Optional[LocalDataManager] = None


def get_data_manager() -> LocalDataManager:
    """获取数据管理器单例"""
    global _local_data_manager

    if _local_data_manager is None:
        _local_data_manager = LocalDataManager()

    return _local_data_manager


if __name__ == "__main__":
    # 测试
    manager = LocalDataManager()

    if not manager.has_database():
        print("创建新数据库...")
        db_path = manager.create_temp_database()
        print(f"数据库路径: {db_path}")

    info = manager.get_database_info()
    print(f"数据库信息: {info}")
