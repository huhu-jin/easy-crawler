"""存储服务模块"""
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional


class StorageService:
    """Markdown 文件存储服务"""
    
    def __init__(self, base_dir: str = "data"):
        """
        初始化存储服务
        
        Args:
            base_dir: 数据存储根目录
        """
        self.base_dir = base_dir
    
    def ensure_directory(self, date: datetime) -> Path:
        """
        确保日期目录存在
        
        Args:
            date: 日期对象
        
        Returns:
            目录路径
        """
        date_str = date.strftime("%Y-%m-%d")
        dir_path = Path(self.base_dir) / date_str
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path
    
    def sanitize_filename(self, filename: str) -> str:
        """
        清理文件名，移除非法字符
        
        Args:
            filename: 原始文件名
        
        Returns:
            清理后的文件名
        """
        # 移除或替换非法字符
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # 限制长度
        if len(filename) > 200:
            filename = filename[:200]
        
        return filename
    
    def save_markdown(self, content: str, title: str, date: Optional[datetime] = None) -> str:
        """
        保存 Markdown 文件
        
        Args:
            content: Markdown 内容
            title: 文件标题（用于生成文件名）
            date: 日期，默认为今天
        
        Returns:
            保存的文件路径
        """
        if date is None:
            date = datetime.now()
        
        # 确保目录存在
        dir_path = self.ensure_directory(date)
        
        # 生成文件名
        filename = self.sanitize_filename(title)
        if not filename.endswith('.md'):
            filename += '.md'
        
        file_path = dir_path / filename
        
        # 如果文件已存在，添加序号
        counter = 1
        original_filename = filename
        while file_path.exists():
            name_without_ext = original_filename.rsplit('.md', 1)[0]
            filename = f"{name_without_ext}_{counter}.md"
            file_path = dir_path / filename
            counter += 1
        
        # 保存文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return str(file_path)
    
    def get_files_by_date(self, date: datetime) -> List[str]:
        """
        获取指定日期的所有 Markdown 文件
        
        Args:
            date: 日期对象
        
        Returns:
            文件名列表
        """
        date_str = date.strftime("%Y-%m-%d")
        dir_path = Path(self.base_dir) / date_str
        
        if not dir_path.exists():
            return []
        
        # 获取所有 .md 文件
        files = [f.name for f in dir_path.glob("*.md")]
        return sorted(files)
    
    def get_file_content(self, date: datetime, filename: str) -> Optional[str]:
        """
        读取指定文件的内容
        
        Args:
            date: 日期对象
            filename: 文件名
        
        Returns:
            文件内容，如果文件不存在返回 None
        """
        date_str = date.strftime("%Y-%m-%d")
        file_path = Path(self.base_dir) / date_str / filename
        
        if not file_path.exists():
            return None
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
