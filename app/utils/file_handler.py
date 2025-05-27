"""
文件处理工具模块
负责文件上传、验证、存储等功能
"""

import os
import uuid
from pathlib import Path
from typing import Optional, Tuple
from fastapi import UploadFile, HTTPException
import logging

from app.config import config
from app.utils.storage_manager import ensure_group_directory, get_unique_filename

logger = logging.getLogger(__name__)

def validate_file_type(filename: str) -> bool:
    """
    验证文件类型是否被允许
    
    Args:
        filename: 文件名
        
    Returns:
        bool: 是否为允许的文件类型
    """
    file_ext = Path(filename).suffix.lower()
    is_allowed = file_ext in config.ALLOWED_FILE_TYPES
    logger.info(f"验证文件类型: {filename} -> {file_ext} -> {'允许' if is_allowed else '不允许'}")
    return is_allowed

def validate_file_size(file_size: int) -> bool:
    """
    验证文件大小是否在允许范围内
    
    Args:
        file_size: 文件大小（字节）
        
    Returns:
        bool: 是否在允许范围内
    """
    return file_size <= config.MAX_FILE_SIZE

def generate_file_path(group_id: str, filename: str) -> Tuple[str, str]:
    """
    生成文件存储路径（使用存储管理器）
    
    Args:
        group_id: 研究组ID
        filename: 文件名
        
    Returns:
        Tuple[str, str]: (完整路径, 相对路径)
    """
    # 确保研究组目录存在
    group_dir = ensure_group_directory(group_id)
    
    # 生成唯一文件名以避免冲突
    unique_filename = get_unique_filename(group_id, filename)
    
    # 生成相对路径（相对于上传根目录）
    relative_path = os.path.join(group_id, unique_filename)
    
    # 生成完整路径
    full_path = os.path.join(group_dir, unique_filename)
    
    return full_path, relative_path

def save_uploaded_file(file: UploadFile, file_path: str) -> bool:
    """
    保存上传的文件到指定路径
    
    Args:
        file: 上传的文件对象
        file_path: 目标文件路径
        
    Returns:
        bool: 保存是否成功
    """
    try:
        # 确保目标目录存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # 保存文件
        with open(file_path, "wb") as buffer:
            content = file.file.read()
            buffer.write(content)
        
        logger.info(f"文件保存成功: {file_path}")
        return True
        
    except Exception as e:
        logger.error(f"文件保存失败: {e}")
        return False

def validate_upload_file(file: UploadFile) -> Tuple[bool, Optional[str]]:
    """
    综合验证上传文件
    
    Args:
        file: 上传的文件对象
        
    Returns:
        Tuple[bool, Optional[str]]: (是否有效, 错误信息)
    """
    logger.info(f"开始验证文件: {file.filename}")
    
    # 检查文件是否为空
    if not file.filename:
        logger.warning("文件名为空")
        return False, "文件名不能为空"
    
    # 检查文件类型
    if not validate_file_type(file.filename):
        allowed_types = ", ".join(config.ALLOWED_FILE_TYPES)
        error_msg = f"不支持的文件类型。允许的类型: {allowed_types}"
        logger.warning(f"文件类型验证失败: {error_msg}")
        return False, error_msg
    
    # 检查文件大小
    file.file.seek(0, 2)  # 移动到文件末尾
    file_size = file.file.tell()
    file.file.seek(0)  # 重置到文件开头
    
    if not validate_file_size(file_size):
        max_size_mb = config.MAX_FILE_SIZE // (1024 * 1024)
        error_msg = f"文件过大。最大允许大小: {max_size_mb}MB"
        logger.warning(f"文件大小验证失败: {error_msg}")
        return False, error_msg
    
    if file_size == 0:
        logger.warning("文件内容为空")
        return False, "文件不能为空"
    
    logger.info(f"文件验证通过: {file.filename}")
    return True, None

def get_file_info(file: UploadFile) -> dict:
    """
    获取文件基本信息
    
    Args:
        file: 上传的文件对象
        
    Returns:
        dict: 文件信息，包含file_size和file_type字段
    """
    # 获取文件大小
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    
    # 获取文件扩展名
    file_ext = Path(file.filename).suffix.lower()
    
    return {
        "filename": file.filename,
        "file_size": file_size,
        "file_type": file_ext,
        "content_type": file.content_type
    }

def cleanup_file(file_path: str) -> bool:
    """
    清理文件（删除物理文件）
    
    Args:
        file_path: 文件路径
        
    Returns:
        bool: 清理是否成功
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"文件清理成功: {file_path}")
            return True
        else:
            logger.warning(f"文件不存在，无需清理: {file_path}")
            return True
    except Exception as e:
        logger.error(f"文件清理失败: {e}")
        return False

def get_file_stats(file_path: str) -> Optional[dict]:
    """
    获取文件统计信息
    
    Args:
        file_path: 文件路径
        
    Returns:
        Optional[dict]: 文件统计信息，如果文件不存在返回None
    """
    try:
        if not os.path.exists(file_path):
            return None
        
        stat = os.stat(file_path)
        return {
            "size": stat.st_size,
            "created": stat.st_ctime,
            "modified": stat.st_mtime,
            "accessed": stat.st_atime
        }
    except Exception as e:
        logger.error(f"获取文件统计失败: {e}")
        return None