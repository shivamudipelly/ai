"""
Chat Router with AI Agent Integration
Handles chat messages with AI-powered financial analysis.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional
from pydantic import BaseModel

from app.agent import ai_agent
from app.repositories import ConversationRepository, MessageRepository

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatMessageRequest(BaseModel):
    conversation_id: str
    message: str
    user_id: Optional[str] = "default_user"


class ChatResponse(BaseModel):
    success: bool
    response: str
    thought_process: Optional[str] = None
    tools_used: list = []
    tool_results: list = []
    iterations: int = 0
    error: Optional[str] = None


@router.post("/message", response_model=ChatResponse)
async def send_message(request: ChatMessageRequest):
    """
    Send a message to the AI agent and get a response.
    The AI will use ReAct pattern to reason and call tools if needed.
    """
    try:
        result = await ai_agent.process_message(
            user_message=request.message,
            conversation_id=request.conversation_id,
            user_id=request.user_id
        )
        
        return ChatResponse(**result)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")


@router.post("/stream")
async def stream_message(request: ChatMessageRequest):
    """
    Stream AI response token by token using Server-Sent Events.
    """
    from fastapi.responses import StreamingResponse
    import json
    
    async def generate():
        try:
            async for chunk in ai_agent.stream_response(
                user_message=request.message,
                conversation_id=request.conversation_id,
                user_id=request.user_id
            ):
                yield f"data: {json.dumps(chunk)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/conversation/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get full conversation history."""
    conv_repo = ConversationRepository()
    conversation = await conv_repo.get_by_id(conversation_id)
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    msg_repo = MessageRepository()
    messages = await msg_repo.get_by_conversation(conversation_id)
    
    return {
        "success": True,
        "conversation": conversation,
        "messages": messages
    }
