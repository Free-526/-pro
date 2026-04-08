"""
文献管理服务层
处理文献相关的业务逻辑
"""
from typing import List, Optional, Dict
from sqlalchemy.orm import Session

from app.models.database import Paper, Chunk, get_db
from app.core.pdf_parser import get_pdf_parser
from app.core.embedder import get_embedder
from app.core.faiss_retriever import get_retriever
from app.config import config

import json
import os


class PaperService:
    """文献服务"""
    
    def __init__(self):
        self.parser = get_pdf_parser()
        self.embedder = get_embedder()
        self.retriever = get_retriever()
    
    def process_pdf(self, file_path: str, paper_id: int, db: Session) -> Dict:
        """
        处理PDF文件
        
        Args:
            file_path: PDF文件路径
            paper_id: 文献ID
            db: 数据库会话
            
        Returns:
            Dict: 处理结果
        """
        try:
            paper = db.query(Paper).filter(Paper.id == paper_id).first()
            if not paper:
                return {"success": False, "error": "文献不存在"}
            
            # 更新状态
            paper.status = "processing"
            db.commit()
            
            # 解析PDF
            result = self.parser.parse(file_path, max_pages=config.MAX_PDF_PAGES)
            
            # 更新文献信息
            paper.title = result['title']
            paper.authors = json.dumps(result['authors'], ensure_ascii=False)
            paper.abstract = result['abstract']
            paper.keywords = json.dumps(result['keywords'], ensure_ascii=False)
            paper.page_count = result['page_count']
            paper.chunk_count = len(result['chunks'])
            
            # 处理文本块
            chunks_data = []
            for i, chunk in enumerate(result['chunks']):
                # 保存到数据库
                db_chunk = Chunk(
                    paper_id=paper_id,
                    chunk_index=i,
                    content=chunk['content'],
                    page_number=chunk['page_number']
                )
                db.add(db_chunk)
                db.commit()
                db.refresh(db_chunk)
                
                chunks_data.append({
                    'chunk_id': db_chunk.id,
                    'paper_id': paper_id,
                    'paper_title': result['title'],
                    'content': chunk['content'],
                    'page_number': chunk['page_number']
                })
            
            # 向量化并添加到FAISS
            if chunks_data:
                self._index_chunks(chunks_data, db)
            
            paper.status = "active"
            db.commit()
            
            return {
                "success": True,
                "title": result['title'],
                "page_count": result['page_count'],
                "chunk_count": len(result['chunks'])
            }
            
        except Exception as e:
            if paper:
                paper.status = "error"
                db.commit()
            return {"success": False, "error": str(e)}
    
    def _index_chunks(self, chunks_data: List[Dict], db: Session):
        """将文本块向量化并添加到索引"""
        texts = [c['content'] for c in chunks_data]
        vectors = self.embedder.encode(texts, normalize=True)
        
        # 添加到FAISS
        faiss_ids = self.retriever.add_vectors(vectors, chunks_data)
        
        # 更新数据库中的faiss_id
        for i, chunk_data in enumerate(chunks_data):
            db_chunk = db.query(Chunk).filter(Chunk.id == chunk_data['chunk_id']).first()
            if db_chunk:
                db_chunk.faiss_id = faiss_ids[i]
        
        db.commit()
        self.retriever.save_index()
    
    def search_papers(self, keyword: str, db: Session, limit: int = 20) -> List[Dict]:
        """搜索文献"""
        papers = db.query(Paper).filter(
            (Paper.title.contains(keyword)) |
            (Paper.authors.contains(keyword)) |
            (Paper.abstract.contains(keyword)),
            Paper.status == "active"
        ).limit(limit).all()
        
        return self._format_papers(papers)
    
    def get_paper_by_id(self, paper_id: int, db: Session) -> Optional[Dict]:
        """根据ID获取文献"""
        paper = db.query(Paper).filter(Paper.id == paper_id).first()
        if not paper:
            return None
        return self._format_paper(paper)
    
    def delete_paper(self, paper_id: int, db: Session) -> bool:
        """删除文献"""
        paper = db.query(Paper).filter(Paper.id == paper_id).first()
        if not paper:
            return False
        
        # 获取关联的chunks并从FAISS中删除
        chunks = db.query(Chunk).filter(Chunk.paper_id == paper_id).all()
        faiss_ids = [c.faiss_id for c in chunks if c.faiss_id is not None]
        
        if faiss_ids:
            self.retriever.delete_vectors(faiss_ids)
            self.retriever.save_index()
        
        # 软删除
        paper.status = "deleted"
        db.commit()
        
        return True
    
    def _format_paper(self, paper: Paper) -> Dict:
        """格式化文献数据"""
        return {
            "id": paper.id,
            "file_name": paper.file_name,
            "title": paper.title,
            "authors": json.loads(paper.authors) if paper.authors else [],
            "abstract": paper.abstract,
            "keywords": json.loads(paper.keywords) if paper.keywords else [],
            "upload_time": paper.upload_time,
            "page_count": paper.page_count,
            "chunk_count": paper.chunk_count,
            "status": paper.status
        }
    
    def _format_papers(self, papers: List[Paper]) -> List[Dict]:
        """格式化文献列表"""
        return [self._format_paper(p) for p in papers]
