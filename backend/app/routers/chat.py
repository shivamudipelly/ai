import json
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.agent import ai_agent
from app.models import (
    ChatHistoryResponse,
    Conversation,
    ConversationCreate,
    Message,
    MessageCreate,
    User,
    UserCreate,
)
from app.repositories import ConversationRepository, MessageRepository, UserRepository

router = APIRouter(prefix="/chat", tags=["Chat & AI Agent"])


class ChatMessageRequest(BaseModel):
    conversation_id: str = Field(..., min_length=1, max_length=100)
    message: str = Field(..., min_length=1, max_length=12000)
    user_id: Optional[str] = Field(default="default_user", min_length=1, max_length=200)
    simple_mode: bool = True


class ChatResponse(BaseModel):
    success: bool
    response: str
    tools_used: List[str] = Field(default_factory=list)
    tool_results: list = Field(default_factory=list)
    iterations: int = 0
    error: Optional[str] = None


async def _require_conversation(conversation_id: str):
    conversation = await ConversationRepository.get_conversation_by_id(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.post("/users", response_model=User, status_code=status.HTTP_201_CREATED)
async def create_user(user_data: UserCreate):
    try:
        existing_user = await UserRepository.get_user_by_id(user_data.email)
        if existing_user:
            return existing_user
        return await UserRepository.create_user(user_data)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to create user") from exc


@router.get("/users/{user_id}", response_model=User)
async def get_user(user_id: str):
    user = await UserRepository.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/conversations", response_model=Conversation, status_code=status.HTTP_201_CREATED)
async def create_conversation(conversation_data: ConversationCreate):
    user = await UserRepository.get_user_by_id(conversation_data.user_id)
    if not user:
        user = await UserRepository.create_user(
            UserCreate(email=f"{conversation_data.user_id}@example.com", name="User")
        )
        conversation_data.user_id = user.id
    return await ConversationRepository.create_conversation(conversation_data)


@router.get("/conversations/{conversation_id}")
@router.get("/conversation/{conversation_id}")
async def get_conversation(conversation_id: str):
    conversation = await _require_conversation(conversation_id)
    messages = await MessageRepository.get_messages_by_conversation(conversation_id)
    return {"success": True, "conversation": conversation, "messages": messages}


@router.get("/users/{user_id}/conversations", response_model=List[Conversation])
async def get_user_conversations(
    user_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    skip: int = Query(default=0, ge=0, le=100000),
):
    return await ConversationRepository.get_user_conversations(user_id, limit, skip)


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
@router.delete("/conversation/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(conversation_id: str):
    await _require_conversation(conversation_id)
    await ConversationRepository.delete_conversation(conversation_id)


@router.post("/messages", response_model=Message, status_code=status.HTTP_201_CREATED)
async def create_message(message_data: MessageCreate):
    await _require_conversation(message_data.conversation_id)
    return await MessageRepository.create_message(message_data)


@router.post("/message", response_model=ChatResponse)
async def send_ai_message(request: ChatMessageRequest):
    await _require_conversation(request.conversation_id)
    try:
        result = await ai_agent.process_message(
            user_message=request.message,
            conversation_id=request.conversation_id,
            user_id=request.user_id or "default_user",
        )
        return ChatResponse(**result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Error processing message") from exc


@router.post("/stream")
async def stream_ai_message(request: ChatMessageRequest):
    await _require_conversation(request.conversation_id)

    async def generate():
        try:
            async for chunk in ai_agent.stream_response(
                user_message=request.message,
                conversation_id=request.conversation_id,
                user_id=request.user_id or "default_user",
            ):
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
        except Exception:
            yield f"data: {json.dumps({'type': 'error', 'content': 'Unable to generate response.', 'done': True})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/conversations/{conversation_id}/messages", response_model=List[Message])
async def get_messages(
    conversation_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    skip: int = Query(default=0, ge=0, le=100000),
):
    await _require_conversation(conversation_id)
    return await MessageRepository.get_messages_by_conversation(conversation_id, limit, skip)


@router.get("/conversations/{conversation_id}/history", response_model=ChatHistoryResponse)
async def get_chat_history(
    conversation_id: str,
    max_context_messages: int = Query(default=10, ge=1, le=100),
):
    history = await MessageRepository.get_chat_history(conversation_id, max_context_messages)
    if not history:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return history
