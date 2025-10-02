"""Initialise LlamaIndex components backed by the persisted ChromaDB store."""

from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core import Settings

# Application imports
from news_scraper.config.settings import settings_instance as settings
from news_scraper.utils.logging import logger
from news_scraper.db import ChromaDBClient

# Configure the embedding model BEFORE creating any indices
# This ensures LlamaIndex uses OpenAI embeddings (1536 dimensions)
embed_model = OpenAIEmbedding(
    model=settings.embedding_model, api_key=settings.openai_api_key
)
Settings.embed_model = embed_model

# Get the db collection
db = ChromaDBClient()
chroma_collection = db.get_collection()
logger.debug(
    f"Successfully loaded ChromaDB collection '{chroma_collection.name}' with {chroma_collection.count()} articles."
)

# Create a LlamaIndex VectorStore object
# This acts as a wrapper around your ChromaDB collection.
vector_store = ChromaVectorStore(chroma_collection=chroma_collection)

# Create the LlamaIndex Storage Context
# This tells LlamaIndex where to "store" its knowledge, which in our case,
# is the ChromaDB vector store we just connected.
storage_context = StorageContext.from_defaults(vector_store=vector_store)

# Create the LlamaIndex Index
# This is the main object that LlamaIndex uses to know about your data.
# We are creating it *from* the vector store, so it doesn't try to create new embeddings.
index = VectorStoreIndex.from_vector_store(
    vector_store,
    storage_context=storage_context,
)
logger.debug("LlamaIndex has now successfully connected to the ChromaDB vector store.")

# Configure the LLM (this is separate from embeddings)
llm = OpenAI(
    model=settings.openai_model,
    temperature=settings.openai_temperature,
    api_key=settings.openai_api_key,
)
Settings.llm = llm

# Create the query engine. This is the primary tool for asking questions.
# It chains together the retrieval from ChromaDB and the answer synthesis by the LLM.
query_engine = index.as_query_engine(
    # You can configure how many top matching articles to retrieve.
    # This helps balance the thoroughness of the answer with speed and cost.
    similarity_top_k=settings.llama_similarity_top_k,
    response_mode=settings.llama_response_mode,  # "compact" or "tree_summarize"
)

logger.debug("Query engine is ready.")
