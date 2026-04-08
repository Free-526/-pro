"""
RAG工具模块
封装现有的RAG功能，提供给智能体使用
"""
from typing import List, Dict, Optional
from sqlalchemy.orm import Session

from app.core.embedder import get_embedder
from app.core.faiss_retriever import get_retriever
from app.core.kimi_client import get_kimi_client
from app.models.database import Chunk, Paper


class RAGTool:
    """RAG工具类"""
    
    def __init__(self, db: Optional[Session] = None):
        """
        初始化RAG工具
        
        Args:
            db: 数据库会话
        """
        self.embedder = get_embedder()
        self.retriever = get_retriever()
        self.kimi = get_kimi_client()
        self.db = db
    
    def retrieve(self, query: str, top_k: int = 5, paper_ids: Optional[List[int]] = None) -> List[Dict]:
        """
        检索相关信息
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            paper_ids: 指定文献范围
            
        Returns:
            List[Dict]: 检索结果
        """
        contexts = []
        
        if paper_ids and self.db:
            # 指定文献范围 - 使用文本匹配
            chunks = self.db.query(Chunk).filter(
                Chunk.paper_id.in_(paper_ids)
            ).all()
            
            keywords = query.split()
            for chunk in chunks:
                score = sum(1 for kw in keywords if kw.lower() in chunk.content.lower())
                if score > 0:
                    paper = self.db.query(Paper).filter(Paper.id == chunk.paper_id).first()
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
                
                # 如果向量检索没有结果，从数据库获取最新文献
                if not contexts and self.db:
                    print(f"[RAG检索] 向量检索无结果，从数据库获取最新文献...")
                    chunks = self.db.query(Chunk).join(Paper).filter(
                        Paper.status == "active"
                    ).order_by(Chunk.id.desc()).limit(top_k).all()
                    
                    for chunk in chunks:
                        paper = self.db.query(Paper).filter(Paper.id == chunk.paper_id).first()
                        contexts.append({
                            'content': chunk.content,
                            'paper_title': paper.title if paper else '未知文献',
                            'page_number': chunk.page_number,
                            'score': 0.5  # 默认分数
                        })
                    
                    print(f"[RAG检索] 从数据库获取 {len(contexts)} 个文本块")
                    
            except Exception as e:
                print(f"向量检索失败: {str(e)}")
                # 回退到数据库检索
                if self.db:
                    print(f"[RAG检索] 向量检索失败，从数据库获取最新文献...")
                    chunks = self.db.query(Chunk).join(Paper).filter(
                        Paper.status == "active"
                    ).order_by(Chunk.id.desc()).limit(top_k).all()
                    
                    for chunk in chunks:
                        paper = self.db.query(Paper).filter(Paper.id == chunk.paper_id).first()
                        contexts.append({
                            'content': chunk.content,
                            'paper_title': paper.title if paper else '未知文献',
                            'page_number': chunk.page_number,
                            'score': 0.5  # 默认分数
                        })
                    
                    print(f"[RAG检索] 从数据库获取 {len(contexts)} 个文本块")
        
        return contexts
    
    def summarize(self, content: str) -> str:
        """
        总结内容
        
        Args:
            content: 要总结的内容
            
        Returns:
            str: 总结结果
        """
        system_prompt = """你是一个总结助手，请对提供的内容进行简要总结，突出重点信息。

要求：
1. 总结要简洁明了
2. 涵盖主要内容
3. 使用自然流畅的语言"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"请总结以下内容：\n{content}"}
        ]
        
        result = ""
        for chunk in self.kimi.chat_completion(messages, stream=False):
            result += chunk
        
        return result
    
    def analyze(self, content: str, analysis_type: str) -> Dict:
        """
        分析内容
        
        Args:
            content: 要分析的内容
            analysis_type: 分析类型
            
        Returns:
            Dict: 分析结果
        """
        system_prompt = f"""你是一个分析助手，请对提供的内容进行{analysis_type}分析。

要求：
1. 分析要深入透彻
2. 提供具体的分析结果
3. 使用自然流畅的语言"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"请对以下内容进行{analysis_type}分析：\n{content}"}
        ]
        
        result = ""
        for chunk in self.kimi.chat_completion(messages, stream=False):
            result += chunk
        
        return {"analysis": result}
    
    def generate(self, prompt: str, context: str = "") -> str:
        """
        生成内容
        
        Args:
            prompt: 生成提示
            context: 上下文信息
            
        Returns:
            str: 生成结果
        """
        system_prompt = """你是一个内容生成助手，请根据提供的提示和上下文生成相关内容。

要求：
1. 内容要符合提示要求
2. 结合上下文信息
3. 使用自然流畅的语言"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"上下文：{context}\n\n提示：{prompt}"}
        ]
        
        result = ""
        for chunk in self.kimi.chat_completion(messages, stream=False):
            result += chunk
        
        return result
    
    def rag_answer(self, query: str, top_k: int = 5) -> str:
        """
        RAG问答
        
        Args:
            query: 用户问题
            top_k: 检索结果数量
            
        Returns:
            str: 回答结果
        """
        # 检索相关信息
        contexts = self.retrieve(query, top_k=top_k)
        
        # 构建RAG提示
        messages = self.kimi.build_rag_prompt(
            query=query,
            contexts=contexts
        )
        
        # 生成回答
        result = ""
        for chunk in self.kimi.chat_completion(messages, stream=False):
            result += chunk
        
        return result