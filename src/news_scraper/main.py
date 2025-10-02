"""Main entry point for the news scraper application."""

from news_scraper.utils.arg_parser import arg_parser
from news_scraper.utils.logging import logger
from news_scraper.config.settings import settings_instance as settings
from news_scraper.core.scraper import NewsScraper
from news_scraper.db import ChromaDBClient
from news_scraper.utils.helpers import is_valid_url
from news_scraper.core.llamaindex import query_engine


def main():
    """Coordinate command-line workflows for scraping and querying news content.

    Returns:
        None: The function orchestrates side effects only.
    """
    args = arg_parser.parse_args()
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")

    if args.urls_file is not None:
        logger.info("Scraping urls mode activated.")

        try:
            with open(args.urls_file, "r", encoding="utf-8") as f:
                urls = []
                for line in f:
                    # Accept only well-formed HTTP(S) URLs from the file, skipping comments or blanks.
                    if line.startswith("http") and is_valid_url(line.strip()):
                        urls.append(line.strip())
            if not urls:
                logger.warning(
                    f"The file '{args.urls_file}' is empty. No URLs to scrape."
                )
                return
        except FileNotFoundError:
            logger.error(f"Error: The file '{args.urls_file}' was not found.")
            return
        except Exception as e:
            logger.error(f"An error occurred while reading the file: {e}")
            return

        # Database will be created in data/db folder if it doesn't exist
        db = ChromaDBClient(
            db_path="./data/db", collection_name=settings.vector_db_collection_name
        )

        async def run_scraper():
            """Execute the asynchronous scraping workflow and return collected articles.

            Returns:
                list[news_scraper.models.article.Article]: Collected article models.
            """
            async with NewsScraper() as news_scraper:
                articles = await news_scraper.scrape_urls(urls)
                logger.info(f"Scraped {len(articles)} articles")
            return articles

        import asyncio

        articles = asyncio.run(run_scraper())

        for article in articles:
            # Store a single article
            success = db.store_article(article)
            logger.debug(f"Article stored: {success}")
            # logger.debug(f"Title: {article.title}\n URL: {article.url}\n Summary: {article.summary}\n Content: {article.content}\n Topics: {article.topics}")

        all_articles = db.get_all_articles()
        logger.debug(f"Total articles saved in database: {len(all_articles)}")
        for art in all_articles:
            logger.debug(f"Article ID: {art['id']}, Title: {art['metadata']['title']}")

    if args.query is not None:
        while True:
            input_query = input("\n\nEnter your query (or 'exit' to quit): ").strip()
            if input_query.lower() == "exit":
                logger.info("Exiting the application.")
                return
            if not input_query:
                print("Please enter a valid query.")
                continue
            query = input_query
            response = query_engine.query(query)
            print(f"\nResponse: {response}")
            print("\nSource Articles:")
            for node in response.source_nodes:
                # The metadata from your original Article object is preserved!
                title = node.node.metadata.get("title", "No Title")
                score = node.score
                print(
                    f"  - Retrieved article '{title}' with a similarity score of: {score:.4f}"
                )
            input_query = ""  # Reset to prompt for new input


if __name__ == "__main__":
    main()
