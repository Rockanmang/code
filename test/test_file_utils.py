#!/usr/bin/env python3
"""
测试文件处理工具函数
验证文件上传相关功能是否正常工作
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config import config
from app.utils.file_handler import (
    validate_file_type, 
    generate_file_path,
    get_file_info
)
from app.utils.text_extractor import (
    extract_title_from_filename,
    extract_title_from_text,
    is_text_extractable
)

def test_config():
    """测试配置功能"""
    print("🔧 测试配置功能...")
    
    # 测试文件类型验证
    assert config.is_allowed_file_type("test.pdf") == True
    assert config.is_allowed_file_type("test.docx") == True
    assert config.is_allowed_file_type("test.html") == True
    assert config.is_allowed_file_type("test.txt") == False
    print("✅ 文件类型验证正常")
    
    # 测试文件大小验证
    assert config.is_file_size_valid(1024) == True  # 1KB
    assert config.is_file_size_valid(50 * 1024 * 1024) == True  # 50MB
    assert config.is_file_size_valid(100 * 1024 * 1024) == False  # 100MB
    print("✅ 文件大小验证正常")
    
    # 测试目录创建
    test_group_id = "test-group-123"
    upload_dir = config.ensure_upload_dir_exists(test_group_id)
    assert os.path.exists(upload_dir)
    print(f"✅ 目录创建正常: {upload_dir}")

def test_file_handler():
    """测试文件处理函数"""
    print("\n📁 测试文件处理函数...")
    
    # 测试文件类型验证
    assert validate_file_type("document.pdf") == True
    assert validate_file_type("document.txt") == False
    print("✅ 文件类型验证函数正常")
    
    # 测试路径生成
    test_group_id = "test-group-456"
    test_filename = "research_paper.pdf"
    full_path, relative_path = generate_file_path(test_group_id, test_filename)
    
    assert test_group_id in full_path
    assert test_group_id in relative_path
    assert full_path.endswith(".pdf")
    assert relative_path.endswith(".pdf")
    print(f"✅ 路径生成正常:")
    print(f"   完整路径: {full_path}")
    print(f"   相对路径: {relative_path}")

def test_text_extractor():
    """测试文本提取函数"""
    print("\n📝 测试文本提取函数...")
    
    # 测试从文件名提取标题
    title1 = extract_title_from_filename("research_paper.pdf")
    assert title1 == "research_paper"
    print(f"✅ 文件名标题提取: '{title1}'")
    
    # 测试从文本提取标题
    test_text = "这是一篇关于人工智能的研究论文\n\n本文介绍了..."
    title2 = extract_title_from_text(test_text)
    assert "人工智能" in title2
    print(f"✅ 文本标题提取: '{title2}'")
    
    # 测试长文本标题截断
    long_text = "这是一个非常非常非常非常非常非常非常非常非常非常长的标题，应该被截断"
    title3 = extract_title_from_text(long_text, max_length=20)
    assert len(title3) <= 23  # 20 + "..."
    print(f"✅ 长标题截断: '{title3}'")
    
    # 测试文件类型支持检查
    assert is_text_extractable("test.pdf") == True
    assert is_text_extractable("test.docx") == False
    print("✅ 文件类型支持检查正常")

def test_directory_structure():
    """测试目录结构"""
    print("\n📂 测试目录结构...")
    
    # 检查uploads目录是否创建
    uploads_dir = Path("./uploads")
    if uploads_dir.exists():
        print(f"✅ uploads目录存在: {uploads_dir.absolute()}")
        
        # 列出子目录
        subdirs = [d for d in uploads_dir.iterdir() if d.is_dir()]
        if subdirs:
            print("📁 发现的研究组目录:")
            for subdir in subdirs:
                print(f"   - {subdir.name}")
        else:
            print("ℹ️  暂无研究组目录")
    else:
        print("ℹ️  uploads目录尚未创建")

def main():
    """主测试函数"""
    print("🧪 文件处理工具函数测试")
    print("="*50)
    
    try:
        test_config()
        test_file_handler()
        test_text_extractor()
        test_directory_structure()
        
        print("\n" + "="*50)
        print("🎉 所有测试通过！文件处理工具函数正常工作")
        
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()