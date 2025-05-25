"""
文本提取工具函数
主要用于从PDF文件中提取文本和标题
"""

import os
from pathlib import Path
from typing import Optional
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_pdf_text(file_path: str) -> Optional[str]:
    """
    使用PyPDF2从PDF文件中提取文本
    
    Args:
        file_path: PDF文件路径
        
    Returns:
        Optional[str]: 提取的文本内容，失败时返回None
    """
    try:
        import PyPDF2
        
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            # 提取所有页面的文本
            text = ""
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text += page.extract_text() + "\n"
            
            # 清理文本（移除多余的空白字符）
            text = " ".join(text.split())
            
            if text.strip():
                logger.info(f"成功从PDF提取文本，长度: {len(text)} 字符")
                return text
            else:
                logger.warning(f"PDF文件 {file_path} 中没有可提取的文本")
                return None
                
    except ImportError:
        logger.error("PyPDF2库未安装，无法提取PDF文本")
        return None
    except Exception as e:
        logger.error(f"提取PDF文本失败: {e}")
        return None

def extract_title_from_text(text: str, max_length: int = 50) -> str:
    """
    从文本中提取标题（简单实现）
    
    Args:
        text: 文本内容
        max_length: 标题最大长度
        
    Returns:
        str: 提取的标题
    """
    if not text or not text.strip():
        return "未知标题"
    
    # 清理文本
    text = text.strip()
    
    # 按行分割，取第一个非空行作为标题
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    if lines:
        title = lines[0]
        # 限制标题长度
        if len(title) > max_length:
            title = title[:max_length] + "..."
        return title
    
    # 如果没有找到合适的行，取前50个字符
    if len(text) > max_length:
        return text[:max_length] + "..."
    
    return text

def extract_title_from_filename(filename: str) -> str:
    """
    从文件名中提取标题（去除扩展名）
    
    Args:
        filename: 文件名
        
    Returns:
        str: 提取的标题
    """
    return Path(filename).stem

def extract_metadata_from_file(file_path: str, original_filename: str) -> dict:
    """
    从文件中提取元数据（标题等）
    
    Args:
        file_path: 文件路径
        original_filename: 原始文件名
        
    Returns:
        dict: 包含提取元数据的字典
    """
    file_ext = Path(file_path).suffix.lower()
    
    metadata = {
        "title": extract_title_from_filename(original_filename),
        "extracted_text": None,
        "extraction_success": False
    }
    
    # 只处理PDF文件
    if file_ext == '.pdf':
        try:
            extracted_text = extract_pdf_text(file_path)
            if extracted_text:
                # 从提取的文本中获取更好的标题
                title_from_text = extract_title_from_text(extracted_text)
                if title_from_text and title_from_text != "未知标题":
                    metadata["title"] = title_from_text
                
                metadata["extracted_text"] = extracted_text
                metadata["extraction_success"] = True
                
                logger.info(f"成功提取PDF元数据: {metadata['title']}")
            else:
                logger.warning(f"PDF文本提取失败，使用文件名作为标题")
                
        except Exception as e:
            logger.error(f"PDF元数据提取失败: {e}")
    
    else:
        # 对于非PDF文件，暂时只使用文件名作为标题
        logger.info(f"文件类型 {file_ext} 暂不支持文本提取，使用文件名作为标题")
    
    return metadata

def is_text_extractable(file_path: str) -> bool:
    """
    检查文件是否支持文本提取
    
    Args:
        file_path: 文件路径
        
    Returns:
        bool: 是否支持文本提取
    """
    file_ext = Path(file_path).suffix.lower()
    # 目前只支持PDF
    return file_ext == '.pdf'