#! /usr/bin/env python3

"""Main entry point for the news scraper application."""

from news_scraper.utils.logging import logger
from news_scraper.config.settings import settings_instance as settings
from news_scraper.core.scraper import NewsScraper
from news_scraper.utils.arg_parser import arg_parser
from news_scraper.utils.helpers import is_valid_url

def main():
    """Main function to run the news scraper application."""
    args = arg_parser.parse_args()
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")

    try:
        with open(args.urls_file, "r", encoding="utf-8") as f:
            urls = []
            for line in f:
                if line.startswith("http") and is_valid_url(line.strip()):
                    urls.append(line.strip())
        if not urls:
            logger.warning(f"The file '{args.urls_file}' is empty. No URLs to scrape.")
            return
    except FileNotFoundError:
        logger.error(f"Error: The file '{args.urls_file}' was not found.")
        return
    except Exception as e:
        logger.error(f"An error occurred while reading the file: {e}")
        return
    
    async def run_scraper():
        async with NewsScraper() as news_scraper:
            articles = await news_scraper.scrape_urls(urls)
            logger.info(f"Scraped {len(articles)} articles")
                
        for article in articles:
            logger.info(f"Title: {article.title}, URL: {article.url}, Summary: {article.summary}, Topics: {article.topics}")

    import asyncio
    asyncio.run(run_scraper())

if __name__ == "__main__":
    main()
