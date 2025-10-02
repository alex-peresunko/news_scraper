"""Handles GenAI-driven summarization and topic identification for scraped articles."""

from openai import AsyncOpenAI
import json
from typing import Tuple, List
from news_scraper.config.settings import settings_instance as settings
from news_scraper.utils.logging import logger

# Initialize the client at the module level for reuse
# This avoids configuration conflicts and is more efficient.
client = AsyncOpenAI(
    api_key=settings.openai_api_key,
    timeout=settings.request_timeout,
)


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
        # Call the 'create' method on the 'chat.completions' attribute
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

        # Parse the response to extract summary and topics
        summary = json.loads(analysis)["summary"] or "No summary available."
        topics_part = json.loads(analysis)["topics"] or []
        topics = [topic.strip() for topic in topics_part if topic.strip()]

        return summary, topics

    except Exception as e:
        # In a real-world scenario, you'd want more robust error handling
        logger.error(f"An error occurred during GenAI analysis: {e}")
        logger.debug(f"Request ID: {request_id}, Content: {content}")
        return "Could not generate summary.", []
