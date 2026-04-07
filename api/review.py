"""
综述生成API路由
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.models.database import get_db, Paper, Chunk, User
from app.models.schemas import ResponseModel, ReviewGenerateRequest
from app.core.review_generator import get_review_generator
from app.core.embedder import get_embedder
from app.core.faiss_retriever import get_retriever
from app.core.auth import get_current_user
from app.core.analytics import Tracker

router = APIRouter()


@router.post("/generate")
async def generate_review(
    request: ReviewGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    生成文献综述（流式响应）
    
    - **topic**: 综述主题
    - **paper_ids**: 指定文献ID列表（可选，不传则使用全部文献）
    - **word_count**: 字数要求，默认3000
    - **language**: 输出语言，zh或en，默认zh
    - **structure**: 结构类型，默认standard
    """
    from fastapi.responses import StreamingResponse
    import json
    
    # 获取当前用户的文献列表
    if request.paper_ids:
        papers = db.query(Paper).filter(
            Paper.id.in_(request.paper_ids),
            Paper.user_id == current_user.id,
            Paper.status == "active"
        ).all()
    else:
        papers = db.query(Paper).filter(
            Paper.user_id == current_user.id,
            Paper.status == "active"
        ).all()

    if not papers:
        raise HTTPException(status_code=400, detail="没有可用的文献，请先上传文献")

    # 记录综述生成事件
    Tracker.track_event(
        db=db,
        user_id=current_user.id,
        event_name="generate_review",
        event_type="review",
        properties={
            "topic": request.topic,
            "paper_count": len(papers),
            "word_count": request.word_count,
            "language": request.language
        }
    )

    # 增加综述生成计数
    Tracker.increment_metric(db, current_user.id, "review_count")

    # 构建文献数据
    papers_data = []
    for paper in papers:
        import json
        papers_data.append({
            "id": paper.id,
            "title": paper.title or paper.file_name,
            "authors": json.loads(paper.authors) if paper.authors else [],
            "abstract": paper.abstract or "",
            "keywords": json.loads(paper.keywords) if paper.keywords else []
        })

    # 根据主题检索相关文本块
    chunks = []
    if request.topic:
        try:
            embedder = get_embedder()
            retriever = get_retriever()

            query_vector = embedder.encode([request.topic], normalize=True)
            search_results = retriever.search(query_vector[0], top_k=10)

            for result in search_results:
                chunks.append({
                    'content': result.get('content', ''),
                    'paper_title': result.get('paper_title', '未知文献'),
                    'page_number': result.get('page_number', '?')
                })
        except Exception as e:
            print(f"检索相关文本块失败: {str(e)}")

    # 生成综述流
    generator = get_review_generator()

    async def generate_stream():
        if chunks:
            # 使用详细模式（基于文本块）
            for chunk in generator.generate_review_with_chunks(
                topic=request.topic,
                papers=papers_data,
                chunks=chunks,
                word_count=request.word_count,
                language=request.language
            ):
                yield f"data: {json.dumps({'type': 'content', 'data': chunk})}\n\n"
        else:
            # 使用简化模式（基于摘要）
            for chunk in generator.generate_review(
                topic=request.topic,
                papers=papers_data,
                word_count=request.word_count,
                language=request.language
            ):
                yield f"data: {json.dumps({'type': 'content', 'data': chunk})}\n\n"

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream"
    )


@router.post("/outline", response_model=ResponseModel)
async def generate_outline(
    topic: str,
    paper_ids: Optional[List[int]] = None,
    db: Session = Depends(get_db)
):
    """
    生成综述大纲

    - **topic**: 综述主题
    - **paper_ids**: 指定文献ID列表（可选）
    """
    # 获取文献
    if paper_ids:
        papers = db.query(Paper).filter(
            Paper.id.in_(paper_ids),
            Paper.status == "active"
        ).all()
    else:
        papers = db.query(Paper).filter(Paper.status == "active").all()

    if not papers:
        raise HTTPException(status_code=400, detail="没有可用的文献")

    # 构建文献数据
    papers_data = []
    for paper in papers:
        import json
        papers_data.append({
            "id": paper.id,
            "title": paper.title or paper.file_name,
            "authors": json.loads(paper.authors) if paper.authors else [],
            "keywords": json.loads(paper.keywords) if paper.keywords else []
        })

    generator = get_review_generator()
    outline = generator.generate_outline(topic, papers_data)

    return ResponseModel(
        code=200,
        data={"outline": outline}
    )


@router.post("/export", response_model=ResponseModel)
async def export_review(
    content: str,
    format: str = "markdown",
    db: Session = Depends(get_db)
):
    """
    导出综述

    - **content**: 综述内容
    - **format**: 导出格式，支持 markdown/pdf/docx
    """
    import os
    import uuid
    from datetime import datetime

    if format not in ["markdown", "pdf", "docx"]:
        raise HTTPException(status_code=400, detail="不支持的导出格式")

    export_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"review_{timestamp}_{export_id}"

    if format == "markdown":
        # 直接返回Markdown内容
        return ResponseModel(
            code=200,
            data={
                "content": content,
                "filename": f"{filename}.md",
                "format": "markdown"
            }
        )

    elif format == "pdf":
        # TODO: 实现PDF导出（可以使用reportlab或weasyprint）
        # 暂时返回提示
        return ResponseModel(
            code=200,
            message="PDF导出功能开发中，请先使用Markdown格式",
            data={"format": "pdf"}
        )

    elif format == "docx":
        # TODO: 实现Word导出（可以使用python-docx）
        return ResponseModel(
            code=200,
            message="Word导出功能开发中，请先使用Markdown格式",
            data={"format": "docx"}
        )