from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings


class Database:
    client: AsyncIOMotorClient = None
    db = None


db = Database()


async def connect_to_database():
    """Connect to MongoDB"""
    db.client = AsyncIOMotorClient(settings.mongodb_url)
    db.db = db.client[settings.mongodb_db_name]
    
    # Verify connection
    await db.client.admin.command('ping')
    print("Connected to MongoDB")


async def close_database_connection():
    """Close MongoDB connection"""
    if db.client:
        db.client.close()
        print("Closed MongoDB connection")
