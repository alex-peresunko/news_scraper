"""Handles GenAI-driven summarization and topic identification for scraped articles."""

from openai import AsyncOpenAI
import json
import tiktoken
from typing import Tuple, List
from news_scraper.config.settings import settings_instance as settings
from news_scraper.utils.logging import logger

# Initialize the client at the module level for reuse
# This avoids configuration conflicts and is more efficient.
client = AsyncOpenAI(
    api_key=settings.openai_api_key,
    timeout=settings.request_timeout,
)


def get_model_context_limit(model: str) -> int:
    """Get the context limit for a given OpenAI model dynamically."""
    # Known model limits - updated as of October 2024
    model_limits = {
        # GPT-5 models
        "gpt-5-nano": 400_000,

        # GPT-3.5 models
        "gpt-3.5-turbo": 16_385,
        "gpt-3.5-turbo-16k": 16_385,
        "gpt-3.5-turbo-1106": 16_385,
        "gpt-3.5-turbo-0125": 16_385,

        # GPT-4 models
        "gpt-4": 8192,
        "gpt-4-0314": 8192,
        "gpt-4-0613": 8192,
        
        # GPT-4 Turbo models
        "gpt-4-turbo": 128_000,
        "gpt-4-turbo-preview": 128_000,
        "gpt-4-1106-preview": 128_000,
        "gpt-4-0125-preview": 128_000,
        "gpt-4-turbo-2024-04-09": 128_000,

        # GPT-4o models
        "gpt-4o": 128_000,
        "gpt-4o-2024-05-13": 128_000,
        "gpt-4o-2024-08-06": 128_000,
        "gpt-4o-mini": 128_000,
        "gpt-4o-mini-2024-07-18": 128_000,

        # Legacy models
        "text-davinci-003": 4097,
        "text-davinci-002": 4097,
        "code-davinci-002": 8001,
    }
    
    # Try exact match first
    if model in model_limits:
        return model_limits[model]
    
    # Try to infer from model name patterns
    model_lower = model.lower()
    
    if "gpt-4o" in model_lower:
        return 128000
    elif "gpt-4-turbo" in model_lower or "gpt-4-1106" in model_lower or "gpt-4-0125" in model_lower:
        return 128000
    elif "gpt-4" in model_lower:
        return 8192
    elif "gpt-3.5-turbo" in model_lower:
        return 16385
    elif "davinci" in model_lower:
        if "code" in model_lower:
            return 8001
        return 4097
    
    # Default fallback - conservative estimate
    logger.warning(f"Unknown model '{model}', using conservative token limit of 4096")
    return 4096


def count_tokens(text: str, model: str = "gpt-3.5-turbo") -> int:
    """Count the number of tokens in a text string for a given model."""
    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except KeyError:
        # Fallback for unknown models
        logger.warning(f"Unknown model '{model}' for token counting, using cl100k_base encoding")
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))


def chunk_content(content: str, max_tokens: int = 3000, model: str = "gpt-3.5-turbo") -> List[str]:
    """Split content into chunks that fit within token limits."""
    # Leave room for system message and response
    safe_token_limit = max_tokens - 1000
    
    # Split by paragraphs first (better semantic boundaries)
    paragraphs = content.split('\n\n')
    chunks = []
    current_chunk = ""
    
    for paragraph in paragraphs:
        test_chunk = current_chunk + ('\n\n' if current_chunk else '') + paragraph
        
        if count_tokens(test_chunk, model) <= safe_token_limit:
            current_chunk = test_chunk
        else:
            # If current chunk is not empty, save it
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = paragraph
            
            # If single paragraph is too large, split by sentences
            if count_tokens(paragraph, model) > safe_token_limit:
                sentences = paragraph.split('. ')
                temp_chunk = ""
                for sentence in sentences:
                    test_sentence = temp_chunk + ('. ' if temp_chunk else '') + sentence
                    if count_tokens(test_sentence, model) <= safe_token_limit:
                        temp_chunk = test_sentence
                    else:
                        if temp_chunk:
                            chunks.append(temp_chunk)
                        temp_chunk = sentence
                if temp_chunk:
                    current_chunk = temp_chunk
            else:
                current_chunk = paragraph
    
    # Add the last chunk
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks


async def analyze_article_chunk(
    request_id: str, chunk: str, chunk_index: int, total_chunks: int
) -> Tuple[str, List[str]]:
    """Analyze a single chunk of article content."""
    context_info = f" (Part {chunk_index + 1} of {total_chunks})" if total_chunks > 1 else ""
    
    prompt = f"""
    Please analyze the following article content{context_info} and provide:
    1. A concise summary of the key points in this section.
    2. A list of the main topics in this section.

    Return the output in the following JSON format:
    {{
        "summary": "Your summary here",
        "topics": ["Topic 1", "Topic 2", "Topic 3"]
    }}
    
    Article Content:
    "{chunk}"
    """

    try:
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that analyzes news articles. Focus on the most important information in each section.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=settings.openai_temperature,
        )

        message_content = response.choices[0].message.content
        if message_content is None:
            raise ValueError("No content returned from OpenAI response.")
        
        analysis = json.loads(message_content.strip())
        summary = analysis.get("summary", "No summary available.")
        topics = [topic.strip() for topic in analysis.get("topics", []) if topic.strip()]

        return summary, topics

    except Exception as e:
        logger.error(f"Error analyzing chunk {chunk_index} for request {request_id}: {e}")
        return f"Could not generate summary for part {chunk_index + 1}.", []


async def merge_chunk_analyses(summaries: List[str], topics_lists: List[List[str]]) -> Tuple[str, List[str]]:
    """Merge multiple chunk analyses into a final summary and topic list."""
    if not summaries:
        return "Could not generate summary.", []
    
    # Combine summaries
    combined_summary = "\n\n".join(f"Section {i+1}: {summary}" for i, summary in enumerate(summaries))
    
    # Create final summary from combined summaries
    final_prompt = f"""
    Based on the following section summaries from a news article, create a single coherent summary:
    
    {combined_summary}
    
    Provide a unified summary that captures the main points without redundancy.
    """
    
    try:
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that creates coherent summaries from multiple sections.",
                },
                {"role": "user", "content": final_prompt},
            ],
            temperature=settings.openai_temperature,
        )
        
        final_summary = response.choices[0].message.content or "Could not generate final summary."
        
    except Exception as e:
        logger.error(f"Error creating final summary: {e}")
        final_summary = " ".join(summaries)
    
    # Merge and deduplicate topics
    all_topics = []
    for topic_list in topics_lists:
        all_topics.extend(topic_list)
    
    # Remove duplicates while preserving order
    unique_topics = []
    seen = set()
    for topic in all_topics:
        topic_lower = topic.lower()
        if topic_lower not in seen:
            seen.add(topic_lower)
            unique_topics.append(topic)
    
    return final_summary.strip(), unique_topics


async def analyze_single_article(request_id: str, content: str) -> Tuple[str, List[str]]:
    """Analyze a single article that fits within token limits."""
    prompt = f"""
    Please analyze the following article content and provide:
    1. A concise summary of the key points.
    2. A list of the main topics in the article.

    Return the output in the following JSON format:
    {{
        "summary": "Your summary here",
        "topics": ["Topic 1", "Topic 2", "Topic 3"]
    }}
    Article Content:
    "{content}"
    """

    try:
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that analyzes news articles.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=settings.openai_temperature,
        )

        message_content = response.choices[0].message.content
        if message_content is None:
            raise ValueError("No content returned from OpenAI response.")
        analysis = message_content.strip()

        summary = json.loads(analysis)["summary"] or "No summary available."
        topics_part = json.loads(analysis)["topics"] or []
        topics = [topic.strip() for topic in topics_part if topic.strip()]

        return summary, topics

    except Exception as e:
        logger.error(f"An error occurred during GenAI analysis for request {request_id}: {e}")
        logger.debug(f"Request ID: {request_id}, Content length: {len(content)}")
        return "Could not generate summary.", []


async def analyze_article_content(
    request_id: str, content: str
) -> Tuple[str, List[str]]:
    """Generate an abstractive summary and key topics for a news article.

    Args:
        request_id: Identifier used for correlating logs and tracing failures.
        content: The article body to analyze.

    Returns:
        Tuple[str, List[str]]: The AI-generated summary and the list of topical labels.

    Raises:
        ValueError: If the model returns an empty response payload.
    """
    # Get model-specific token limits dynamically
    max_tokens = get_model_context_limit(settings.openai_model)
    total_tokens = count_tokens(content, settings.openai_model)
    
    logger.info(f"Request {request_id}: Content has {total_tokens} tokens, model limit is {max_tokens}")
    
    # If content fits in one request, use original logic
    if total_tokens <= max_tokens - 1000:  # Leave room for system message and response
        logger.debug(f"Request {request_id}: Content fits in single request")
        return await analyze_single_article(request_id, content)
    
    # Split into chunks and analyze separately
    logger.info(f"Request {request_id}: Splitting content into chunks due to token limit")
    chunks = chunk_content(content, max_tokens, settings.openai_model)
    
    logger.info(f"Request {request_id}: Created {len(chunks)} chunks for analysis")
    
    summaries = []
    topics_lists = []
    
    for i, chunk in enumerate(chunks):
        chunk_tokens = count_tokens(chunk, settings.openai_model)
        logger.debug(f"Request {request_id}: Analyzing chunk {i+1}/{len(chunks)} ({chunk_tokens} tokens)")
        
        summary, topics = await analyze_article_chunk(request_id, chunk, i, len(chunks))
        summaries.append(summary)
        topics_lists.append(topics)
    
    # Merge results
    logger.debug(f"Request {request_id}: Merging {len(summaries)} chunk analyses")
    final_summary, final_topics = await merge_chunk_analyses(summaries, topics_lists)
    
    logger.info(f"Request {request_id}: Completed chunked analysis - final summary: {len(final_summary)} chars, topics: {len(final_topics)}")
    return final_summary, final_topics
