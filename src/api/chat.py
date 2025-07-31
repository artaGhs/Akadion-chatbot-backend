"""
Chat API endpoints for handling user questions and streaming responses.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator

from ..models.schemas import ChatRequest, ChatResponse, ErrorResponse
from ..services.rag_service import RAGService
from ..services.conversation_manager import conversation_manager

router = APIRouter(prefix="/chat", tags=["chat"])

# Initialize RAG service
rag_service = RAGService()


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Process a chat message and return a response using RAG.
    
    Args:
        request: Chat request containing the user's message
        
    Returns:
        ChatResponse with generated answer and sources
    """
    try:
        if not request.message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        response = await rag_service.generate_response(request)
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing chat request: {str(e)}")


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """
    Process a chat message and return a streaming response using RAG.
    
    Args:
        request: Chat request containing the user's message
        
    Returns:
        StreamingResponse with real-time generated answer
    """
    try:
        if not request.message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        async def generate_response() -> AsyncGenerator[str, None]:
            """Generate streaming response chunks."""
            async for chunk in rag_service.generate_streaming_response(request):
                # Format as Server-Sent Events (SSE)
                yield f"data: {chunk}\n\n"
            
            # Send end signal
            yield "data: [DONE]\n\n"
        
        return StreamingResponse(
            generate_response(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/plain; charset=utf-8"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing streaming chat request: {str(e)}")


@router.get("/stats")
async def get_chat_stats():
    """
    Get statistics about the chat system and knowledge base.
    
    Returns:
        Dictionary with system statistics
    """
    try:
        knowledge_base_stats = rag_service.get_collection_stats()
        conversation_stats = conversation_manager.get_stats()
        
        return {
            "status": "healthy",
            "knowledge_base": knowledge_base_stats,
            "conversations": conversation_stats
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving chat stats: {str(e)}")


@router.delete("/conversation/{session_id}")
async def clear_conversation(session_id: str):
    """
    Clear conversation history for a specific session.
    
    Args:
        session_id: Session identifier to clear
        
    Returns:
        Success message
    """
    try:
        success = conversation_manager.clear_conversation(session_id)
        
        if success:
            return {"message": f"Conversation {session_id} cleared successfully", "success": True}
        else:
            return {"message": f"No conversation found for session {session_id}", "success": False}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing conversation: {str(e)}")


@router.get("/conversation/{session_id}")
async def get_conversation_history(session_id: str, limit: int = 10):
    """
    Get conversation history for a specific session.
    
    Args:
        session_id: Session identifier
        limit: Maximum number of messages to return
        
    Returns:
        List of conversation messages
    """
    try:
        messages = conversation_manager.get_recent_messages(session_id, limit)
        
        return {
            "session_id": session_id,
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat()
                }
                for msg in messages
            ],
            "message_count": len(messages)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving conversation: {str(e)}")


@router.post("/cleanup-sessions")
async def cleanup_expired_sessions():
    """
    Clean up expired conversation sessions.
    
    Returns:
        Number of sessions cleaned up
    """
    try:
        cleaned_count = conversation_manager.cleanup_expired_sessions()
        
        return {
            "message": f"Cleaned up {cleaned_count} expired sessions",
            "cleaned_sessions": cleaned_count
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error cleaning up sessions: {str(e)}") 