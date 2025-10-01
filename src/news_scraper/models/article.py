"""Data models for articles and related entities."""

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, HttpUrl


class Article(BaseModel):
    """Article data model."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique article ID")
    url: HttpUrl = Field(description="Article URL")
    title: str = Field(description="Article title")
    content: str = Field(description="Article content")
    summary: Optional[str] = Field(default=None, description="Article summary")
    topics: Optional[List[str]] = Field(default_factory=list, description="Article topics")
    
    def __post_init__(self):
        """Post-initialization processing."""
        if self.word_count == 0:
            self.word_count = len(self.content.split())
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class ArticleAnalysis(BaseModel):
    """A model to hold the structured analysis of a news article."""
    title: str = Field(description="The title of the news article.")
    content: str = Field(description="The full text content of the news article, extracted as plain text.")
    summary: Optional[str] = Field(description="A concise summary of the key points of the article.")
    topics: Optional[List[str]] = Field(description="A list of the main topics discussed in the article.")