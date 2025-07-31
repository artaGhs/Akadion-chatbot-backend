"""
In-memory conversation management service.
Handles storing and retrieving conversation history for active sessions.
"""

import uuid
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from ..models.schemas import Conversation, ConversationMessage
from ..core.config import settings


class ConversationManager:
    """Manages in-memory conversation storage and retrieval."""
    
    def __init__(self):
        """Initialize the conversation manager."""
        # In-memory storage: session_id -> Conversation
        self._conversations: Dict[str, Conversation] = {}
        
        # Configuration
        self.max_history_messages = getattr(settings, 'max_history_messages', 10)  # Keep last 10 messages
        self.session_timeout_hours = getattr(settings, 'session_timeout_hours', 24)  # 24 hour timeout
    
    def get_conversation(self, session_id: str) -> Conversation:
        """
        Get or create a conversation for the given session ID.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            Conversation object for the session
        """
        if session_id not in self._conversations:
            self._conversations[session_id] = Conversation(session_id=session_id)
        
        # Update last accessed time
        self._conversations[session_id].last_updated = datetime.now()
        
        return self._conversations[session_id]
    
    def add_message(self, session_id: str, role: str, content: str) -> None:
        """
        Add a message to the conversation.
        
        Args:
            session_id: Session identifier
            role: Message role ('user' or 'assistant')
            content: Message content
        """
        conversation = self.get_conversation(session_id)
        
        message = ConversationMessage(
            role=role,
            content=content,
            timestamp=datetime.now()
        )
        
        conversation.messages.append(message)
        conversation.last_updated = datetime.now()
        
        # Trim conversation if it gets too long
        self._trim_conversation(conversation)
    
    def get_recent_messages(self, session_id: str, limit: Optional[int] = None) -> List[ConversationMessage]:
        """
        Get recent messages from a conversation.
        
        Args:
            session_id: Session identifier
            limit: Maximum number of messages to return (defaults to max_history_messages)
            
        Returns:
            List of recent conversation messages
        """
        conversation = self.get_conversation(session_id)
        
        if limit is None:
            limit = self.max_history_messages
        
        # Return the most recent messages (up to the limit)
        return conversation.messages[-limit:] if conversation.messages else []
    
    def get_conversation_context(self, session_id: str, include_current: bool = False) -> str:
        """
        Get formatted conversation context for including in prompts.
        
        Args:
            session_id: Session identifier
            include_current: Whether to include the very latest message
            
        Returns:
            Formatted conversation history string
        """
        messages = self.get_recent_messages(session_id)
        
        if not messages:
            return ""
        
        # If we don't want to include current message, remove the last one
        if not include_current and messages:
            messages = messages[:-1]
        
        if not messages:
            return ""
        
        # Format messages for context
        context_parts = []
        for msg in messages:
            role_label = "Human" if msg.role == "user" else "Assistant"
            context_parts.append(f"{role_label}: {msg.content}")
        
        return "\n\n".join(context_parts)
    
    def clear_conversation(self, session_id: str) -> bool:
        """
        Clear a conversation.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if conversation was cleared, False if it didn't exist
        """
        if session_id in self._conversations:
            del self._conversations[session_id]
            return True
        return False
    
    def _trim_conversation(self, conversation: Conversation) -> None:
        """
        Trim conversation to keep only recent messages.
        
        Args:
            conversation: Conversation to trim
        """
        if len(conversation.messages) > self.max_history_messages:
            # Keep only the most recent messages
            conversation.messages = conversation.messages[-self.max_history_messages:]
    
    def cleanup_expired_sessions(self) -> int:
        """
        Remove expired conversation sessions.
        
        Returns:
            Number of sessions cleaned up
        """
        cutoff_time = datetime.now() - timedelta(hours=self.session_timeout_hours)
        expired_sessions = []
        
        for session_id, conversation in self._conversations.items():
            if conversation.last_updated < cutoff_time:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self._conversations[session_id]
        
        return len(expired_sessions)
    
    def get_active_sessions_count(self) -> int:
        """Get the number of active conversation sessions."""
        return len(self._conversations)
    
    def get_stats(self) -> dict:
        """Get conversation manager statistics."""
        total_sessions = len(self._conversations)
        total_messages = sum(len(conv.messages) for conv in self._conversations.values())
        
        return {
            "active_sessions": total_sessions,
            "total_messages": total_messages,
            "max_history_messages": self.max_history_messages,
            "session_timeout_hours": self.session_timeout_hours
        }


# Global conversation manager instance
conversation_manager = ConversationManager()