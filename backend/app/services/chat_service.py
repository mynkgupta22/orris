import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta, UTC
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy.exc import NoResultFound

from app.models.chat_history import ChatHistory
from app.models.query_log import QueryLog
from app.models.user import User

logger = logging.getLogger(__name__)

class ChatService:
    def __init__(self, db: Session):
        self.db = db

    def create_chat_session(self, user_id: int, first_question: str) -> ChatHistory:
        """Create a new chat session with the first user question"""
        expires_at = datetime.now(UTC) + timedelta(days=30)
        
        chat_session = ChatHistory(
            user_id=user_id,
            title=first_question[:50],  # First 50 chars as title
            conversation_data={"messages": []},
            expires_at=expires_at
        )
        
        # Add first human message
        chat_session.add_message(
            role="human",
            content=first_question,
            timestamp=datetime.now(UTC).isoformat()
        )
        
        self.db.add(chat_session)
        self.db.commit()
        self.db.refresh(chat_session)
        
        return chat_session

    def get_chat_session(self, session_id: UUID, user_id: int) -> Optional[ChatHistory]:
        """Get chat session by session_id and user_id"""
        try:
            chat_session = self.db.query(ChatHistory).filter(
                ChatHistory.session_id == session_id,
                ChatHistory.user_id == user_id
            ).one()
            
            # Check if session is expired
            if chat_session.is_expired():
                return None
                
            return chat_session
        except NoResultFound:
            return None

    def add_assistant_response(self, session_id: UUID, user_id: int, content: str, image_base64: Optional[str] = None):
        """Add assistant's response to a chat session."""
        session = self.get_chat_session(session_id, user_id)
        if not session:
            logger.warning(f"Attempted to add assistant response to non-existent session {session_id}")
            return
        
        timestamp = datetime.now(UTC).isoformat()
        session.add_message(
            role="assistant",
            content=content,
            timestamp=timestamp
        )
        
        # If there's an image, find the message we just added and append the key
        if image_base64:
            # The message is the last one in the list
            if session.conversation_data and session.conversation_data.get("messages"):
                session.conversation_data["messages"][-1]["image_base64"] = image_base64
        
        self.db.commit()

    def add_user_message(self, session_id: UUID, user_id: int, message: str) -> bool:
        """Add user message to existing chat session"""
        chat_session = self.get_chat_session(session_id, user_id)
        if not chat_session:
            return False
            
        chat_session.add_message(
            role="human",
            content=message,
            timestamp=datetime.now(UTC).isoformat()
        )
        
        self.db.commit()
        return True

    def get_conversation_context(self, session_id: UUID, user_id: int, last_n: int = 10) -> List[Dict[str, str]]:
        """Get last N messages from conversation for context"""
        chat_session = self.get_chat_session(session_id, user_id)
        if not chat_session:
            return []
            
        return chat_session.get_last_n_messages(last_n)

    def get_user_chat_sessions(self, user_id: int, limit: int = 50) -> List[ChatHistory]:
        """Get user's chat sessions ordered by most recent"""
        return self.db.query(ChatHistory).filter(
            ChatHistory.user_id == user_id,
            ChatHistory.expires_at > datetime.now(UTC)
        ).order_by(ChatHistory.updated_at.desc()).limit(limit).all()

    def delete_chat_session(self, session_id: UUID, user_id: int) -> bool:
        """Delete a chat session"""
        chat_session = self.get_chat_session(session_id, user_id)
        if not chat_session:
            return False
            
        self.db.delete(chat_session)
        self.db.commit()
        return True

    def format_conversation_context(self, messages: List[Dict[str, str]]) -> str:
        """Format conversation messages for LLM context"""
        if not messages:
            return ""
            
        context_lines = []
        for msg in messages:
            role = "User" if msg["role"] == "human" else "Assistant"
            context_lines.append(f"{role}: {msg['content']}")
            
        return "Previous conversation:\n" + "\n".join(context_lines) + "\n\n"

    def log_query(
        self,
        user_id: int,
        user_query: str,
        llm_prompt: str,
        llm_response: str,
        processing_time_ms: int,
        session_id: Optional[UUID] = None,
        retrieved_chunks: Optional[List[Dict]] = None,
        context_metadata: Optional[Dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        error_message: Optional[str] = None,
        error_type: Optional[str] = None
    ) -> QueryLog:
        """Log a query for compliance purposes"""
        query_log = QueryLog.create_log(
            user_id=user_id,
            session_id=session_id,
            user_query=user_query,
            llm_prompt=llm_prompt,
            llm_response=llm_response,
            processing_time_ms=processing_time_ms,
            retrieved_chunks=retrieved_chunks,
            context_metadata=context_metadata,
            ip_address=ip_address,
            user_agent=user_agent,
            error_message=error_message,
            error_type=error_type
        )
        
        self.db.add(query_log)
        self.db.commit()
        self.db.refresh(query_log)
        
        return query_log

    def cleanup_expired_sessions(self) -> int:
        """Clean up expired chat sessions (run this as a background task)"""
        expired_sessions = self.db.query(ChatHistory).filter(
            ChatHistory.expires_at < datetime.now(UTC)
        )
        
        count = expired_sessions.count()
        expired_sessions.delete()
        self.db.commit()
        
        return count
