from fastapi import APIRouter, HTTPException, status
from typing import List, Optional

from app.models import (
    MessageCreate, Message,
    ConversationCreate, Conversation,
    UserCreate, User,
    ChatHistoryResponse, ContextWindowConfig
)
from app.repositories import UserRepository, ConversationRepository, MessageRepository
from app.database import db

router = APIRouter(prefix="/chat", tags=["Chat & Memory"])


def check_db_connection():
    """Check if database is connected"""
    if not db.db:
        print("ERROR: Database connection not available - db.db is None")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection not available. Please ensure MongoDB is running."
        )
    print(f"Database connection OK: {db.db.name}")


@router.post("/users", response_model=User, status_code=status.HTTP_201_CREATED)
async def create_user(user_data: UserCreate):
    """
    Create a new user.
    
    This is the entry point for user management. Each user can have multiple conversations.
    """
    try:
        check_db_connection()
        
        # Check if user with this email already exists
        existing_user = await UserRepository.get_user_by_id(user_data.email)  # Using email as temp ID check
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )
        
        user = await UserRepository.create_user(user_data)
        return user
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating user: {e}")
        import traceback
        traceback.print_exc()
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
    """
    Create a new conversation for a user.
    
    A conversation is a container for messages. Each conversation belongs to a user.
    """
    # Verify user exists
    user = await UserRepository.get_user_by_id(conversation_data.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    conversation = await ConversationRepository.create_conversation(conversation_data)
    return conversation


@router.get("/conversations/{conversation_id}", response_model=Conversation)
async def get_conversation(conversation_id: str):
    """Get conversation by ID"""
    conversation = await ConversationRepository.get_conversation_by_id(conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    return conversation


@router.get("/users/{user_id}/conversations", response_model=List[Conversation])
async def get_user_conversations(user_id: str, limit: int = 20, skip: int = 0):
    """
    Get all conversations for a user.
    
    Returns conversations sorted by last updated time (most recent first).
    """
    # Verify user exists
    user = await UserRepository.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    conversations = await ConversationRepository.get_user_conversations(user_id, limit, skip)
    return conversations


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(conversation_id: str):
    """
    Delete a conversation and all its messages.
    
    This is a cascade delete - all messages in the conversation will also be deleted.
    """
    success = await ConversationRepository.delete_conversation(conversation_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )


@router.post("/messages", response_model=Message, status_code=status.HTTP_201_CREATED)
async def create_message(message_data: MessageCreate):
    """
    Create a new message in a conversation.
    
    This is the primary endpoint for adding messages to the chat history.
    Each message is associated with a conversation and has a role (user/assistant/system).
    """
    # Verify conversation exists
    conversation = await ConversationRepository.get_conversation_by_id(message_data.conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    message = await MessageRepository.create_message(message_data)
    return message


@router.get("/conversations/{conversation_id}/messages", response_model=List[Message])
async def get_messages(conversation_id: str, limit: int = 100, skip: int = 0):
    """
    Get all messages in a conversation.
    
    Returns messages in chronological order (oldest first).
    """
    # Verify conversation exists
    conversation = await ConversationRepository.get_conversation_by_id(conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    messages = await MessageRepository.get_messages_by_conversation(conversation_id, limit, skip)
    return messages


@router.get("/conversations/{conversation_id}/history", response_model=ChatHistoryResponse)
async def get_chat_history(conversation_id: str, max_context_messages: int = 10):
    """
    Get complete chat history with context window for AI processing.
    
    This is the CRITICAL endpoint for the AI engine. It returns:
    - The conversation metadata
    - All messages in the conversation
    - A context window (last N messages) formatted for AI consumption
    
    The context window includes:
    - Recent messages (configurable via max_context_messages)
    - System prompt (if enabled) to guide AI behavior
    
    This enables the AI to maintain conversation memory and provide contextual responses.
    """
    # Verify conversation exists
    conversation = await ConversationRepository.get_conversation_by_id(conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
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
    """
    Get only the context window (last N messages) for AI processing.
    
    This is a lightweight version of the history endpoint, returning only
    the messages needed for AI context (not the full history).
    
    Use this when you need to minimize data transfer and only require
    the recent conversation context.
    """
    # Verify conversation exists
    conversation = await ConversationRepository.get_conversation_by_id(conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    config = ContextWindowConfig(
        max_messages=max_messages,
        include_system_prompt=include_system_prompt
    )
    
    context_window = await MessageRepository.get_context_window(conversation_id, config)
    return context_window
