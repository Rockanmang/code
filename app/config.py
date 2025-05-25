"""
应用配置文件
定义文件存储、上传限制等配置
"""

import os
from pathlib import Path

class Config:
    """基础配置类"""
    
    # 文件存储配置
    UPLOAD_ROOT_DIR = "./uploads"  # 文件存储根目录
    
    # 允许的文件类型
    ALLOWED_FILE_TYPES = ['.pdf', '.docx', '.html', '.htm']
    
    # 文件大小限制（字节）
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    
    # 文件类型MIME映射
    FILE_TYPE_MAPPING = {
        '.pdf': 'application/pdf',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.html': 'text/html',
        '.htm': 'text/html'
    }
    
    @classmethod
    def get_upload_dir(cls, group_id: str) -> str:
        """获取指定研究组的上传目录路径"""
        return os.path.join(cls.UPLOAD_ROOT_DIR, group_id)
    
    @classmethod
    def ensure_upload_dir_exists(cls, group_id: str) -> str:
        """确保上传目录存在，如果不存在则创建"""
        upload_dir = cls.get_upload_dir(group_id)
        Path(upload_dir).mkdir(parents=True, exist_ok=True)
        return upload_dir
    
    @classmethod
    def is_allowed_file_type(cls, filename: str) -> bool:
        """检查文件类型是否被允许"""
        file_ext = Path(filename).suffix.lower()
        return file_ext in cls.ALLOWED_FILE_TYPES
    
    @classmethod
    def get_file_type(cls, filename: str) -> str:
        """获取文件类型"""
        return Path(filename).suffix.lower()
    
    @classmethod
    def is_file_size_valid(cls, file_size: int) -> bool:
        """检查文件大小是否在允许范围内"""
        return 0 < file_size <= cls.MAX_FILE_SIZE

# 创建配置实例
config = Config()