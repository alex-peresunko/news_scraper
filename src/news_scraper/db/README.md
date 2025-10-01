# Database Package

This package provides ChromaDB integration for storing and retrieving scraped news articles.

## Features

- **Persistent Storage**: Articles are stored in a persistent ChromaDB database
- **Automatic Initialization**: Database and collection are created automatically if they don't exist
- **Semantic Search**: Built-in vector search capabilities for finding similar articles
- **Batch Operations**: Support for storing multiple articles at once
- **Metadata Management**: Comprehensive metadata storage including authors, dates, keywords, and topics

## Installation

ChromaDB is included in the requirements:

```bash
pip install chromadb
```

## Usage

### Initialize the Database

```python
from news_scraper.db import ChromaDBClient

# Initialize with default settings (data/db folder)
db = ChromaDBClient()

# Or specify custom path and collection name
db = ChromaDBClient(
    db_path="./data/db",
    collection_name="news_articles"
)
```

### Store Articles

```python
from news_scraper.models.article import Article

# Store a single article
article = Article(
    url="https://example.com/article",
    title="Article Title",
    content="Article content...",
    source_domain="example.com",
    authors=["Author Name"],
    meta_keywords=["keyword1", "keyword2"]
)

success = db.store_article(article)

# Store multiple articles
articles = [article1, article2, article3]
result = db.store_articles(articles)
print(f"Stored: {result['success']}, Failed: {result['failed']}")
```

### Retrieve Articles

```python
# Get article by ID
article_data = db.get_article(article_id)

# Check if article exists
exists = db.article_exists(article_id)

# Get all articles
all_articles = db.get_all_articles(limit=100)

# Get count
count = db.count()
```

### Search Articles

```python
# Semantic search
results = db.search_articles(
    query="artificial intelligence news",
    n_results=10
)

# Search with filters
results = db.search_articles(
    query="technology",
    n_results=5,
    where={"source_domain": "example.com"}
)

for result in results:
    print(f"Title: {result['metadata']['title']}")
    print(f"Similarity: {result['distance']}")
```

### Delete Articles

```python
# Delete a single article
success = db.delete_article(article_id)

# Reset entire collection (delete all articles)
db.reset_collection()
```

## Database Location

By default, the database is stored in `./data/db/` relative to where the script is run. The directory is created automatically if it doesn't exist.

## Data Structure

Each article is stored with:
- **Document**: Combined title and content (used for embeddings)
- **Metadata**: All article fields including:
  - url
  - title
  - source_domain
  - word_count
  - scraped_at
  - authors (JSON)
  - meta_keywords (JSON)
  - topics (JSON)
  - publish_date (optional)
  - top_image (optional)
  - meta_description (optional)
  - summary (optional)

## Vector Embeddings

ChromaDB automatically generates vector embeddings for semantic search using the default embedding model (`all-MiniLM-L6-v2`). This allows you to:
- Find similar articles
- Search by semantic meaning (not just keywords)
- Group related content

## API Reference

### ChromaDBClient

#### `__init__(db_path: str = "./data/db", collection_name: str = "news_articles")`
Initialize the ChromaDB client.

#### `store_article(article: Article) -> bool`
Store a single article. Returns True if successful.

#### `store_articles(articles: List[Article]) -> Dict[str, int]`
Store multiple articles. Returns dict with success and failed counts.

#### `get_article(article_id: str) -> Optional[Dict[str, Any]]`
Retrieve an article by ID.

#### `article_exists(article_id: str) -> bool`
Check if an article exists in the database.

#### `search_articles(query: str, n_results: int = 10, where: Optional[Dict] = None) -> List[Dict]`
Perform semantic search for articles.

#### `get_all_articles(limit: Optional[int] = None) -> List[Dict]`
Retrieve all articles from the database.

#### `delete_article(article_id: str) -> bool`
Delete an article from the database.

#### `count() -> int`
Get the total number of articles.

#### `reset_collection() -> bool`
Delete all articles from the collection.

## Logging

The package uses `loguru` for logging. All database operations are logged with appropriate log levels:
- INFO: Successful operations
- WARNING: Reset operations
- ERROR: Failed operations
