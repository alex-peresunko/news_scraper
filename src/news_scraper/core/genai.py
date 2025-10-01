"""Handles GenAI-driven analysis of scraped articles using LangChain and Playwright."""

import asyncio
from typing import Optional, List
from pydantic import HttpUrl, BaseModel, Field, SecretStr

# LangChain Imports
from langchain.agents import AgentExecutor
# We will manually build the agent, so we need these components
from langchain.agents.format_scratchpad.openai_tools import format_to_openai_tool_messages
from langchain.agents.output_parsers.openai_tools import OpenAIToolsAgentOutputParser
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool

# Your Application Imports
from news_scraper.config.settings import settings_instance as settings
from news_scraper.models.article import Article, ArticleAnalysis
from news_scraper.core.toolkits import ToolkitManager
from news_scraper.utils.logging import logger


@tool
def record_article_analysis(analysis: ArticleAnalysis) -> ArticleAnalysis:
    """Use this tool to record the structured analysis of the news article."""
    return analysis


async def analyze_article_with_langchain(url: str) -> Optional[Article]:
    """
    Analyzes a news article from a URL to generate a structured output
    using a LangChain agent.
    """
    llm = ChatOpenAI(
        model=settings.openai_model,
        temperature=settings.openai_temperature,
        api_key=SecretStr(settings.openai_api_key)
    )

    toolkit = await ToolkitManager.get_toolkit()
    browsing_tools = toolkit.get_tools()
    tools = browsing_tools + [record_article_analysis]
    
    # --- THE FIX: Manually construct the agent using LCEL ---

    # 1. Bind the tool to the LLM to force it to be called
    llm_with_tools = llm.bind_tools([record_article_analysis], tool_choice="record_article_analysis")

    # 2. Create the prompt. This remains the same.
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful assistant that analyzes news articles. Your goal is to extract the title, content, summary, and topics from the article at the given URL. If you cannot retrieve the full content after trying, you MUST still call the 'record_article_analysis' tool, but populate the 'content' field with a message like 'Full content could not be retrieved.'"),
        ("user", "Please analyze the news article at the following URL: {input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])

    # 3. Manually create the agent runnable chain. This replaces 'create_openai_tools_agent'.
    agent = (
        {
            "input": lambda x: x["input"],
            "agent_scratchpad": lambda x: format_to_openai_tool_messages(
                x["intermediate_steps"]
            ),
        }
        | prompt
        | llm_with_tools
        | OpenAIToolsAgentOutputParser()
    )
    
    # This line is now fully type-safe.
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=settings.debug, max_iterations=5)

    try:
        response = await agent_executor.ainvoke({"input": url})
        agent_output = response.get("output", {})

        if agent_output and isinstance(agent_output, ArticleAnalysis):
            analysis_dict = agent_output.model_dump()
            scraped_article = Article(**analysis_dict, url=HttpUrl(url))
            logger.success(f"Successfully scraped and analyzed: {url}")

            if settings.rate_limit_delay > 0:
                await asyncio.sleep(settings.rate_limit_delay)
            
            return scraped_article
        else:
            logger.warning(f"Agent did not return a structured dictionary for URL: {url}. Output was: {response.get('output')}")
            return None

    except Exception as e:
        logger.error(f"An error occurred during LangChain analysis for URL {url}: {e}")
        return None