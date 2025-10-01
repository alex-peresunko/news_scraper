"""ChromaDB client for storing and retrieving news articles."""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

import chromadb
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection
from chromadb.config import Settings as ChromaSettings
from loguru import logger

from news_scraper.models.article import Article


class ChromaDBClient:
    """ChromaDB client for managing news articles."""
    
    def __init__(self, db_path: str = "./data/db", collection_name: str = "news_articles"):
        """
        Initialize ChromaDB client.
        
        Args:
            db_path: Path to the database directory
            collection_name: Name of the collection to use
        """
        self.db_path = Path(db_path)
        self.collection_name = collection_name
        self._client: ClientAPI
        self._collection: Collection
        
        # Ensure database directory exists
        self.db_path.mkdir(parents=True, exist_ok=True)
        
        self._initialize_db()
    
    def _initialize_db(self) -> None:
        """Initialize the ChromaDB client and collection."""
        try:
            # Initialize ChromaDB client with persistent storage
            self._client = chromadb.PersistentClient(
                path=str(self.db_path),
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Get or create collection
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "News articles collection"}
            )
            
            logger.info(f"ChromaDB initialized at {self.db_path}")
            logger.info(f"Collection '{self.collection_name}' ready with {self._collection.count()} documents")
            
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            raise
    
    def _article_to_metadata(self, article: Article) -> Dict[str, Any]:
        """
        Convert article to metadata dictionary for ChromaDB.
        
        Args:
            article: Article object
            
        Returns:
            Metadata dictionary
        """
        metadata = {
            "url": str(article.url),
            "title": article.title,
            "source_domain": article.source_domain,
            "word_count": article.word_count,
            "scraped_at": article.scraped_at.isoformat(),
            "authors": json.dumps(article.authors),
            "meta_keywords": json.dumps(article.meta_keywords),
            "topics": json.dumps(article.topics) if article.topics else "[]",
        }
        
        # Add optional fields if they exist
        if article.publish_date:
            metadata["publish_date"] = article.publish_date.isoformat()
        if article.top_image:
            metadata["top_image"] = article.top_image
        if article.meta_description:
            metadata["meta_description"] = article.meta_description
        if article.summary:
            metadata["summary"] = article.summary
        
        return metadata
    
    def store_article(self, article: Article) -> bool:
        """
        Store a single article in the database.
        
        Args:
            article: Article object to store
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Prepare document content (combining title and content for embedding)
            document = f"{article.title}\n\n{article.content}"
            
            # Prepare metadata
            metadata = self._article_to_metadata(article)
            
            # Add to collection
            self._collection.add(
                documents=[document],
                metadatas=[metadata],
                ids=[article.id]
            )
            
            logger.debug(f"Stored article: {article.title} (ID: {article.id})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store article {article.id}: {e}")
            return False
    
    def store_articles(self, articles: List[Article]) -> Dict[str, int]:
        """
        Store multiple articles in the database.
        
        Args:
            articles: List of Article objects to store
            
        Returns:
            Dictionary with success and failure counts
        """
        if not articles:
            logger.warning("No articles to store")
            return {"success": 0, "failed": 0}
        
        success_count = 0
        failed_count = 0
        
        try:
            documents = []
            metadatas = []
            ids = []
            
            for article in articles:
                try:
                    # Prepare document content
                    document = f"{article.title}\n\n{article.content}"
                    metadata = self._article_to_metadata(article)
                    
                    documents.append(document)
                    metadatas.append(metadata)
                    ids.append(article.id)
                    
                except Exception as e:
                    logger.error(f"Failed to prepare article {article.id}: {e}")
                    failed_count += 1
            
            # Batch add to collection
            if documents:
                self._collection.add(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )
                success_count = len(documents)
                logger.info(f"Successfully stored {success_count} articles")
            
        except Exception as e:
            logger.error(f"Failed to store articles batch: {e}")
            failed_count += len(articles) - success_count
        
        return {"success": success_count, "failed": failed_count}
    
    def get_article(self, article_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve an article by ID.
        
        Args:
            article_id: Article ID
            
        Returns:
            Article data as dictionary or None if not found
        """
        try:
            result = self._collection.get(
                ids=[article_id],
                include=["documents", "metadatas"]
            )
            
            if result["ids"]:
                return {
                    "id": result["ids"][0],
                    "document": result["documents"][0], # type: ignore
                    "metadata": result["metadatas"][0] # type: ignore
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to retrieve article {article_id}: {e}")
            return None
    
    def article_exists(self, article_id: str) -> bool:
        """
        Check if an article exists in the database.
        
        Args:
            article_id: Article ID
            
        Returns:
            True if article exists, False otherwise
        """
        try:
            result = self._collection.get(ids=[article_id])
            return len(result["ids"]) > 0
        except Exception as e:
            logger.error(f"Failed to check article existence {article_id}: {e}")
            return False
    
    def search_articles(
        self,
        query: str,
        n_results: int = 10,
        where: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for articles using semantic search.
        
        Args:
            query: Search query
            n_results: Number of results to return
            where: Optional filter conditions
            
        Returns:
            List of matching articles
        """
        try:
            results = self._collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where,
                include=["documents", "metadatas", "distances"]
            )
            
            articles = []
            for i in range(len(results["ids"][0])):
                articles.append({
                    "id": results["ids"][0][i],
                    "document": results["documents"][0][i], # type: ignore
                    "metadata": results["metadatas"][0][i], # type: ignore
                    "distance": results["distances"][0][i] # type: ignore
                })
            
            return articles
            
        except Exception as e:
            logger.error(f"Failed to search articles: {e}")
            return []
    
    def get_all_articles(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Retrieve all articles from the database.
        
        Args:
            limit: Optional limit on number of articles to retrieve
            
        Returns:
            List of all articles
        """
        try:
            result = self._collection.get(
                include=["documents", "metadatas"],
                limit=limit
            )
            
            articles = []
            for i in range(len(result["ids"])):
                articles.append({
                    "id": result["ids"][i],
                    "document": result["documents"][i], # type: ignore
                    "metadata": result["metadatas"][i]  # type: ignore
                })
            
            return articles
            
        except Exception as e:
            logger.error(f"Failed to retrieve all articles: {e}")
            return []
    
    def delete_article(self, article_id: str) -> bool:
        """
        Delete an article from the database.
        
        Args:
            article_id: Article ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self._collection.delete(ids=[article_id])
            logger.info(f"Deleted article: {article_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete article {article_id}: {e}")
            return False
    
    def count(self) -> int:
        """
        Get the total number of articles in the database.
        
        Returns:
            Number of articles
        """
        try:
            return self._collection.count()
        except Exception as e:
            logger.error(f"Failed to count articles: {e}")
            return 0
    
    def reset_collection(self) -> bool:
        """
        Delete all articles from the collection.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self._client.delete_collection(name=self.collection_name)
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "News articles collection"}
            )
            logger.warning(f"Collection '{self.collection_name}' has been reset")
            return True
            
        except Exception as e:
            logger.error(f"Failed to reset collection: {e}")
            return False
