"""
Chat API routes:
- POST   /api/kbs/{kb_id}/chat/sessions                    — Create session
- GET    /api/kbs/{kb_id}/chat/sessions                    — List sessions
- GET    /api/chat/sessions/{session_id}/messages           — Get messages
- POST   /api/chat/sessions/{session_id}/messages           — Send message (non-streaming)
- POST   /api/chat/sessions/{session_id}/stream             — Stream Q&A (SSE)
- DELETE /api/chat/sessions/{session_id}                    — Delete session
"""

import json
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db, async_session
from app.core.deps import get_current_user
from app.core.permissions import KBAccessLevel, require_kb_access
from app.models import ChatMessage, ChatSession, MessageRole, User
from app.rag.rag_service import RAGService
from app.schemas.chat import (
    MessageCreate,
    MessageResponse,
    SessionCreate,
    SessionResponse,
    StreamRequest,
)

router = APIRouter(tags=["Chat"])
settings = get_settings()
logger = logging.getLogger(__name__)


async def _get_session_with_kb_access(
    db: AsyncSession,
    session_id: int,
    current_user: User,
    level: KBAccessLevel = KBAccessLevel.VIEWER,
) -> ChatSession:
    """Load a chat session owned by the user and verify KB access."""
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
    await require_kb_access(db, session.knowledge_base_id, current_user, level)
    return session


# ============================================
# Session Management
# ============================================

@router.post("/api/kbs/{kb_id}/chat/sessions", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    kb_id: int,
    req: SessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new chat session in a knowledge base."""
    await require_kb_access(db, kb_id, current_user, KBAccessLevel.VIEWER)

    session = ChatSession(
        knowledge_base_id=kb_id,
        user_id=current_user.id,
        title=req.title,
    )
    db.add(session)
    await db.flush()
    return session


@router.get("/api/kbs/{kb_id}/chat/sessions", response_model=list[SessionResponse])
async def list_sessions(
    kb_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List chat sessions for a knowledge base, newest first."""
    await require_kb_access(db, kb_id, current_user, KBAccessLevel.VIEWER)

    result = await db.execute(
        select(ChatSession)
        .where(
            ChatSession.knowledge_base_id == kb_id,
            ChatSession.user_id == current_user.id,
        )
        .order_by(ChatSession.updated_at.desc())
    )
    return result.scalars().all()


@router.delete("/api/chat/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a chat session and all its messages."""
    session = await _get_session_with_kb_access(db, session_id, current_user)

    await db.delete(session)
    await db.flush()


# ============================================
# Messages
# ============================================

@router.get("/api/chat/sessions/{session_id}/messages", response_model=list[MessageResponse])
async def get_messages(
    session_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get messages for a chat session, oldest first."""
    await _get_session_with_kb_access(db, session_id, current_user)

    msg_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
        .limit(limit)
    )
    return msg_result.scalars().all()


@router.post("/api/chat/sessions/{session_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    session_id: int,
    req: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Save a user message (non-streaming fallback)."""
    await _get_session_with_kb_access(db, session_id, current_user)

    message = ChatMessage(
        session_id=session_id,
        user_id=current_user.id,
        role=MessageRole.USER,
        content=req.content,
    )
    db.add(message)
    await db.flush()
    return message


# ============================================
# Streaming Q&A (SSE)
# ============================================

@router.post("/api/chat/sessions/{session_id}/stream")
async def stream_chat(
    session_id: int,
    req: StreamRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Stream a RAG-enhanced answer via Server-Sent Events.

    SSE event types:
    - retrieval_start  — Starting vector search
    - retrieval_done   — Retrieved N chunks
    - token            — LLM output token
    - references       — Source references
    - done             — Complete (includes full answer + refs)
    - error            — Error occurred
    """
    # Validate session and KB access
    session = await _get_session_with_kb_access(db, session_id, current_user)

    kb_id = session.knowledge_base_id

    # Get recent chat history
    history_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(settings.MAX_CHAT_HISTORY_ROUNDS * 2)  # user + assistant per round
    )
    recent_messages = list(reversed(history_result.scalars().all()))  # oldest first

    chat_history = [
        {"role": msg.role.value if hasattr(msg.role, 'value') else msg.role, "content": msg.content}
        for msg in recent_messages
    ]

    rag_service = RAGService()

    async def event_generator() -> AsyncGenerator[str, None]:
        """Generate SSE events with RAG pipeline."""
        full_answer = ""
        references = []

        # Use a fresh DB session for RAG filtering + saving
        async with async_session() as rag_db:
            try:
                async for event in rag_service.stream_answer(
                    knowledge_base_id=kb_id,
                    question=req.content,
                    chat_history=chat_history,
                    db=rag_db,
                    top_k=req.top_k,
                    user_id=current_user.id,
                ):
                    event_type = event.get("event", "message")
                    data = event.get("data", {})

                    # Serialize as SSE
                    data_json = json.dumps(data, ensure_ascii=False)
                    yield f"event: {event_type}\ndata: {data_json}\n\n"

                    if event_type == "token":
                        full_answer += data.get("content", "")
                    elif event_type == "references":
                        references = data
                    elif event_type == "done":
                        if not full_answer and data.get("content"):
                            full_answer = data["content"]
                        if not references and data.get("references"):
                            references = data["references"]

                    if event_type == "error":
                        return

            except Exception:
                logger.exception("SSE stream error")
                error_data = json.dumps(
                    {"message": "An error occurred while generating the response."},
                    ensure_ascii=False,
                )
                yield f"event: error\ndata: {error_data}\n\n"
                return

            # Save results to DB after streaming completes
            if full_answer:
                try:
                    await rag_service.save_rag_results(
                        db=rag_db,
                        session_id=session_id,
                        user_id=current_user.id,
                        question=req.content,
                        answer=full_answer,
                        references=references if isinstance(references, list) else [],
                    )
                except Exception as e:
                    logger.exception(f"Failed to save RAG results: {e}")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
