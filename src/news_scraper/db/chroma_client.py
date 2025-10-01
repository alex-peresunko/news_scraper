"""ChromaDB client for storing and retrieving news articles."""

import json
import tiktoken
from pathlib import Path
from typing import List, Optional, Dict, Any

import chromadb
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection
from chromadb.config import Settings as ChromaSettings
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from loguru import logger

from news_scraper.models.article import Article
from news_scraper.config.settings import settings_instance as settings


class ChromaDBClient:
    """ChromaDB client for managing news articles."""
    
    # Maximum tokens for the embedding model (with safety margin)
    MAX_EMBEDDING_TOKENS = 8000  # Leave some buffer from the 8192 limit
    
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
        
        # Initialize tokenizer for text-embedding-ada-002 (cl100k_base encoding)
        try:
            self._tokenizer = tiktoken.encoding_for_model("text-embedding-ada-002")
        except Exception as e:
            logger.warning(f"Failed to load model-specific tokenizer: {e}. Using cl100k_base encoding.")
            self._tokenizer = tiktoken.get_encoding("cl100k_base")
        
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
            
            # Create OpenAI embedding function
            # This ensures ChromaDB uses OpenAI embeddings (1536 dimensions)
            embedding_function = OpenAIEmbeddingFunction(
                api_key=settings.openai_api_key,
                model_name=settings.embedding_model
            )
            
            # Get or create collection with OpenAI embeddings
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "News articles collection"},
                embedding_function=embedding_function # type: ignore
            )
            
            logger.info(f"ChromaDB initialized at {self.db_path}")
            logger.info(f"Collection '{self.collection_name}' ready with {self._collection.count()} documents")
            
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            raise
    
    def _count_tokens(self, text: str) -> int:
        """
        Count tokens in text using the OpenAI tokenizer.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Number of tokens
        """
        return len(self._tokenizer.encode(text))
    
    def _chunk_text(self, text: str, max_tokens: int) -> List[str]:
        """
        Split text into chunks that don't exceed max_tokens.
        Uses sentence-based chunking for better semantic coherence.
        
        Args:
            text: Text to chunk
            max_tokens: Maximum tokens per chunk
            
        Returns:
            List of text chunks
        """
        # Split by sentences (simple approach)
        sentences = text.replace('\n', ' ').split('. ')
        
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            # Add period back if it was removed
            if not sentence.endswith('.'):
                sentence += '.'
            
            sentence_tokens = self._count_tokens(sentence)
            
            # If a single sentence exceeds max_tokens, split it further
            if sentence_tokens > max_tokens:
                # If we have accumulated text, save it first
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                    current_chunk = []
                    current_tokens = 0
                
                # Split the long sentence by words
                words = sentence.split()
                word_chunk = []
                word_tokens = 0
                
                for word in words:
                    word_token_count = self._count_tokens(word + ' ')
                    if word_tokens + word_token_count > max_tokens:
                        if word_chunk:
                            chunks.append(' '.join(word_chunk))
                        word_chunk = [word]
                        word_tokens = word_token_count
                    else:
                        word_chunk.append(word)
                        word_tokens += word_token_count
                
                if word_chunk:
                    chunks.append(' '.join(word_chunk))
                continue
            
            # Check if adding this sentence would exceed the limit
            if current_tokens + sentence_tokens > max_tokens:
                # Save current chunk and start a new one
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                current_chunk = [sentence]
                current_tokens = sentence_tokens
            else:
                current_chunk.append(sentence)
                current_tokens += sentence_tokens
        
        # Add the last chunk
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks if chunks else [text[:max_tokens]]  # Fallback
    
    def _article_to_metadata(self, article: Article, chunk_index: int = 0, total_chunks: int = 1) -> Dict[str, Any]:
        """
        Convert article to metadata dictionary for ChromaDB.
        
        Args:
            article: Article object
            chunk_index: Index of this chunk (0-based)
            total_chunks: Total number of chunks for this article
            
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
            "chunk_index": chunk_index,
            "total_chunks": total_chunks,
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
        Automatically chunks large articles to fit within embedding model limits.
        
        Args:
            article: Article object to store
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Prepare full document content
            full_document = f"{article.title}\n\n{article.content}"
            
            # Check if document needs chunking
            token_count = self._count_tokens(full_document)
            
            if token_count <= self.MAX_EMBEDDING_TOKENS:
                # Document fits within limits - store as-is
                metadata = self._article_to_metadata(article, 0, 1)
                
                self._collection.add(
                    documents=[full_document],
                    metadatas=[metadata],
                    ids=[article.id]
                )
                
                logger.debug(f"Stored article: {article.title} (ID: {article.id}, tokens: {token_count})")
            else:
                # Document exceeds limits - chunk it
                logger.info(f"Article '{article.title}' has {token_count} tokens, chunking required")
                
                # Chunk the content (not the title, to avoid repetition)
                content_chunks = self._chunk_text(article.content, self.MAX_EMBEDDING_TOKENS - self._count_tokens(article.title) - 10)
                
                documents = []
                metadatas = []
                ids = []
                
                for i, chunk in enumerate(content_chunks):
                    # Combine title with each chunk
                    document = f"{article.title}\n\n{chunk}"
                    metadata = self._article_to_metadata(article, i, len(content_chunks))
                    chunk_id = f"{article.id}_chunk_{i}"
                    
                    documents.append(document)
                    metadatas.append(metadata)
                    ids.append(chunk_id)
                
                # Store all chunks
                self._collection.add(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )
                
                logger.info(f"Stored article '{article.title}' in {len(content_chunks)} chunks")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to store article {article.id}: {e}")
            return False
    
    def store_articles(self, articles: List[Article]) -> Dict[str, int]:
        """
        Store multiple articles in the database.
        Uses individual storage for each article to handle chunking properly.
        
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
        
        # Store articles individually to handle chunking
        for article in articles:
            if self.store_article(article):
                success_count += 1
            else:
                failed_count += 1
        
        logger.info(f"Successfully stored {success_count} articles, {failed_count} failed")
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

    def get_collection(self) -> Collection:
        """
        Get the underlying ChromaDB collection.
        
        Returns:
            ChromaDB Collection object
        """
        return self._collection