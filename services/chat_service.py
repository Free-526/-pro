"""
对话服务层
处理对话相关的业务逻辑
"""
from typing import List, Optional, Dict, Iterator
from sqlalchemy.orm import Session

from app.models.database import ChatSession, ChatMessage, Chunk, Paper
from app.core.kimi_client import get_kimi_client
from app.core.embedder import get_embedder
from app.core.faiss_retriever import get_retriever


class ChatService:
    """对话服务"""
    
    def __init__(self):
        self.kimi = get_kimi_client()
        self.embedder = get_embedder()
        self.retriever = get_retriever()
    
    def create_session(self, session_name: str, db: Session) -> Dict:
        """创建对话会话"""
        session = ChatSession(session_name=session_name or "新会话")
        db.add(session)
        db.commit()
        db.refresh(session)
        
        return {
            "id": session.id,
            "session_name": session.session_name,
            "created_at": session.created_at,
            "updated_at": session.updated_at
        }
    
    def get_session_history(self, session_id: int, db: Session) -> List[Dict]:
        """获取会话历史"""
        messages = db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id
        ).order_by(ChatMessage.created_at).all()
        
        return [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "references": eval(m.references) if m.references else None,
                "created_at": m.created_at
            }
            for m in messages
        ]
    
    def retrieve_contexts(
        self, 
        query: str, 
        paper_ids: Optional[List[int]] = None,
        db: Session = None,
        top_k: int = 5
    ) -> List[Dict]:
        """
        检索相关上下文
        
        Args:
            query: 查询文本
            paper_ids: 指定文献范围
            db: 数据库会话
            top_k: 返回结果数量
            
        Returns:
            List[Dict]: 相关上下文列表
        """
        contexts = []
        
        if paper_ids and db:
            # 指定文献范围 - 使用文本匹配
            chunks = db.query(Chunk).filter(
                Chunk.paper_id.in_(paper_ids)
            ).all()
            
            keywords = query.split()
            for chunk in chunks:
                score = sum(1 for kw in keywords if kw.lower() in chunk.content.lower())
                if score > 0:
                    paper = db.query(Paper).filter(Paper.id == chunk.paper_id).first()
                    contexts.append({
                        'content': chunk.content,
                        'paper_title': paper.title if paper else '未知文献',
                        'page_number': chunk.page_number,
                        'score': score
                    })
            
            contexts.sort(key=lambda x: x['score'], reverse=True)
            contexts = contexts[:top_k]
        else:
            # 使用向量检索
            try:
                query_vector = self.embedder.encode([query], normalize=True)
                search_results = self.retriever.search(query_vector[0], top_k=top_k)
                
                for result in search_results:
                    contexts.append({
                        'content': result.get('content', ''),
                        'paper_title': result.get('paper_title', '未知文献'),
                        'page_number': result.get('page_number', '?'),
                        'score': result.get('score', 0)
                    })
            except Exception as e:
                print(f"向量检索失败: {str(e)}")
        
        return contexts
    
    def generate_response(
        self,
        query: str,
        contexts: List[Dict],
        chat_history: Optional[List[Dict]] = None,
        stream: bool = True
    ) -> Iterator[str]:
        """
        生成回复
        
        Args:
            query: 用户问题
            contexts: 相关上下文
            chat_history: 历史对话
            stream: 是否流式输出
            
        Yields:
            str: 生成的文本片段
        """
        messages = self.kimi.build_rag_prompt(
            query=query,
            contexts=contexts,
            chat_history=chat_history
        )
        
        for chunk in self.kimi.chat_completion(messages, stream=stream):
            yield chunk
    
    def save_message(
        self,
        session_id: int,
        role: str,
        content: str,
        references: Optional[List[Dict]] = None,
        db: Session = None
    ) -> Dict:
        """保存消息"""
        message = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            references=str(references) if references else None
        )
        db.add(message)
        db.commit()
        db.refresh(message)
        
        return {
            "id": message.id,
            "role": message.role,
            "content": message.content,
            "created_at": message.created_at
        }
