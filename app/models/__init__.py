# 导入所有模型，确保SQLAlchemy能够发现它们
from .user import User
from .research_group import ResearchGroup, UserResearchGroup
from .literature import Literature

# 导出所有模型
__all__ = ['User', 'ResearchGroup', 'UserResearchGroup', 'Literature']