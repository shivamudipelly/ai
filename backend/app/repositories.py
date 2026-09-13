from typing import List, Optional
from datetime import datetime
import uuid

from app.models import (
    Message, MessageCreate, MessageRole,
    Conversation, ConversationCreate,
    User, UserCreate,
    ChatHistoryResponse, ContextWindowConfig
)
from app.database import db


def _clean_doc(doc: Optional[dict]) -> Optional[dict]:
    """Helper to remove MongoDB internal _id before Pydantic parsing"""
    if not doc:
        return None
    d = dict(doc)
    d.pop("_id", None)
    return d


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
        
        if db.db is not None:
            await db.db.users.insert_one(dict(user_dict))
        else:
            db.in_memory["users"][user_id] = dict(user_dict)
            
        return User(**user_dict)
    
    @staticmethod
    async def get_user_by_id(user_id: str) -> Optional[User]:
        """Get user by ID or email"""
        if db.db is not None:
            user_doc = await db.db.users.find_one({"$or": [{"id": user_id}, {"email": user_id}]})
            if user_doc:
                return User(**_clean_doc(user_doc))
            return None
        else:
            for u in db.in_memory["users"].values():
                if u.get("id") == user_id or u.get("email") == user_id:
                    return User(**u)
            return None
    
    @staticmethod
    async def increment_conversation_count(user_id: str) -> bool:
        """Increment user's conversation count"""
        if db.db is not None:
            result = await db.db.users.update_one(
                {"id": user_id},
                {"$inc": {"conversation_count": 1}}
            )
            return result.modified_count > 0
        else:
            user = db.in_memory["users"].get(user_id)
            if user:
                user["conversation_count"] = user.get("conversation_count", 0) + 1
                return True
            return False


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
        
        if db.db is not None:
            await db.db.conversations.insert_one(dict(conv_dict))
        else:
            db.in_memory["conversations"][conv_id] = dict(conv_dict)
        
        # Increment user's conversation count
        await UserRepository.increment_conversation_count(conversation_data.user_id)
        
        return Conversation(**conv_dict)
    
    @staticmethod
    async def get_conversation_by_id(conversation_id: str) -> Optional[Conversation]:
        """Get conversation by ID"""
        if db.db is not None:
            conv_doc = await db.db.conversations.find_one({"id": conversation_id})
            if conv_doc:
                return Conversation(**_clean_doc(conv_doc))
            return None
        else:
            conv = db.in_memory["conversations"].get(conversation_id)
            if conv:
                return Conversation(**conv)
            return None

    @staticmethod
    async def get_by_id(conversation_id: str) -> Optional[Conversation]:
        """Alias for get_conversation_by_id for backward compatibility"""
        return await ConversationRepository.get_conversation_by_id(conversation_id)
    
    @staticmethod
    async def update_conversation_title(conversation_id: str, title: str) -> bool:
        """Update conversation title"""
        if db.db is not None:
            result = await db.db.conversations.update_one(
                {"id": conversation_id},
                {"$set": {"title": title, "updated_at": datetime.utcnow()}}
            )
            return result.modified_count > 0
        else:
            conv = db.in_memory["conversations"].get(conversation_id)
            if conv:
                conv["title"] = title
                conv["updated_at"] = datetime.utcnow()
                return True
            return False
    
    @staticmethod
    async def increment_message_count(conversation_id: str) -> bool:
        """Increment conversation's message count"""
        if db.db is not None:
            result = await db.db.conversations.update_one(
                {"id": conversation_id},
                {"$inc": {"message_count": 1}, "$set": {"updated_at": datetime.utcnow()}}
            )
            return result.modified_count > 0
        else:
            conv = db.in_memory["conversations"].get(conversation_id)
            if conv:
                conv["message_count"] = conv.get("message_count", 0) + 1
                conv["updated_at"] = datetime.utcnow()
                return True
            return False
    
    @staticmethod
    async def get_user_conversations(user_id: str, limit: int = 20, skip: int = 0) -> List[Conversation]:
        """Get all conversations for a user"""
        if db.db is not None:
            cursor = db.db.conversations.find(
                {"user_id": user_id}
            ).sort("updated_at", -1).skip(skip).limit(limit)
            
            conversations = []
            async for doc in cursor:
                conversations.append(Conversation(**_clean_doc(doc)))
            return conversations
        else:
            user_convs = [
                c for c in db.in_memory["conversations"].values()
                if c.get("user_id") == user_id
            ]
            user_convs.sort(key=lambda x: x.get("updated_at", datetime.min), reverse=True)
            sliced = user_convs[skip:skip+limit]
            return [Conversation(**c) for c in sliced]
    
    @staticmethod
    async def delete_conversation(conversation_id: str) -> bool:
        """Delete a conversation and all its messages"""
        if db.db is not None:
            await db.db.messages.delete_many({"conversation_id": conversation_id})
            result = await db.db.conversations.delete_one({"id": conversation_id})
            return result.deleted_count > 0
        else:
            db.in_memory["messages"] = [
                m for m in db.in_memory["messages"]
                if m.get("conversation_id") != conversation_id
            ]
            if conversation_id in db.in_memory["conversations"]:
                del db.in_memory["conversations"][conversation_id]
                return True
            return False


class MessageRepository:
    """Repository for message-related database operations"""
    
    @staticmethod
    async def create_message(message_data: MessageCreate) -> Message:
        """Create a new message"""
        message_id = f"msg_{uuid.uuid4().hex[:12]}"
        message_dict = message_data.model_dump()
        message_dict["id"] = message_id
        message_dict["created_at"] = datetime.utcnow()
        
        if db.db is not None:
            await db.db.messages.insert_one(dict(message_dict))
        else:
            db.in_memory["messages"].append(dict(message_dict))
        
        # Increment conversation's message count
        await ConversationRepository.increment_message_count(message_data.conversation_id)
        
        return Message(**message_dict)

    @staticmethod
    async def add_message(
        conversation_id: str, 
        user_id: str, 
        role: str, 
        content: str, 
        metadata: Optional[dict] = None
    ) -> Message:
        """Convenience method to add a message to a conversation"""
        role_enum = MessageRole(role) if isinstance(role, str) else role
        msg_create = MessageCreate(
            conversation_id=conversation_id,
            role=role_enum,
            content=content
        )
        message = await MessageRepository.create_message(msg_create)
        if metadata:
            await MessageRepository.update_message_metadata(message.id, metadata)
            message.metadata = metadata
        return message
    
    @staticmethod
    async def get_messages_by_conversation(
        conversation_id: str, 
        limit: int = 100, 
        skip: int = 0
    ) -> List[Message]:
        """Get all messages for a conversation"""
        if db.db is not None:
            cursor = db.db.messages.find(
                {"conversation_id": conversation_id}
            ).sort("created_at", 1).skip(skip).limit(limit)
            
            messages = []
            async for doc in cursor:
                messages.append(Message(**_clean_doc(doc)))
            return messages
        else:
            conv_msgs = [
                m for m in db.in_memory["messages"]
                if m.get("conversation_id") == conversation_id
            ]
            conv_msgs.sort(key=lambda x: x.get("created_at", datetime.min))
            sliced = conv_msgs[skip:skip+limit]
            return [Message(**m) for m in sliced]

    @staticmethod
    async def get_by_conversation(conversation_id: str, limit: int = 100, skip: int = 0) -> List[Message]:
        """Alias for get_messages_by_conversation for backward compatibility"""
        return await MessageRepository.get_messages_by_conversation(conversation_id, limit, skip)
    
    @staticmethod
    async def get_context_window(
        conversation_id: str, 
        config: ContextWindowConfig
    ) -> List[Message]:
        """
        Get the last N messages for AI context window.
        This is crucial for maintaining conversation memory.
        """
        if db.db is not None:
            cursor = db.db.messages.find(
                {"conversation_id": conversation_id}
            ).sort("created_at", -1).limit(config.max_messages)
            
            messages = []
            async for doc in cursor:
                messages.append(Message(**_clean_doc(doc)))
            messages.reverse()
        else:
            conv_msgs = [
                m for m in db.in_memory["messages"]
                if m.get("conversation_id") == conversation_id
            ]
            conv_msgs.sort(key=lambda x: x.get("created_at", datetime.min), reverse=True)
            recent = conv_msgs[:config.max_messages]
            recent.reverse()
            messages = [Message(**m) for m in recent]
        
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
        if db.db is not None:
            result = await db.db.messages.update_one(
                {"id": message_id},
                {"$set": {"metadata": metadata}}
            )
            return result.modified_count > 0
        else:
            for m in db.in_memory["messages"]:
                if m.get("id") == message_id:
                    m["metadata"] = metadata
                    return True
            return False
