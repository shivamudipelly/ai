from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MessageRole(str, Enum):
    """Role of the message sender."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class MessageBase(BaseModel):
    """Base schema for a message."""
    content: str = Field(..., description="The message content")
    role: MessageRole = Field(..., description="Role of the sender")


class MessageCreate(MessageBase):
    """Schema for creating a new message."""
    conversation_id: str = Field(..., description="ID of the conversation this message belongs to")


class Message(MessageBase):
    """Complete message schema with all fields."""
    id: str = Field(..., description="Unique message ID")
    conversation_id: str = Field(..., description="ID of the parent conversation")
    created_at: datetime = Field(default_factory=utc_now)
    metadata: Optional[dict] = Field(default=None, description="Additional message metadata")


class ConversationBase(BaseModel):
    """Base schema for a conversation."""
    title: str = Field(..., min_length=1, max_length=200, description="Conversation title")
    user_id: str = Field(..., min_length=1, max_length=200, description="ID of the user who owns this conversation")


class ConversationCreate(ConversationBase):
    """Schema for creating a new conversation."""
    pass


class Conversation(ConversationBase):
    """Complete conversation schema with all fields."""
    id: str = Field(..., description="Unique conversation ID")
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    message_count: int = Field(default=0, ge=0)


class UserBase(BaseModel):
    """Base schema for a user."""
    email: str = Field(..., min_length=3, max_length=320)
    name: Optional[str] = Field(default=None, max_length=200)


class UserCreate(UserBase):
    """Schema for creating a new user."""
    pass


class User(UserBase):
    """Complete user schema with all fields."""
    id: str = Field(..., description="Unique user ID")
    created_at: datetime = Field(default_factory=utc_now)
    conversation_count: int = Field(default=0, ge=0)


class ChatHistoryResponse(BaseModel):
    """Response schema for conversation history."""
    conversation: Conversation
    messages: List[Message]
    context_window: List[Message] = Field(default_factory=list)


class ContextWindowConfig(BaseModel):
    """Configuration for context-window retrieval."""
    max_messages: int = Field(default=10, ge=1, le=100)
    include_system_prompt: bool = Field(default=True)
