"""
对话问答API路由
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.database import get_db, ChatSession, ChatMessage, Paper, Chunk, User
from app.models.schemas import (
    ResponseModel, 
    ChatSessionCreate, 
    ChatSessionResponse,
    ChatMessageCreate,
    ChatMessageResponse,
    AgentRequest,
    AgentResponse
)
from app.core.kimi_client import get_kimi_client
from app.services.agent_service import get_agent_service
from app.core.embedder import get_embedder
from app.core.faiss_retriever import get_retriever
from app.core.auth import get_current_user
from app.core.analytics import Tracker

router = APIRouter()
agent_service = get_agent_service()


@router.post("/sessions", response_model=ResponseModel)
async def create_session(
    session: ChatSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建对话会话"""
    db_session = ChatSession(
        user_id=current_user.id,
        session_name=session.session_name or "新会话"
    )
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    
    # 记录会话创建事件
    Tracker.track_event(
        db=db,
        user_id=current_user.id,
        event_name="create_chat_session",
        event_type="chat",
        properties={"session_name": session.session_name}
    )
    
    return ResponseModel(
        code=200,
        data={
            "id": db_session.id,
            "session_name": db_session.session_name,
            "created_at": db_session.created_at,
            "updated_at": db_session.updated_at
        }
    )


@router.get("/sessions", response_model=ResponseModel)
async def list_sessions(
    page: int = 1,
    size: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取会话列表"""
    query = db.query(ChatSession).filter(ChatSession.user_id == current_user.id)
    total = query.count()
    sessions = query.order_by(ChatSession.updated_at.desc()).offset((page - 1) * size).limit(size).all()
    
    return ResponseModel(
        code=200,
        data={
            "total": total,
            "items": [
                {
                    "id": s.id,
                    "session_name": s.session_name,
                    "created_at": s.created_at,
                    "updated_at": s.updated_at
                }
                for s in sessions
            ]
        }
    )


@router.get("/sessions/{session_id}", response_model=ResponseModel)
async def get_session(
    session_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取会话详情和历史消息"""
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在或无权访问")
    
    messages = db.query(ChatMessage).filter(
        ChatMessage.session_id == session_id
    ).order_by(ChatMessage.created_at).all()
    
    return ResponseModel(
        code=200,
        data={
            "session": {
                "id": session.id,
                "session_name": session.session_name,
                "created_at": session.created_at,
                "updated_at": session.updated_at
            },
            "messages": [
                {
                    "id": m.id,
                    "role": m.role,
                    "content": m.content,
                    "references": eval(m.references) if m.references else None,
                    "created_at": m.created_at
                }
                for m in messages
            ]
        }
    )


@router.delete("/sessions/{session_id}", response_model=ResponseModel)
async def delete_session(
    session_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除会话"""
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在或无权访问")
    
    db.delete(session)
    db.commit()
    
    return ResponseModel(code=200, message="删除成功")


@router.post("/messages")
async def send_message(
    message: ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    发送消息并获取回复（流式响应）
    
    - **session_id**: 会话ID
    - **message**: 用户消息
    - **paper_ids**: 指定文献范围（可选）
    """
    from fastapi.responses import StreamingResponse
    import json
    
    # 检查会话
    session = db.query(ChatSession).filter(
        ChatSession.id == message.session_id,
        ChatSession.user_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在或无权访问")
    
    # 保存用户消息
    user_msg = ChatMessage(
        session_id=message.session_id,
        role="user",
        content=message.message
    )
    db.add(user_msg)
    db.commit()
    
    # 记录聊天事件
    Tracker.track_event(
        db=db,
        user_id=current_user.id,
        event_name="chat_message",
        event_type="chat",
        properties={"session_id": message.session_id, "has_paper_ids": bool(message.paper_ids)}
    )
    
    # 增加聊天次数计数
    Tracker.increment_metric(db, current_user.id, "chat_count")
    
    # 获取历史消息（最近10条）
    history = db.query(ChatMessage).filter(
        ChatMessage.session_id == message.session_id
    ).order_by(ChatMessage.created_at.desc()).limit(10).all()
    
    chat_history = [
        {"role": h.role, "content": h.content}
        for h in reversed(history)
    ]
    
    # 检索相关文献内容（只检索当前用户的文献）
    contexts = []
    if message.paper_ids:
        # 指定文献范围 - 检查是否属于当前用户
        chunks = db.query(Chunk).join(Paper).filter(
            Chunk.paper_id.in_(message.paper_ids),
            Paper.user_id == current_user.id
        ).all()
        
        # 简单文本匹配（可以优化为向量检索）
        keywords = message.message.split()
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
        
        # 按相关度排序
        contexts.sort(key=lambda x: x['score'], reverse=True)
        contexts = contexts[:5]
    else:
        # 使用向量检索
        try:
            embedder = get_embedder()
            retriever = get_retriever()
            
            print(f"[RAG检索] 查询: {message.message[:50]}...")
            print(f"[RAG检索] FAISS索引向量数: {retriever.index.ntotal if retriever.index else 0}")
            
            query_vector = embedder.encode([message.message], normalize=True)
            print(f"[RAG检索] 查询向量维度: {query_vector.shape}")
            
            # 使用较低的阈值确保能返回结果（简单嵌入器相似度可能不高）
            search_results = retriever.search(query_vector[0], top_k=5, threshold=0.1)
            print(f"[RAG检索] 检索结果数: {len(search_results)}")
            
            # 如果没有结果，尝试更低阈值或从数据库获取
            if not search_results:
                print(f"[RAG检索] 向量检索无结果，从数据库获取最新文献...")
                # 从数据库获取当前用户的最近上传的文献内容
                chunks = db.query(Chunk).join(Paper).filter(
                    Paper.user_id == current_user.id,
                    Paper.status == "active"
                ).order_by(Chunk.id.desc()).limit(5).all()
                
                for chunk in chunks:
                    paper = db.query(Paper).filter(Paper.id == chunk.paper_id).first()
                    contexts.append({
                        'content': chunk.content,
                        'paper_title': paper.title if paper else '未知文献',
                        'page_number': chunk.page_number,
                        'score': 0.5  # 默认分数
                    })
                
                print(f"[RAG检索] 从数据库获取 {len(contexts)} 个文本块")
            
            for result in search_results:
                contexts.append({
                    'content': result.get('content', ''),
                    'paper_title': result.get('paper_title', '未知文献'),
                    'page_number': result.get('page_number', '?'),
                    'score': result.get('score', 0)
                })
                print(f"[RAG检索] 匹配: {result.get('paper_title', '未知')} (得分: {result.get('score', 0):.3f})")
                
        except Exception as e:
            print(f"[RAG检索] 向量检索失败: {str(e)}")
            import traceback
            traceback.print_exc()
    
    # 构建Prompt
    kimi = get_kimi_client()
    messages_for_kimi = kimi.build_rag_prompt(
        query=message.message,
        contexts=contexts,
        chat_history=chat_history[:-1] if len(chat_history) > 1 else None
    )
    
    # 生成回复流
    async def generate_response():
        full_response = []
        references = []
        
        # 发送检索到的上下文信息
        if contexts:
            ref_data = [
                {
                    "paper_title": c.get("paper_title"),
                    "page_number": c.get("page_number"),
                    "score": round(c.get("score", 0), 3)
                }
                for c in contexts
            ]
            yield f"data: {json.dumps({'type': 'references', 'data': ref_data})}\n\n"
        
        # 流式生成回复
        for chunk in kimi.chat_completion(messages_for_kimi, stream=True):
            full_response.append(chunk)
            yield f"data: {json.dumps({'type': 'content', 'data': chunk})}\n\n"
        
        # 保存完整回复到数据库
        complete_response = "".join(full_response)
        assistant_msg = ChatMessage(
            session_id=message.session_id,
            role="assistant",
            content=complete_response,
            references=str([
                {
                    "paper_title": c.get("paper_title"),
                    "page_number": c.get("page_number")
                }
                for c in contexts
            ]) if contexts else None
        )
        db.add(assistant_msg)
        db.commit()
        
        # 更新会话时间
        session.updated_at = func.now()
        db.commit()
        
        # 发送完成标记
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
    
    return StreamingResponse(
        generate_response(),
        media_type="text/event-stream"
    )


@router.post("/agent/process", response_model=ResponseModel)
async def agent_process(
    request: AgentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """智能体处理接口"""
    result = agent_service.process_query(
        user_query=request.query,
        user_id=current_user.id,
        db=db
    )
    return ResponseModel(
        code=200,
        data={
            "summary": result.get("summary", "任务执行完成"),
            "response": result.get("summary", "任务执行完成"),
            "tasks": result.get("tasks", []),
            "results": result.get("results", {})
        }
    )


@router.post("/agent/create")
async def create_agent():
    """创建智能体"""
    agent_id = agent_service.create_agent()
    return {"agent_id": agent_id}


@router.get("/agent/count")
async def get_agent_count():
    """获取智能体数量"""
    count = agent_service.get_agent_count()
    return {"count": count}


@router.delete("/agent/{agent_id}")
async def delete_agent(agent_id: str):
    """删除智能体"""
    success = agent_service.delete_agent(agent_id)
    return {"success": success}