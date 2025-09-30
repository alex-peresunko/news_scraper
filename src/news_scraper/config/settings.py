"""Application settings and configuration management."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Application settings
    app_name: str = Field(default="News Scraper", description="Application name")
    app_version: str = Field(default="0.0.1", description="Application version")
    debug: bool = Field(default=False, description="Debug mode")
    
    # OpenAI Configuration
    openai_api_key: str = Field(description="OpenAI API key")
    openai_model: str = Field(default="gpt-3.5-turbo", description="OpenAI model to use")
    openai_temperature: float = Field(default=0.1, description="OpenAI temperature")
    openai_max_tokens: int = Field(default=2000, description="OpenAI max tokens")
    
    # Vector Database Configuration
    vector_db_path: str = Field(default="./data/chroma_db", description="Vector database path")
    vector_db_collection_name: str = Field(default="news_articles", description="Collection name")
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2", 
        description="Embedding model"
    )
    
    # Scraping Configuration
    user_agent: str = Field(
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        description="User agent for web scraping"
    )
    request_timeout: int = Field(default=30, description="Request timeout in seconds")
    max_concurrent_requests: int = Field(default=5, description="Max concurrent requests")
    rate_limit_delay: float = Field(default=1.0, description="Rate limit delay in seconds")
    
    # Logging Configuration
    log_level: str = Field(default="INFO", description="Logging level")
    log_file: str = Field(default="./logs/news_scraper.log", description="Log file path")
    log_max_size: str = Field(default="10MB", description="Max log file size")
    log_backup_count: int = Field(default=5, description="Log backup count")
    log_format: str = Field(
        default="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        description="Log format"
    )
    
    # Database Configuration
    database_url: str = Field(default="sqlite:///./data/news_scraper.db", description="Database URL")
    
    @property
    def project_root(self) -> Path:
        """Get project root directory."""
        return Path(__file__).parent.parent.parent.parent
    
    @property
    def data_dir(self) -> Path:
        """Get data directory."""
        data_path = Path(self.vector_db_path).parent
        if not data_path.is_absolute():
            data_path = self.project_root / data_path
        return data_path
    
    @property
    def logs_dir(self) -> Path:
        """Get logs directory."""
        log_path = Path(self.log_file).parent
        if not log_path.is_absolute():
            log_path = self.project_root / log_path
        return log_path
    
    def create_directories(self) -> None:
        """Create necessary directories."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Create .gitkeep files for empty directories
        (self.data_dir / ".gitkeep").touch(exist_ok=True)
        (self.logs_dir / ".gitkeep").touch(exist_ok=True)


# Global settings instance
settings_instance = Settings() # pyright: ignore[reportCallIssue]

# Ensure directories exist
settings_instance.create_directories()