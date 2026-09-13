from typing import List, Optional
from datetime import datetime
import uuid
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models import (
    Message, MessageCreate, MessageRole,
    Conversation, ConversationCreate,
    User, UserCreate,
    ChatHistoryResponse, ContextWindowConfig
)
from app.database import db


class UserRepository:
    """Repository for user-related database operations"""
    
    @staticmethod
    async def create_user(user_data: UserCreate) -> User:
        """Create a new user"""
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        user_dict = user_data.model_dump()
        user_dict["id"] = user_id
        user_dict["created_at"] = datetime.utcnow()
        user_dict["conversation_count"] = 0
        
        await db.db.users.insert_one(user_dict)
        return User(**user_dict)
    
    @staticmethod
    async def get_user_by_id(user_id: str) -> Optional[User]:
        """Get user by ID"""
        user_doc = await db.db.users.find_one({"id": user_id})
        if user_doc:
            return User(**user_doc)
        return None
    
    @staticmethod
    async def increment_conversation_count(user_id: str) -> bool:
        """Increment user's conversation count"""
        result = await db.db.users.update_one(
            {"id": user_id},
            {"$inc": {"conversation_count": 1}}
        )
        return result.modified_count > 0


class ConversationRepository:
    """Repository for conversation-related database operations"""
    
    @staticmethod
    async def create_conversation(conversation_data: ConversationCreate) -> Conversation:
        """Create a new conversation"""
        conv_id = f"conv_{uuid.uuid4().hex[:12]}"
        conv_dict = conversation_data.model_dump()
        conv_dict["id"] = conv_id
        conv_dict["created_at"] = datetime.utcnow()
        conv_dict["updated_at"] = datetime.utcnow()
        conv_dict["message_count"] = 0
        
        await db.db.conversations.insert_one(conv_dict)
        
        # Increment user's conversation count
        await UserRepository.increment_conversation_count(conversation_data.user_id)
        
        return Conversation(**conv_dict)
    
    @staticmethod
    async def get_conversation_by_id(conversation_id: str) -> Optional[Conversation]:
        """Get conversation by ID"""
        conv_doc = await db.db.conversations.find_one({"id": conversation_id})
        if conv_doc:
            return Conversation(**conv_doc)
        return None
    
    @staticmethod
    async def update_conversation_title(conversation_id: str, title: str) -> bool:
        """Update conversation title"""
        result = await db.db.conversations.update_one(
            {"id": conversation_id},
            {"$set": {"title": title, "updated_at": datetime.utcnow()}}
        )
        return result.modified_count > 0
    
    @staticmethod
    async def increment_message_count(conversation_id: str) -> bool:
        """Increment conversation's message count"""
        result = await db.db.conversations.update_one(
            {"id": conversation_id},
            {"$inc": {"message_count": 1}, "$set": {"updated_at": datetime.utcnow()}}
        )
        return result.modified_count > 0
    
    @staticmethod
    async def get_user_conversations(user_id: str, limit: int = 20, skip: int = 0) -> List[Conversation]:
        """Get all conversations for a user"""
        cursor = db.db.conversations.find(
            {"user_id": user_id}
        ).sort("updated_at", -1).skip(skip).limit(limit)
        
        conversations = []
        async for doc in cursor:
            conversations.append(Conversation(**doc))
        return conversations
    
    @staticmethod
    async def delete_conversation(conversation_id: str) -> bool:
        """Delete a conversation and all its messages"""
        # Delete all messages first
        await db.db.messages.delete_many({"conversation_id": conversation_id})
        
        # Delete the conversation
        result = await db.db.conversations.delete_one({"id": conversation_id})
        return result.deleted_count > 0


class MessageRepository:
    """Repository for message-related database operations"""
    
    @staticmethod
    async def create_message(message_data: MessageCreate) -> Message:
        """Create a new message"""
        message_id = f"msg_{uuid.uuid4().hex[:12]}"
        message_dict = message_data.model_dump()
        message_dict["id"] = message_id
        message_dict["created_at"] = datetime.utcnow()
        
        await db.db.messages.insert_one(message_dict)
        
        # Increment conversation's message count
        await ConversationRepository.increment_message_count(message_data.conversation_id)
        
        return Message(**message_dict)
    
    @staticmethod
    async def get_messages_by_conversation(
        conversation_id: str, 
        limit: int = 100, 
        skip: int = 0
    ) -> List[Message]:
        """Get all messages for a conversation"""
        cursor = db.db.messages.find(
            {"conversation_id": conversation_id}
        ).sort("created_at", 1).skip(skip).limit(limit)
        
        messages = []
        async for doc in cursor:
            messages.append(Message(**doc))
        return messages
    
    @staticmethod
    async def get_context_window(
        conversation_id: str, 
        config: ContextWindowConfig
    ) -> List[Message]:
        """
        Get the last N messages for AI context window.
        This is crucial for maintaining conversation memory.
        """
        # Get the most recent messages based on max_messages
        cursor = db.db.messages.find(
            {"conversation_id": conversation_id}
        ).sort("created_at", -1).limit(config.max_messages)
        
        messages = []
        async for doc in cursor:
            messages.append(Message(**doc))
        
        # Reverse to get chronological order (oldest to newest)
        messages.reverse()
        
        # Optionally add system prompt at the beginning
        if config.include_system_prompt:
            system_prompt = Message(
                id="system_prompt",
                conversation_id=conversation_id,
                content="""You are a professional Financial AI Analyst. You provide accurate, data-driven financial insights.
                
IMPORTANT RULES:
1. NEVER guess or hallucinate numbers - always use provided data
2. Clearly distinguish between facts and opinions
3. Cite sources when available
4. Warn about risks and uncertainties
5. Do not provide guaranteed predictions
6. Structure responses clearly with headings and bullet points""",
                role=MessageRole.SYSTEM,
                created_at=datetime.utcnow(),
                metadata={"type": "system_prompt"}
            )
            messages.insert(0, system_prompt)
        
        return messages
    
    @staticmethod
    async def get_chat_history(conversation_id: str, max_context_messages: int = 10) -> Optional[ChatHistoryResponse]:
        """
        Get complete chat history for a conversation including context window.
        This is the main method used when the AI needs to understand the conversation context.
        """
        conversation = await ConversationRepository.get_conversation_by_id(conversation_id)
        if not conversation:
            return None
        
        all_messages = await MessageRepository.get_messages_by_conversation(conversation_id)
        
        context_config = ContextWindowConfig(max_messages=max_context_messages)
        context_window = await MessageRepository.get_context_window(conversation_id, context_config)
        
        return ChatHistoryResponse(
            conversation=conversation,
            messages=all_messages,
            context_window=context_window
        )
    
    @staticmethod
    async def update_message_metadata(message_id: str, metadata: dict) -> bool:
        """Update message metadata (e.g., for storing tool call results)"""
        result = await db.db.messages.update_one(
            {"id": message_id},
            {"$set": {"metadata": metadata}}
        )
        return result.modified_count > 0
