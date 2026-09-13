from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # MongoDB settings
    mongodb_url: str = "mongodb://mongodb:27017"
    mongodb_db_name: str = "financial_ai"
    
    # Ollama settings
    ollama_host: str = "http://ai-engine:11434"
    ollama_model: str = "qwen2.5:1.5b"  # Default model; can be overridden via OLLAMA_MODEL env var
    ollama_timeout: float = 120.0
    
    # Context settings
    max_context_messages: int = 10
    
    # API settings
    api_prefix: str = "/api"
    
    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
