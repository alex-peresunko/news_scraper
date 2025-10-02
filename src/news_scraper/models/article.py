"""Data models for articles and related entities."""

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, HttpUrl


class Article(BaseModel):
    """Structured representation of a scraped news article and model metadata."""

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), description="Unique article ID"
    )
    url: HttpUrl = Field(description="Article URL")
    title: str = Field(description="Article title")
    content: str = Field(description="Article content")
    authors: List[str] = Field(default_factory=list, description="Article authors")
    publish_date: Optional[datetime] = Field(
        default=None, description="Publication date"
    )
    scraped_at: datetime = Field(
        default_factory=datetime.utcnow, description="When article was scraped"
    )
    top_image: Optional[str] = Field(default=None, description="Top image URL")
    meta_description: str = Field(default="", description="Meta description")
    meta_keywords: List[str] = Field(default_factory=list, description="Meta keywords")
    source_domain: str = Field(description="Source domain")
    word_count: int = Field(default=0, description="Word count")
    summary: Optional[str] = Field(default=None, description="Article summary")
    topics: Optional[List[str]] = Field(
        default_factory=list, description="Article topics"
    )

    def __post_init__(self):
        """Populate derived fields once the model is instantiated.

        Calculates ``word_count`` lazily when the caller does not provide it.
        """
        if self.word_count == 0:
            self.word_count = len(self.content.split())

    class Config:
        """Pydantic configuration."""

        json_encoders = {datetime: lambda v: v.isoformat()}
