from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import json

from app.models import (
    MessageCreate, Message,
    ConversationCreate, Conversation,
    UserCreate, User,
    ChatHistoryResponse, ContextWindowConfig
)
from app.repositories import UserRepository, ConversationRepository, MessageRepository
from app.agent import ai_agent

router = APIRouter(prefix="/chat", tags=["Chat & AI Agent"])


class ChatMessageRequest(BaseModel):
    conversation_id: str
    message: str
    user_id: Optional[str] = "default_user"
    simple_mode: Optional[bool] = True


class ChatResponse(BaseModel):
    success: bool
    response: str
    thought_process: Optional[str] = None
    tools_used: list = []
    tool_results: list = []
    iterations: int = 0
    error: Optional[str] = None


@router.post("/users", response_model=User, status_code=status.HTTP_201_CREATED)
async def create_user(user_data: UserCreate):
    """Create a new user"""
    try:
        # Check if existing user by email
        existing_user = await UserRepository.get_user_by_id(user_data.email)
        if existing_user:
            return existing_user
        
        user = await UserRepository.create_user(user_data)
        return user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}"
        )


@router.get("/users/{user_id}", response_model=User)
async def get_user(user_id: str):
    """Get user by ID"""
    user = await UserRepository.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.post("/conversations", response_model=Conversation, status_code=status.HTTP_201_CREATED)
async def create_conversation(conversation_data: ConversationCreate):
    """Create a new conversation for a user"""
    user = await UserRepository.get_user_by_id(conversation_data.user_id)
    if not user:
        # Auto-create fallback user if user_id was provided
        user = await UserRepository.create_user(UserCreate(email=f"{conversation_data.user_id}@example.com", name="User"))
        conversation_data.user_id = user.id
    
    conversation = await ConversationRepository.create_conversation(conversation_data)
    return conversation


@router.get("/conversations/{conversation_id}")
@router.get("/conversation/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get conversation by ID along with its messages"""
    conversation = await ConversationRepository.get_conversation_by_id(conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    messages = await MessageRepository.get_messages_by_conversation(conversation_id)
    return {
        "success": True,
        "conversation": conversation,
        "messages": messages
    }


@router.get("/users/{user_id}/conversations", response_model=List[Conversation])
async def get_user_conversations(user_id: str, limit: int = 20, skip: int = 0):
    """Get all conversations for a user"""
    conversations = await ConversationRepository.get_user_conversations(user_id, limit, skip)
    return conversations


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
@router.delete("/conversation/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(conversation_id: str):
    """Delete a conversation and all its messages"""
    success = await ConversationRepository.delete_conversation(conversation_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )


@router.post("/messages", response_model=Message, status_code=status.HTTP_201_CREATED)
async def create_message(message_data: MessageCreate):
    """Add a raw message to chat history"""
    conversation = await ConversationRepository.get_conversation_by_id(message_data.conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    message = await MessageRepository.create_message(message_data)
    return message


@router.post("/message", response_model=ChatResponse)
async def send_ai_message(request: ChatMessageRequest):
    """Send a message to the AI agent and receive ReAct reasoning response"""
    try:
        result = await ai_agent.process_message(
            user_message=request.message,
            conversation_id=request.conversation_id,
            user_id=request.user_id or "default_user"
        )
        return ChatResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")


@router.post("/stream")
async def stream_ai_message(request: ChatMessageRequest):
    """Stream AI response token by token via Server-Sent Events (SSE)"""
    async def generate():
        try:
            async for chunk in ai_agent.stream_response(
                user_message=request.message,
                conversation_id=request.conversation_id,
                user_id=request.user_id or "default_user"
            ):
                yield f"data: {json.dumps(chunk)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e), 'done': True, 'error': str(e)})}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/conversations/{conversation_id}/messages", response_model=List[Message])
async def get_messages(conversation_id: str, limit: int = 100, skip: int = 0):
    """Get all messages in a conversation"""
    messages = await MessageRepository.get_messages_by_conversation(conversation_id, limit, skip)
    return messages


@router.get("/conversations/{conversation_id}/history", response_model=ChatHistoryResponse)
async def get_chat_history(conversation_id: str, max_context_messages: int = 10):
    """Get complete chat history with context window"""
    chat_history = await MessageRepository.get_chat_history(conversation_id, max_context_messages)
    if not chat_history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Failed to retrieve chat history"
        )
    return chat_history


@router.get("/conversations/{conversation_id}/context-window", response_model=List[Message])
async def get_context_window(
    conversation_id: str, 
    max_messages: int = 10,
    include_system_prompt: bool = True
):
    """Get AI context window (last N messages)"""
    config = ContextWindowConfig(
        max_messages=max_messages,
        include_system_prompt=include_system_prompt
    )
    context_window = await MessageRepository.get_context_window(conversation_id, config)
    return context_window
