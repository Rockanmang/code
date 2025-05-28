#!/usr/bin/env python3
"""
创建测试用户脚本
"""
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import get_db
from app.models.user import User
from app.models.research_group import ResearchGroup, UserResearchGroup
from app.auth import hash_password
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_test_user():
    """创建测试用户"""
    db_gen = get_db()
    db = next(db_gen)
    
    try:
        # 检查用户是否已存在
        existing_user = db.query(User).filter(User.username == "testuser").first()
        if existing_user:
            logger.info("测试用户已存在")
            return existing_user.id
        
        # 创建测试用户
        hashed_password = hash_password("testpass123")
        test_user = User(
            username="testuser",
            email="testuser@example.com",
            password_hash=hashed_password
        )
        
        db.add(test_user)
        db.commit()
        db.refresh(test_user)
        
        logger.info(f"创建测试用户成功: {test_user.id}")
        
        # 创建测试研究组
        existing_group = db.query(ResearchGroup).filter(ResearchGroup.name == "测试研究组").first()
        if not existing_group:
            test_group = ResearchGroup(
                name="测试研究组",
                institution="测试机构",
                description="用于测试的研究组",
                research_area="测试领域"
            )
            
            db.add(test_group)
            db.commit()
            db.refresh(test_group)
            
            # 添加用户到研究组
            membership = UserResearchGroup(
                user_id=test_user.id,
                group_id=test_group.id
            )
            db.add(membership)
            db.commit()
            
            logger.info(f"创建测试研究组成功: {test_group.id}")
        else:
            logger.info("测试研究组已存在")
        
        return test_user.id
        
    except Exception as e:
        logger.error(f"创建测试用户失败: {e}")
        db.rollback()
        return None
    finally:
        db.close()

if __name__ == "__main__":
    create_test_user() 