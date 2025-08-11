from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from typing import Dict
import logging
import time
from datetime import datetime, timezone
import os
from pathlib import Path

from app.core.dependencies import get_current_active_user
from app.core.database import get_sync_db
from app.models.user import User, UserRole
from app.services.chat_service import ChatService
from sqlalchemy.orm import Session
from app.rag.pipeline.retrieval_pipeline import RetrievalPipeline
from app.rag.api.retriever_schemas import QueryRequest, QueryResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/rag", tags=["RAG Retriever"])

# Initialize retriever service
retriever_service = RetrievalPipeline()

@router.post("/query", response_model=QueryResponse)
async def query_documents(
    request: QueryRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_sync_db),
    http_request: Request = None
) -> QueryResponse:
    """
    Query documents using RAG with role-based access control and chat history
    
    - **SIGNED_UP**: Access to public documents only
    - **NON_PI_ACCESS**: Access to non-personal information documents
    - **PI_ACCESS**: Access to personal documents + non-PI documents
    
    **Multi-turn Conversation:**
    - If session_id is provided: Continue existing conversation
    - If session_id is None: Start new conversation
    - Returns error if session_id provided but doesn't exist
    """
    
    start_time = time.time()
    client_ip = http_request.client.host if http_request and http_request.client else "unknown"
    user_agent = http_request.headers.get("user-agent", "unknown") if http_request else "unknown"
    
    chat_service = ChatService(db)
    chat_session = None
    conversation_context = ""
    
    logger.info(
        f"RAG query from user {current_user.id} ({current_user.role.value}): "
        f"'{request.query[:100]}...' [Session: {request.session_id}]"
    )
    
    try:
        # Handle chat session logic
        if request.session_id:
            # Validate existing session
            chat_session = chat_service.get_chat_session(request.session_id, current_user.id)
            if not chat_session:
                raise HTTPException(
                    status_code=404,
                    detail="Chat session not found or expired"
                )
            
            # Add user message to existing session
            chat_service.add_user_message(request.session_id, current_user.id, request.query)
            
            # Get conversation context (last 10 messages)
            conversation_history = chat_service.get_conversation_context(
                request.session_id, current_user.id, last_n=10
            )
            conversation_context = chat_service.format_conversation_context(conversation_history)
            
        else:
            # Create new chat session
            chat_session = chat_service.create_chat_session(current_user.id, request.query)
        
        # Build enhanced query with conversation context
        enhanced_query = request.query
        if conversation_context:
            enhanced_query = f"{conversation_context}Current question: {request.query}"
        
        # Process the query with the retriever service
        rag_response = await retriever_service.retrieve_and_answer(
            query=enhanced_query,
            user=current_user,
            session_id=chat_session.session_id,
            top_k_pre=request.top_k_pre,
            top_k_post=request.top_k_post,
            ip_address=client_ip,
            user_agent=user_agent 
        )
        
        # Add assistant response to chat session
        chat_service.add_assistant_response(
            chat_session.session_id, 
            current_user.id, 
            rag_response.answer
        )
        
        # Calculate processing time
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        # Log query for compliance
        chat_service.log_query(
            user_id=current_user.id,
            user_query=request.query,
            llm_prompt=enhanced_query,  # Include conversation context in logs
            llm_response=rag_response.answer,
            processing_time_ms=processing_time_ms,
            session_id=chat_session.session_id,
            retrieved_chunks=[],  # TODO: Add retrieved chunks from response
            context_metadata={
                "conversation_context_included": bool(conversation_context),
                "context_length": len(conversation_context) if conversation_context else 0,
                "top_k_pre": request.top_k_pre,
                "top_k_post": request.top_k_post
            },
            ip_address=client_ip,
            user_agent=user_agent
        )
        
        # Return response (session_id already included in rag_response)
        return rag_response
        
    except HTTPException:
        # Re-raise HTTP exceptions (like 404 for invalid session_id)
        raise
    except Exception as e:
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        # Log error for compliance
        chat_service.log_query(
            user_id=current_user.id,
            user_query=request.query,
            llm_prompt=enhanced_query if 'enhanced_query' in locals() else request.query,
            llm_response="",
            processing_time_ms=processing_time_ms,
            session_id=chat_session.session_id if chat_session else None,
            ip_address=client_ip,
            user_agent=user_agent,
            error_message=str(e),
            error_type=type(e).__name__
        )
        
        logger.error(f"Query processing failed for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to process your query. Please try again later."
        )

@router.get("/status")
async def get_retriever_status(
    current_user: User = Depends(get_current_active_user)
) -> Dict:
    """
    Get RAG retriever service status
    
    Requires authentication but available to all user roles.
    """
    
    try:
        status = retriever_service.get_service_status()
        
        # Add user-specific access information
        status["user_access"] = {
            "user_id": current_user.id,
            "role": current_user.role.value,
            "can_access_pi": current_user.role == UserRole.PI_ACCESS,
            "can_access_non_pi": current_user.role in [UserRole.NON_PI_ACCESS, UserRole.PI_ACCESS] or current_user.role == UserRole.SIGNED_UP
        }
        
        return status
        
    except Exception as e:
        logger.error(f"Failed to get retriever status: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get service status"
        )

@router.get("/access-summary")
async def get_user_access_summary(
    current_user: User = Depends(get_current_active_user)
) -> Dict:
    """
    Get summary of what documents the current user can access
    """
    
    from app.rag.access_control import AccessController
    
    try:
        access_controller = AccessController()
        summary = access_controller.get_user_access_summary(current_user)
        
        # Add role descriptions for frontend
        role_descriptions = {
            "signed_up": "Basic access to public documents only",
            "non_pi_access": "Access to all non-personal information documents", 
            "pi_access": "Full access to your personal documents and public documents"
        }
        
        summary["role_description"] = role_descriptions.get(
            current_user.role.value, 
            "Unknown role"
        )
        
        summary["access_rules"] = {
            "public_documents": "✅ Can access",
            "non_pi_documents": "✅ Can access" if current_user.role != UserRole.SIGNED_UP else "❌ No access",
            "personal_pi_documents": "✅ Can access your own" if current_user.role == UserRole.PI_ACCESS else "❌ No access",
            "other_users_pi_documents": "❌ Never accessible"
        }
        
        return summary
        
    except Exception as e:
        logger.error(f"Failed to get access summary for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get access summary"
        )

@router.get("/chat-sessions")
async def get_user_chat_sessions(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_sync_db),
    limit: int = 50
):
    """Get user's chat sessions"""
    chat_service = ChatService(db)
    sessions = chat_service.get_user_chat_sessions(current_user.id, limit)
    
    return [
        {
            "session_id": session.session_id,
            "title": session.title,
            "message_count": session.get_message_count(),
            "created_at": session.created_at,
            "updated_at": session.updated_at,
            "expires_at": session.expires_at
        }
        for session in sessions
    ]

@router.get("/chat-sessions/{session_id}")
async def get_chat_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_sync_db)
):
    """Get specific chat session with full conversation"""
    from uuid import UUID
    
    try:
        session_uuid = UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid session ID format")
    
    chat_service = ChatService(db)
    session = chat_service.get_chat_session(session_uuid, current_user.id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found or expired")
    
    return {
        "session_id": session.session_id,
        "title": session.title,
        "conversation": session.conversation_data,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
        "expires_at": session.expires_at,
        "message_count": session.get_message_count()
    }

@router.delete("/chat-sessions/{session_id}")
async def delete_chat_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_sync_db)
):
    """Delete a chat session"""
    from uuid import UUID
    
    try:
        session_uuid = UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid session ID format")
    
    chat_service = ChatService(db)
    success = chat_service.delete_chat_session(session_uuid, current_user.id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Chat session not found")
    
    return {"message": "Chat session deleted successfully"}

@router.get("/images/{chunk_id}")
async def get_chunk_image(
    chunk_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Serve image files for RAG chunks
    
    Returns the image file associated with a specific chunk ID.
    Access control is handled by the RAG pipeline - only chunks
    the user has access to will be returned in queries.
    """
    try:
        # Query Qdrant to get chunk metadata and verify access
        from app.rag.index_qdrant import get_client
        
        client = get_client()
        
        # Retrieve the specific chunk by ID
        points = client.retrieve(
            collection_name="document_chunks",
            ids=[chunk_id]
        )
        
        if not points:
            raise HTTPException(status_code=404, detail="Chunk not found")
        
        chunk = points[0]
        payload = chunk.payload
        
        # Check if it's an image chunk
        if not payload.get("is_image", False):
            raise HTTPException(status_code=400, detail="Chunk is not an image")
        
        # Get image path from metadata
        image_url = payload.get("image_url")
        if not image_url:
            raise HTTPException(status_code=404, detail="Image file not found in metadata")
        
        # Convert to absolute path and verify file exists
        image_path = Path(image_url)
        if not image_path.is_absolute():
            # If relative path, make it relative to backend directory
            image_path = Path(__file__).parent.parent.parent / image_path
        
        if not image_path.exists():
            raise HTTPException(status_code=404, detail="Image file not found on disk")
        
        # Determine media type from file extension
        media_type = "image/jpeg"  # default
        ext = image_path.suffix.lower()
        if ext in [".png"]:
            media_type = "image/png"
        elif ext in [".gif"]:
            media_type = "image/gif"
        elif ext in [".webp"]:
            media_type = "image/webp"
        
        return FileResponse(
            path=str(image_path),
            media_type=media_type,
            filename=f"{chunk_id}{image_path.suffix}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to serve image for chunk {chunk_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve image"
        )
