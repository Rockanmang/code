"""
认证和权限验证辅助函数
用于验证用户权限和组成员身份
"""

from sqlalchemy.orm import Session
from app.models.user import User
from app.models.research_group import ResearchGroup, UserResearchGroup
from fastapi import HTTPException

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