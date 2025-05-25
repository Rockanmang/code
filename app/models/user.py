# 导入需要的库
from sqlalchemy import Column, String
from sqlalchemy.orm import relationship
import uuid

# 从research_group.py导入Base
from .research_group import Base

# 定义User模型
class User(Base):
    __tablename__ = 'users'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    
    # 与研究组的多对多关系
    research_groups = relationship("ResearchGroup", secondary="user_research_groups", back_populates="users")
    
    # 与文献的一对多关系（用户上传的文献）- 明确指定外键
    uploaded_literature = relationship("Literature", foreign_keys="Literature.uploaded_by", back_populates="uploader")