from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.database import connect_to_database, close_database_connection
from app.routers import chat


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - startup and shutdown"""
    await connect_to_database()
    yield
    await close_database_connection()


app = FastAPI(
    title="Financial AI Platform",
    description="AI-powered financial analysis platform with real-time data",
    version="0.1.0",
    lifespan=lifespan
)

# Configure CORS for Docker network
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat.router, prefix=settings.api_prefix)


@app.get(f"{settings.api_prefix}/health")
async def health_check():
    """Health check endpoint to verify backend is running"""
    return {
        "status": "healthy",
        "service": "financial-ai-backend",
        "version": "0.1.0"
    }


@app.get(f"{settings.api_prefix}/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to Financial AI Platform API",
        "docs": f"{settings.api_prefix}/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
