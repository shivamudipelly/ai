from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # MongoDB settings
    mongodb_url: str = "mongodb://mongodb:27017"
    mongodb_db_name: str = "financial_ai"
    
    # Ollama settings
    ollama_host: str = "http://ai-engine:11434"
    ollama_model: str = "qwen2.5:14b"  # Qwen 2.5 with reasoning capabilities
    
    # API settings
    api_prefix: str = "/api"
    
    class Config:
        env_file = ".env"


settings = Settings()
