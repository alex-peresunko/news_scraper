"""Database package for storing and retrieving news articles."""

from news_scraper.db.chroma_client import ChromaDBClient

__all__ = ["ChromaDBClient"]