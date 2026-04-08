"""
智能体服务层
处理智能体相关的业务逻辑
"""
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
import uuid

from app.core.agent import Agent
from app.core.rag_tool import RAGTool


class AgentService:
    """智能体服务"""
    
    def __init__(self):
        """
        初始化智能体服务
        """
        self.agents: Dict[str, Agent] = {}
    
    def create_agent(self, user_id: str = None) -> str:
        """
        创建智能体
        
        Args:
            user_id: 用户ID，默认生成随机ID
            
        Returns:
            str: 智能体ID
        """
        if not user_id:
            user_id = str(uuid.uuid4())
        
        agent = Agent(user_id)
        self.agents[user_id] = agent
        return user_id
    
    def process_query(self, user_query: str, user_id: str = None, db: Optional[Session] = None) -> Dict[str, Any]:
        """
        处理用户查询
        
        Args:
            user_query: 用户查询
            user_id: 用户ID
            db: 数据库会话
            
        Returns:
            Dict[str, Any]: 处理结果
        """
        # 创建或获取智能体
        if not user_id:
            user_id = self.create_agent()
        
        if user_id not in self.agents:
            self.agents[user_id] = Agent(user_id)
        
        agent = self.agents[user_id]
        
        # 任务拆解
        tasks = agent.task_decomposition(user_query)
        
        # 创建RAG工具
        rag_tool = RAGTool(db)
        
        # 执行任务
        result = agent.execute_tasks(rag_tool)
        
        return result
    
    def get_agent(self, user_id: str) -> Optional[Agent]:
        """
        获取智能体
        
        Args:
            user_id: 用户ID
            
        Returns:
            Optional[Agent]: 智能体实例
        """
        return self.agents.get(user_id)
    
    def delete_agent(self, user_id: str) -> bool:
        """
        删除智能体
        
        Args:
            user_id: 用户ID
            
        Returns:
            bool: 是否成功
        """
        if user_id in self.agents:
            agent = self.agents[user_id]
            agent.close()
            del self.agents[user_id]
            return True
        return False
    
    def get_agent_count(self) -> int:
        """
        获取智能体数量
        
        Returns:
            int: 智能体数量
        """
        return len(self.agents)


# 单例模式
_agent_service = None


def get_agent_service() -> AgentService:
    """
    获取智能体服务实例
    
    Returns:
        AgentService: 智能体服务实例
    """
    global _agent_service
    if _agent_service is None:
        _agent_service = AgentService()
    return _agent_service