#! /usr/bin/env python3

"""Main entry point for the news scraper application."""

import asyncio
from news_scraper.utils.logging import logger
from news_scraper.config.settings import settings_instance as settings
from news_scraper.core.genai import analyze_article_with_langchain
from news_scraper.utils.arg_parser import arg_parser
from news_scraper.utils.helpers import is_valid_url
from news_scraper.core.toolkits import ToolkitManager

async def main_async():
    """Asynchronous main function to run the news scraper application."""
    args = arg_parser.parse_args()
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")

    try:
        with open(args.urls_file, "r", encoding="utf-8") as f:
            urls = [line.strip() for line in f if line.strip() and is_valid_url(line.strip())]
        if not urls:
            logger.warning(f"The file '{args.urls_file}' is empty or contains no valid URLs.")
            return
    except FileNotFoundError:
        logger.error(f"Error: The file '{args.urls_file}' was not found.")
        return
    except Exception as e:
        logger.error(f"An error occurred while reading the file: {e}")
        return

    try:
        tasks = []
        for url in urls:
            tasks.append(analyze_article_with_langchain(url))
        
        results = await asyncio.gather(*tasks)
        
        for article in results:
            if article:
                logger.info(f"Title: {article.title}, URL: {article.url}, Summary: {article.summary}, Topics: {article.topics}")
            else:
                logger.error("Failed to analyze an article.")
    finally:
        # Ensure the browser is closed gracefully
        await ToolkitManager.close_browser()

def main():
    """Synchronous entry point."""
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
