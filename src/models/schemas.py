"""
Pydantic models for API request and response validation.
Provides automatic data validation, conversion, and OpenAPI schema generation.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    message: str = Field(..., min_length=1, max_length=1000, description="User's question or message")
    stream: bool = Field(default=True, description="Whether to stream the response")
    session_id: str = Field(default="default", description="Session ID for conversation tracking")


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    response: str = Field(..., description="Generated response from the RAG system")
    sources: List[str] = Field(default=[], description="Source chunks used for generation")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")


class FileUploadResponse(BaseModel):
    """Response model for file upload/ingestion endpoint."""
    message: str = Field(..., description="Status message")
    filename: str = Field(..., description="Name of the uploaded file")
    chunks_processed: int = Field(..., description="Number of text chunks processed")
    success: bool = Field(..., description="Whether the ingestion was successful")
    timestamp: datetime = Field(default_factory=datetime.now, description="Upload timestamp")


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""
    status: str = Field(default="healthy", description="Service health status")
    timestamp: datetime = Field(default_factory=datetime.now, description="Health check timestamp")
    version: str = Field(default="1.0.0", description="API version")


class ErrorResponse(BaseModel):
    """Response model for error cases."""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")


class TextChunk(BaseModel):
    """Model representing a text chunk with metadata."""
    id: str = Field(..., description="Unique identifier for the chunk")
    text: str = Field(..., description="The text content of the chunk")
    source: str = Field(..., description="Source file or document")
    page_number: Optional[int] = Field(None, description="Page number (for PDFs)")
    embedding: Optional[List[float]] = Field(None, description="Vector embedding of the text")


class ConversationMessage(BaseModel):
    """Model representing a single message in a conversation."""
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.now, description="Message timestamp")


class Conversation(BaseModel):
    """Model representing a conversation session."""
    session_id: str = Field(..., description="Unique session identifier")
    messages: List[ConversationMessage] = Field(default=[], description="List of messages in conversation")
    created_at: datetime = Field(default_factory=datetime.now, description="Conversation creation time")
    last_updated: datetime = Field(default_factory=datetime.now, description="Last message time") 