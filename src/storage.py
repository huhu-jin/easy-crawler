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
    
    def ensure_directory(self, date: datetime, file_dir: str = "") -> Path:
        """
        确保日期目录存在
        
        Args:
            date: 日期对象
            file_dir: 网站子目录名（来自 config.json 的 file_dir 字段）
        
        Returns:
            目录路径
        """
        date_str = date.strftime("%Y-%m-%d")
        if file_dir:
            dir_path = Path(self.base_dir) / file_dir / date_str
        else:
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
    
    def save_markdown(self, content: str, title: str, date: Optional[datetime] = None, file_dir: str = "") -> str:
        """
        保存 Markdown 文件
        
        Args:
            content: Markdown 内容
            title: 文件标题（用于生成文件名）
            date: 日期，默认为今天
            file_dir: 网站子目录名（来自 config.json 的 file_dir 字段）
        
        Returns:
            保存的文件路径
        """
        if date is None:
            date = datetime.now()
        
        # 确保目录存在
        dir_path = self.ensure_directory(date, file_dir)
        
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
    
    def get_files_by_date(self, date: datetime, file_dir: str = "") -> List[str]:
        """
        获取指定日期的所有 Markdown 文件
        
        Args:
            date: 日期对象
            file_dir: 网站子目录名（来自 config.json 的 file_dir 字段），为空则列出所有子目录
        
        Returns:
            文件名列表（当 file_dir 为空时，格式为 "subdir/filename.md"）
        """
        date_str = date.strftime("%Y-%m-%d")
        
        if file_dir:
            dir_path = Path(self.base_dir) / file_dir / date_str
            if not dir_path.exists():
                return []
            files = [f.name for f in dir_path.glob("*.md")]
            return sorted(files)
        else:
            # 未指定 file_dir，遍历所有子目录
            base_path = Path(self.base_dir)
            files = []
            if base_path.exists():
                for subdir in sorted(base_path.iterdir()):
                    if subdir.is_dir():
                        date_path = subdir / date_str
                        if date_path.exists():
                            for f in date_path.glob("*.md"):
                                files.append(f"{subdir.name}/{f.name}")
                # 兼容旧版直接放在 base_dir/date/ 的文件
                old_path = base_path / date_str
                if old_path.exists():
                    for f in old_path.glob("*.md"):
                        files.append(f.name)
            return sorted(files)
    
    def get_files_grouped_by_dir(self, date: datetime) -> List[dict]:
        """
        按 file_dir 分组获取指定日期的所有 Markdown 文件
        
        Args:
            date: 日期对象
        
        Returns:
            列表，每项为 {"file_dir": str, "files": List[str]}
        """
        date_str = date.strftime("%Y-%m-%d")
        base_path = Path(self.base_dir)
        result = []
        
        if base_path.exists():
            for subdir in sorted(base_path.iterdir()):
                if subdir.is_dir():
                    date_path = subdir / date_str
                    if date_path.exists():
                        files = sorted(f.name for f in date_path.glob("*.md"))
                        result.append({
                            "file_dir": subdir.name,
                            "files": files
                        })
        
        return result

    def get_file_content(self, date: datetime, filename: str, file_dir: str = "") -> Optional[str]:
        """
        读取指定文件的内容
        
        Args:
            date: 日期对象
            filename: 文件名
            file_dir: 网站子目录名（来自 config.json 的 file_dir 字段）
        
        Returns:
            文件内容，如果文件不存在返回 None
        """
        date_str = date.strftime("%Y-%m-%d")
        if file_dir:
            file_path = Path(self.base_dir) / file_dir / date_str / filename
        else:
            file_path = Path(self.base_dir) / date_str / filename
        
        if not file_path.exists():
            return None
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
