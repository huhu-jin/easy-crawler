"""配置加载模块"""
import json
import os
from typing import List, Dict


class ConfigLoader:
    """配置文件加载器"""
    
    def __init__(self, config_path: str = "config.json"):
        """
        初始化配置加载器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self.urls = []
    
    def load(self) -> List[Dict[str, str]]:
        """
        加载配置文件
        
        Returns:
            URL 配置列表
        
        Raises:
            FileNotFoundError: 配置文件不存在
            json.JSONDecodeError: JSON 格式错误
            ValueError: 配置格式不正确
        """
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 验证配置格式
        if not isinstance(config, list):
            raise ValueError("配置文件必须是一个数组")
        
        for item in config:
            if not isinstance(item, dict):
                raise ValueError("配置项必须是对象")
            if 'url' not in item or 'desc' not in item:
                raise ValueError("配置项必须包含 'url' 和 'desc' 字段")
        
        self.urls = config
        return self.urls
    
    def get_urls(self) -> List[Dict[str, str]]:
        """
        获取 URL 列表
        
        Returns:
            URL 配置列表
        """
        return self.urls
