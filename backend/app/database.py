from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings


class Database:
    client: AsyncIOMotorClient = None
    db = None


db = Database()


async def connect_to_database():
    """Connect to MongoDB"""
    try:
        db.client = AsyncIOMotorClient(settings.mongodb_url, serverSelectionTimeoutMS=5000)
        db.db = db.client[settings.mongodb_db_name]
        
        # Verify connection
        await db.client.admin.command('ping')
        print("Connected to MongoDB")
    except Exception as e:
        print(f"Warning: Could not connect to MongoDB: {e}")
        print("Running without database connection - some features will be disabled")
        # Don't fail startup, allow running without DB for testing
        db.client = None
        db.db = None


async def close_database_connection():
    """Close MongoDB connection"""
    if db.client:
        db.client.close()
        print("Closed MongoDB connection")
