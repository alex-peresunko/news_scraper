#! /usr/bin/env python3

"""Main entry point for the news scraper application."""

from news_scraper.utils.logging import logger
from news_scraper.config.settings import settings_instance as settings
from news_scraper.core.scraper import NewsScraper 

def main():
    """Main function to run the news scraper application."""
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    # Example urls to scrape
    urls = [
        "https://meta.ua/uk/news/weather/duzhe-holodnii-start-zhovtnya-didenko-poperedila-pro-doschi-ta-6c-v-ukrayini-899952/",
        "https://censor.net/biz/news/3577064/pryvatbank-organizuvav-navchalni-festyvali-z-fingramotnosti-dlya-diteyi",
        "https://www.epam.com/about"
        # Add more URLs as needed
    ]
    
    async def run_scraper():
        async with NewsScraper() as news_scraper:
            articles = await news_scraper.scrape_urls(urls)
            logger.info(f"Scraped {len(articles)} articles")
                
        for article in articles:
            logger.info(f"Title: {article.title}, URL: {article.url}")

    import asyncio
    asyncio.run(run_scraper())

if __name__ == "__main__":
    main()
