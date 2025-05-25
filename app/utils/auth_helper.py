"""
认证和权限验证辅助函数
用于验证用户权限和组成员身份
"""

from sqlalchemy.orm import Session
from app.models.user import User
from app.models.research_group import ResearchGroup, UserResearchGroup
from app.models.literature import Literature
from fastapi import HTTPException
from typing import Optional
import os

def verify_group_membership(user_id: str, group_id: str, db: Session) -> bool:
    """
    验证用户是否为指定研究组的成员
    
    Args:
        user_id: 用户ID
        group_id: 研究组ID
        db: 数据库会话
        
    Returns:
        bool: 是否为组成员
    """
    try:
        # 查询用户-研究组关系
        membership = db.query(UserResearchGroup).filter(
            UserResearchGroup.user_id == user_id,
            UserResearchGroup.group_id == group_id
        ).first()
        
        return membership is not None
        
    except Exception as e:
        print(f"验证组成员身份失败: {e}")
        return False

def verify_group_exists(group_id: str, db: Session) -> bool:
    """
    验证研究组是否存在
    
    Args:
        group_id: 研究组ID
        db: 数据库会话
        
    Returns:
        bool: 研究组是否存在
    """
    try:
        group = db.query(ResearchGroup).filter(ResearchGroup.id == group_id).first()
        return group is not None
    except Exception as e:
        print(f"验证研究组存在失败: {e}")
        return False

def get_user_groups(user_id: str, db: Session) -> list:
    """
    获取用户所属的所有研究组
    
    Args:
        user_id: 用户ID
        db: 数据库会话
        
    Returns:
        list: 研究组列表
    """
    try:
        # 通过关联表查询用户的所有研究组
        groups = db.query(ResearchGroup).join(
            UserResearchGroup, ResearchGroup.id == UserResearchGroup.group_id
        ).filter(UserResearchGroup.user_id == user_id).all()
        
        return groups
        
    except Exception as e:
        print(f"获取用户研究组失败: {e}")
        return []

def require_group_membership(user_id: str, group_id: str, db: Session) -> None:
    """
    要求用户必须是指定研究组成员，否则抛出异常
    
    Args:
        user_id: 用户ID
        group_id: 研究组ID
        db: 数据库会话
        
    Raises:
        HTTPException: 如果用户不是组成员
    """
    # 首先验证研究组是否存在
    if not verify_group_exists(group_id, db):
        raise HTTPException(status_code=404, detail="研究组不存在")
    
    # 验证用户是否为组成员
    if not verify_group_membership(user_id, group_id, db):
        raise HTTPException(status_code=403, detail="您不是该研究组的成员，无权访问")

def get_group_info(group_id: str, db: Session) -> dict:
    """
    获取研究组基本信息
    
    Args:
        group_id: 研究组ID
        db: 数据库会话
        
    Returns:
        dict: 研究组信息
    """
    try:
        group = db.query(ResearchGroup).filter(ResearchGroup.id == group_id).first()
        if group:
            return {
                "id": group.id,
                "name": group.name,
                "institution": group.institution,
                "description": group.description,
                "research_area": group.research_area
            }
        return None
    except Exception as e:
        print(f"获取研究组信息失败: {e}")
        return None

# ===== 新增：文献访问权限验证 =====

def verify_literature_access(user_id: str, literature_id: str, db: Session) -> bool:
    """
    验证用户对特定文献的访问权限
    
    Args:
        user_id: 用户ID
        literature_id: 文献ID
        db: 数据库会话
        
    Returns:
        bool: 是否有访问权限
    """
    try:
        # 获取文献信息
        literature = db.query(Literature).filter(Literature.id == literature_id).first()
        if not literature:
            return False
        
        # 检查文献是否被软删除
        if literature.status != 'active':
            return False
        
        # 验证用户是否为该文献所属研究组的成员
        return verify_group_membership(user_id, literature.research_group_id, db)
        
    except Exception as e:
        print(f"验证文献访问权限失败: {e}")
        return False

def get_literature_with_permission(literature_id: str, user_id: str, db: Session) -> Optional[Literature]:
    """
    获取文献信息并验证权限
    
    Args:
        literature_id: 文献ID
        user_id: 用户ID
        db: 数据库会话
        
    Returns:
        Literature: 文献对象，如果无权限则返回None
        
    Raises:
        HTTPException: 根据不同情况抛出相应的HTTP异常
    """
    try:
        # 获取文献信息
        literature = db.query(Literature).filter(Literature.id == literature_id).first()
        
        # 文献不存在
        if not literature:
            raise HTTPException(status_code=404, detail="文献不存在")
        
        # 文献已被软删除
        if literature.status != 'active':
            raise HTTPException(status_code=410, detail="文献已被删除")
        
        # 验证用户权限
        if not verify_group_membership(user_id, literature.research_group_id, db):
            raise HTTPException(status_code=403, detail="您无权访问此文献，请确认您是该研究组的成员")
        
        return literature
        
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        print(f"获取文献信息失败: {e}")
        raise HTTPException(status_code=500, detail="获取文献信息失败")

def verify_file_exists(file_path: str) -> bool:
    """
    验证文件是否存在于磁盘上
    
    Args:
        file_path: 文件路径
        
    Returns:
        bool: 文件是否存在
    """
    try:
        return os.path.exists(file_path) and os.path.isfile(file_path)
    except Exception as e:
        print(f"验证文件存在失败: {e}")
        return False

def get_content_type(file_path: str) -> str:
    """
    根据文件扩展名获取Content-Type
    
    Args:
        file_path: 文件路径
        
    Returns:
        str: Content-Type
    """
    file_extension = os.path.splitext(file_path)[1].lower()
    
    content_types = {
        '.pdf': 'application/pdf',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.doc': 'application/msword',
        '.html': 'text/html',
        '.htm': 'text/html',
        '.txt': 'text/plain'
    }
    
    return content_types.get(file_extension, 'application/octet-stream')