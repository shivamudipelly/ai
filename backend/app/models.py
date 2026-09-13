from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class MessageRole(str, Enum):
    """Role of the message sender"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class MessageBase(BaseModel):
    """Base schema for a message"""
    content: str = Field(..., description="The message content")
    role: MessageRole = Field(..., description="Role of the sender")


class MessageCreate(MessageBase):
    """Schema for creating a new message"""
    conversation_id: str = Field(..., description="ID of the conversation this message belongs to")


class Message(MessageBase):
    """Complete message schema with all fields"""
    id: str = Field(..., description="Unique message ID")
    conversation_id: str = Field(..., description="ID of the parent conversation")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Message creation timestamp")
    metadata: Optional[dict] = Field(default=None, description="Additional metadata (e.g., tool calls, sources)")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "msg_123456",
                "conversation_id": "conv_789012",
                "content": "What is the current price of TCS stock?",
                "role": "user",
                "created_at": "2024-01-15T10:30:00Z",
                "metadata": None
            }
        }


class ConversationBase(BaseModel):
    """Base schema for a conversation"""
    title: str = Field(..., description="Conversation title")
    user_id: str = Field(..., description="ID of the user who owns this conversation")


class ConversationCreate(ConversationBase):
    """Schema for creating a new conversation"""
    pass


class Conversation(ConversationBase):
    """Complete conversation schema with all fields"""
    id: str = Field(..., description="Unique conversation ID")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Conversation creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    message_count: int = Field(default=0, description="Total number of messages in this conversation")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "conv_789012",
                "title": "TCS Stock Analysis",
                "user_id": "user_123",
                "created_at": "2024-01-15T10:00:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
                "message_count": 5
            }
        }


class UserBase(BaseModel):
    """Base schema for a user"""
    email: str = Field(..., description="User email address")
    name: Optional[str] = Field(default=None, description="User's full name")


class UserCreate(UserBase):
    """Schema for creating a new user"""
    pass


class User(UserBase):
    """Complete user schema with all fields"""
    id: str = Field(..., description="Unique user ID")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="User creation timestamp")
    conversation_count: int = Field(default=0, description="Total number of conversations")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "user_123",
                "email": "john@example.com",
                "name": "John Doe",
                "created_at": "2024-01-01T00:00:00Z",
                "conversation_count": 5
            }
        }


class ChatHistoryResponse(BaseModel):
    """Response schema for chat history retrieval"""
    conversation: Conversation
    messages: List[Message]
    context_window: List[Message] = Field(default=[], description="Last N messages for AI context")


class ContextWindowConfig(BaseModel):
    """Configuration for context window retrieval"""
    max_messages: int = Field(default=10, description="Maximum number of recent messages to include")
    include_system_prompt: bool = Field(default=True, description="Whether to include system prompt in context")
