"""
News scraping functionality using Selenium with chromedriver-autoinstaller
for automated WebDriver management.
"""

import asyncio
import re
import time
from typing import List, Optional
from urllib.parse import urljoin, urlparse
from pydantic import HttpUrl


from news_scraper.core.genai import analyze_article_content
from news_scraper.config.settings import settings_instance as settings
from news_scraper.models.article import Article
from news_scraper.utils.logging import logger

import chromedriver_autoinstaller
from bs4 import BeautifulSoup
from newspaper import Article as NewspaperArticle
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException


def is_valid_url(url: str) -> bool:
    """Return ``True`` when the given string is an HTTP(S) URL candidate.

    Args:
        url: String to validate.

    Returns:
        bool: ``True`` if the value starts with an HTTP scheme.
    """
    return url.startswith(('http://', 'https://'))


def normalize_url(url: str) -> str:
    """Return the trimmed representation of a URL to avoid trailing whitespace.

    Args:
        url: Original URL value.

    Returns:
        str: Cleaned URL suitable for downstream processing.
    """
    return url.strip()

# --- End Mock Objects ---


class NewsScraper:
    """News scraper with async support, using Selenium for robust page fetching."""

    def __init__(self):
        """Prepare Selenium dependencies and concurrency controls for scraping sessions."""
        # Automatically download and install the correct chromedriver version
        chromedriver_autoinstaller.install()
        logger.info("ChromeDriver is checked and up-to-date.")
        self.semaphore = asyncio.Semaphore(settings.max_concurrent_requests)

    async def __aenter__(self):
        """Return the scraper instance after verifying ChromeDriver availability.

        Returns:
            NewsScraper: The prepared scraper instance for use in ``async with``.
        """
        logger.info("Entering scraper context. Checking for ChromeDriver...")
        # Automatically download and install the correct chromedriver version
        chromedriver_autoinstaller.install()
        logger.debug("ChromeDriver is ready.")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Handle context exit by logging success or bubbling up exceptions.

        Args:
            exc_type: Exception type raised within the context.
            exc_val: Exception instance raised within the context.
            exc_tb: Traceback associated with the exception.
        """
        if exc_type:
            logger.error(f"Exiting scraper context due to an exception: {exc_val}")
        else:
            logger.debug("Exiting scraper context.")
        # No resources to clean up here, but this is the correct place for it.
        pass

    def _get_html_with_selenium(self, url: str) -> str:
        """Fetch HTML by driving a headless Chrome session synchronously.

        Args:
            url: Fully-qualified URL to request.

        Returns:
            str: The raw HTML returned by the browser.

        Raises:
            TimeoutException: If the page load exceeds the configured timeout.
            WebDriverException: For any Selenium-related failure.
        """
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument(f"user-agent={settings.user_agent}")
        chrome_options.add_argument("--log-level=3") # Suppress selenium logs
        chrome_options.add_argument("--window-size=1920,1080")
        
        driver = None
        try:
            # The driver is now found automatically by Selenium
            driver = webdriver.Chrome(options=chrome_options)
            driver.set_page_load_timeout(settings.request_timeout)
            
            logger.debug(f"Selenium navigating to: {url}")
            driver.get(url)

            # Allow the page time to execute JavaScript and render late-loading content.
            time.sleep(5) 
            
            html_content = driver.page_source
            logger.debug(f"Successfully retrieved HTML from {url}")
            return html_content
        
        except (TimeoutException, WebDriverException) as e:
            logger.error(f"Selenium failed to get URL {url}: {e}")
            raise
        finally:
            if driver:
                driver.quit()

    async def scrape_url(self, url: str) -> Optional[Article]:
        """Scrape and enrich a single news article.

        Args:
            url: Target page to scrape.

        Returns:
            Optional[Article]: A populated article model or ``None`` on failure.
        """
        async with self.semaphore:
            try:
                if not is_valid_url(url):
                    logger.error(f"Invalid URL: {url}")
                    return None
                
                url = normalize_url(url)
                logger.info(f"Scraping URL: {url}")
                
                # Run the blocking Selenium code in a separate thread
                # (asyncio.to_thread keeps the event loop responsive while Selenium runs).
                html_content = await asyncio.to_thread(self._get_html_with_selenium, url)

                # Use newspaper3k to parse the HTML obtained from Selenium
                article = NewspaperArticle(url)
                article.download(input_html=html_content)
                article.parse()
                
                if not article.title or not article.text:
                    logger.warning(f"No title or text found for URL: {url}")
                    return None
                
                # Analyze the article content using GenAI
                summary, topics = await analyze_article_content(url, article.text)
                
                scraped_article = Article(
                    url=HttpUrl(url),
                    title=article.title.strip(),
                    content=article.text.strip(),
                    authors=article.authors or [],
                    top_image=article.top_image,
                    meta_description=article.meta_description or "",
                    meta_keywords=article.meta_keywords or [],
                    source_domain=urlparse(url).netloc,
                    summary=summary,
                    topics=topics
                )
                
                logger.success(f"Successfully scraped: {url}")
                logger.debug(f"Analyzed data for URL {url}\nTitle: {scraped_article.title}\nSummary: {scraped_article.summary}\nTopics: {scraped_article.topics}")
                
                if settings.rate_limit_delay > 0:
                    # Respect target sites' rate limits to reduce the chance of throttling.
                    await asyncio.sleep(settings.rate_limit_delay)
                
                return scraped_article
                
            except Exception as e:
                logger.error(f"Error scraping {url}: {e}")
                return None

    async def scrape_urls(self, urls: List[str]) -> List[Article]:
        """Scrape multiple URLs concurrently while preserving ordering.

        Args:
            urls: A list of absolute URLs to collect.

        Returns:
            List[Article]: Successfully scraped articles.
        """
        logger.info(f"Starting to scrape {len(urls)} URLs")
        tasks = [self.scrape_url(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        articles = [res for res in results if isinstance(res, Article)]
        
        logger.info(f"Successfully scraped {len(articles)} out of {len(urls)} URLs")
        return articles

    async def extract_links_from_page(self, url: str, same_domain_only: bool = True) -> List[str]:
        """Discover candidate article links from a page.

        Args:
            url: Seed page to crawl for anchors.
            same_domain_only: When ``True``, restrict results to the seed domain.

        Returns:
            List[str]: Deduplicated list of article-like URLs.
        """
        try:
            html_content = await asyncio.to_thread(self._get_html_with_selenium, url)
            soup = BeautifulSoup(html_content, 'html.parser')
            base_domain = urlparse(url).netloc
            links = []
            
            for link in soup.find_all('a', href=True):
                href = urljoin(url, str(link['href']))
                
                if same_domain_only and urlparse(href).netloc != base_domain:
                    continue
                
                if self._is_likely_article_url(href):
                    links.append(href)
            
            unique_links = list(dict.fromkeys(links))
            logger.info(f"Extracted {len(unique_links)} potential article links from {url}")
            return unique_links
            
        except Exception as e:
            logger.error(f"Error extracting links from {url}: {e}")
            return []
    
    def _is_likely_article_url(self, url: str) -> bool:
        """Return ``True`` when heuristics classify the path as an article link.

        Args:
            url: Candidate URL to assess.

        Returns:
            bool: ``True`` for article-like URLs, ``False`` otherwise.
        """
        article_patterns = [r'/\d{4}/\d{2}/', r'/story/', '/article/', '/news/']
        exclude_patterns = ['/category/', '/tag/', '/author/']
        url_path = urlparse(url).path.lower()
        if any(re.search(p, url_path) for p in exclude_patterns):
            return False
        return any(re.search(p, url_path) for p in article_patterns)

