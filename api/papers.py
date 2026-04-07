"""
文献管理API路由
"""
import os
import shutil
import json
import traceback
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.database import get_db, Paper, Chunk, SessionLocal, User
from app.models.schemas import ResponseModel, PaperResponse, PaperListResponse
from app.core.pdf_parser import get_pdf_parser
from app.core.embedder import get_embedder
from app.core.faiss_retriever import get_retriever
from app.core.auth import get_current_user, get_optional_user
from app.core.analytics import Tracker
from app.config import config

router = APIRouter()


def process_pdf_sync(file_path: str, paper_id: int, user_id: int):
    """同步处理PDF文件（用于后台线程）"""
    import threading
    print(f"🔄 [Thread-{threading.current_thread().name}] 开始处理PDF (ID: {paper_id}, User: {user_id}): {file_path}")
    
    # 创建新的数据库会话
    db = SessionLocal()
    try:
        # 更新状态为处理中
        paper = db.query(Paper).filter(Paper.id == paper_id, Paper.user_id == user_id).first()
        if not paper:
            print(f"❌ 找不到文献记录 ID: {paper_id} 或无权访问")
            return
        
        paper.status = "processing"
        db.commit()
        print(f"📄 文献状态更新为 processing: {paper.file_name}")
        
        # 解析PDF
        print(f"🔍 开始解析PDF...")
        parser = get_pdf_parser()
        result = parser.parse(file_path, max_pages=config.MAX_PDF_PAGES)
        print(f"✅ PDF解析完成: {result['page_count']}页, {len(result['chunks'])}个文本块")
        
        # 更新文献信息
        paper.title = result['title']
        paper.authors = json.dumps(result['authors'], ensure_ascii=False)
        paper.abstract = result['abstract']
        paper.keywords = json.dumps(result['keywords'], ensure_ascii=False)
        paper.page_count = result['page_count']
        paper.chunk_count = len(result['chunks'])
        db.commit()
        print(f"📝 文献元数据已更新")
        
        # 向量化文本块
        print(f"🤖 加载嵌入模型...")
        embedder = get_embedder()
        print(f"✅ 嵌入模型加载完成")
        
        retriever = get_retriever()
        
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
            
            # 准备向量化数据
            chunks_data.append({
                'chunk_id': db_chunk.id,
                'paper_id': paper_id,
                'paper_title': result['title'],
                'content': chunk['content'],
                'page_number': chunk['page_number']
            })
        
        print(f"📦 已保存 {len(chunks_data)} 个文本块到数据库")
        
        # 批量向量化
        if chunks_data:
            print(f"🔢 开始向量化...")
            texts = [c['content'] for c in chunks_data]
            vectors = embedder.encode(texts, normalize=True)
            print(f"✅ 向量化完成: {vectors.shape}")
            
            # 添加到FAISS索引
            print(f"💾 添加到FAISS索引...")
            faiss_ids = retriever.add_vectors(vectors, chunks_data)
            print(f"✅ FAISS索引添加完成: {len(faiss_ids)} 个向量")
            
            # 更新数据库中的faiss_id
            for i, chunk_data in enumerate(chunks_data):
                db_chunk = db.query(Chunk).filter(Chunk.id == chunk_data['chunk_id']).first()
                if db_chunk:
                    db_chunk.faiss_id = faiss_ids[i]
            
            db.commit()
            retriever.save_index()
            print(f"💾 FAISS索引已保存")
        
        paper.status = "active"
        db.commit()
        print(f"✅ PDF处理完成: {paper.title}")
        
    except Exception as e:
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        print(f"❌ 处理PDF失败: {error_msg}")
        
        paper = db.query(Paper).filter(Paper.id == paper_id).first()
        if paper:
            paper.status = "error"
            db.commit()
    finally:
        db.close()
        print(f"🔒 数据库会话已关闭 (ID: {paper_id})")


@router.post("/upload", response_model=ResponseModel)
async def upload_papers(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    上传PDF文献文件
    
    - **files**: 支持多文件上传，每个文件最大50MB
    """
    uploaded = []
    failed = []
    
    for file in files:
        # 检查文件类型
        if not file.filename.lower().endswith('.pdf'):
            failed.append({
                "file_name": file.filename,
                "error": "仅支持PDF文件"
            })
            continue
        
        # 检查文件大小
        content = await file.read()
        if len(content) > config.MAX_FILE_SIZE:
            failed.append({
                "file_name": file.filename,
                "error": f"文件大小超过限制({config.MAX_FILE_SIZE // 1024 // 1024}MB)"
            })
            continue
        
        try:
            # 按用户隔离文件存储路径
            user_upload_dir = os.path.join(config.UPLOAD_DIR, str(current_user.id))
            os.makedirs(user_upload_dir, exist_ok=True)
            file_path = os.path.join(user_upload_dir, file.filename)
            
            # 检查当前用户是否已存在同名文件
            existing_paper = db.query(Paper).filter(
                Paper.user_id == current_user.id,
                Paper.file_path == file_path
            ).first()
            if existing_paper:
                print(f"🔄 文件已存在，正在替换: {file.filename}")
                # 删除旧的FAISS向量
                old_chunks = db.query(Chunk).filter(Chunk.paper_id == existing_paper.id).all()
                faiss_ids = [c.faiss_id for c in old_chunks if c.faiss_id is not None]
                if faiss_ids:
                    try:
                        retriever = get_retriever()
                        retriever.delete_vectors(faiss_ids)
                        retriever.save_index()
                        print(f"✅ 已删除旧向量: {len(faiss_ids)} 个")
                    except Exception as e:
                        print(f"⚠️ 删除旧向量失败: {e}")
                
                # 删除旧的chunks记录
                db.query(Chunk).filter(Chunk.paper_id == existing_paper.id).delete()
                
                # 软删除旧文献记录
                existing_paper.status = "deleted"
                db.commit()
                db.flush()  # 强制刷新，确保删除生效
                print(f"✅ 旧记录已清理")
                
                # 重新查询确认状态
                db.refresh(existing_paper)
            
            # 保存新文件（覆盖旧文件）
            with open(file_path, "wb") as f:
                f.write(content)
            
            # 创建数据库记录
            paper = Paper(
                user_id=current_user.id,
                file_name=file.filename,
                file_path=file_path,
                file_size=len(content),
                status="pending"
            )
            db.add(paper)
            db.commit()
            db.refresh(paper)
            
            # 使用线程池后台处理PDF
            import threading
            thread = threading.Thread(
                target=process_pdf_sync,
                args=(file_path, paper.id, current_user.id)
            )
            thread.daemon = True
            thread.start()
            
            uploaded.append({
                "id": paper.id,
                "file_name": file.filename,
                "status": "processing"
            })
            
        except Exception as e:
            failed.append({
                "file_name": file.filename,
                "error": str(e)
            })
    
    return ResponseModel(
        code=200,
        message="上传成功" if uploaded else "上传失败",
        data={
            "uploaded": uploaded,
            "failed": failed
        }
    )


@router.get("", response_model=ResponseModel)
async def list_papers(
    page: int = 1,
    size: int = 20,
    keyword: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取文献列表
    
    - **page**: 页码，从1开始
    - **size**: 每页数量
    - **keyword**: 搜索关键词（标题、作者）
    - **status**: 状态筛选
    """
    query = db.query(Paper).filter(Paper.user_id == current_user.id)
    
    # 搜索过滤
    if keyword:
        query = query.filter(
            (Paper.title.contains(keyword)) |
            (Paper.authors.contains(keyword))
        )
    
    if status:
        query = query.filter(Paper.status == status)
    else:
        query = query.filter(Paper.status != "deleted")
    
    # 分页
    total = query.count()
    papers = query.order_by(Paper.upload_time.desc()).offset((page - 1) * size).limit(size).all()
    
    # 解析JSON字段
    items = []
    for paper in papers:
        item = {
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
        items.append(item)


    return ResponseModel(
        code=200,
        data={
            "total": total,
            "items": items
        }
    )


@router.get("/{paper_id}", response_model=ResponseModel)
async def get_paper(
    paper_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取文献详情"""
    paper = db.query(Paper).filter(Paper.id == paper_id, Paper.user_id == current_user.id).first()

    if not paper:
        raise HTTPException(status_code=404, detail="文献不存在或无权访问")

    try:
        authors = json.loads(paper.authors) if paper.authors else []
    except:
        authors = []
    try:
        keywords = json.loads(paper.keywords) if paper.keywords else []
    except:
        keywords = []

    return ResponseModel(
        code=200,
        data={
            "id": paper.id,
            "file_name": paper.file_name,
            "title": paper.title,
            "authors": authors,
            "abstract": paper.abstract,
            "keywords": keywords,
            "upload_time": paper.upload_time,
            "page_count": paper.page_count,
            "chunk_count": paper.chunk_count,
            "status": paper.status
        }
    )


@router.delete("/{paper_id}", response_model=ResponseModel)
async def delete_paper(
    paper_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除文献（软删除）"""
    paper = db.query(Paper).filter(Paper.id == paper_id, Paper.user_id == current_user.id).first()

    if not paper:
        raise HTTPException(status_code=404, detail="文献不存在或无权访问")

    # 获取关联的chunks并从FAISS中删除
    chunks = db.query(Chunk).filter(Chunk.paper_id == paper_id).all()
    faiss_ids = [c.faiss_id for c in chunks if c.faiss_id is not None]

    if faiss_ids:
        retriever = get_retriever()
        retriever.delete_vectors(faiss_ids)
        retriever.save_index()

    # 软删除
    paper.status = "deleted"
    db.commit()

    return ResponseModel(code=200, message="删除成功")


@router.get("/{paper_id}/chunks", response_model=ResponseModel)
async def get_paper_chunks(
    paper_id: int,
    page: int = 1,
    size: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取文献的文本块列表"""
    paper = db.query(Paper).filter(Paper.id == paper_id, Paper.user_id == current_user.id).first()

    if not paper:
        raise HTTPException(status_code=404, detail="文献不存在或无权访问")

    query = db.query(Chunk).filter(Chunk.paper_id == paper_id)
    total = query.count()
    chunks = query.order_by(Chunk.chunk_index).offset((page - 1) * size).limit(size).all()

    return ResponseModel(
        code=200,
        data={
            "total": total,
            "items": [
                {
                    "id": c.id,
                    "chunk_index": c.chunk_index,
                    "content": c.content,
                    "page_number": c.page_number
                }
                for c in chunks
            ]
        }
    )


import json