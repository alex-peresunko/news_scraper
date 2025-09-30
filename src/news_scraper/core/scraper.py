"""
News scraping functionality using Selenium with chromedriver-autoinstaller
for automated WebDriver management.
"""

import asyncio
import re
import time
from typing import List, Optional
from urllib.parse import urljoin, urlparse


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
    return url.startswith(('http://', 'https://'))

def normalize_url(url: str) -> str:
    return url.strip()

# --- End Mock Objects ---


class NewsScraper:
    """News scraper with async support, using Selenium for robust page fetching."""

    def __init__(self):
        """
        Initialize the scraper.
        This will automatically check for and install the correct version of ChromeDriver.
        """
        # Automatically download and install the correct chromedriver version
        chromedriver_autoinstaller.install()
        logger.info("ChromeDriver is checked and up-to-date.")
        self.semaphore = asyncio.Semaphore(settings.max_concurrent_requests)

    async def __aenter__(self) :
        """
        Async context manager entry.
        Ensures ChromeDriver is installed and ready for use.
        """
        logger.info("Entering scraper context. Checking for ChromeDriver...")
        # Automatically download and install the correct chromedriver version
        chromedriver_autoinstaller.install()
        logger.debug("ChromeDriver is ready.")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Async context manager exit.
        Logs the exit status. No specific cleanup is needed as Selenium
        instances are managed per-request.
        """
        if exc_type:
            logger.error(f"Exiting scraper context due to an exception: {exc_val}")
        else:
            logger.debug("Exiting scraper context.")
        # No resources to clean up here, but this is the correct place for it.
        pass

    def _get_html_with_selenium(self, url: str) -> str:
        """
        Fetches the HTML of a URL using a synchronous Selenium instance.
        This method is designed to be run in a separate thread.
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
        """
        Scrape a single URL using Selenium and newspaper3k.
        """
        async with self.semaphore:
            try:
                if not is_valid_url(url):
                    logger.error(f"Invalid URL: {url}")
                    return None
                
                url = normalize_url(url)
                logger.info(f"Scraping URL: {url}")
                
                # Run the blocking Selenium code in a separate thread
                html_content = await asyncio.to_thread(self._get_html_with_selenium, url)

                # Use newspaper3k to parse the HTML obtained from Selenium
                article = NewspaperArticle(url)
                article.download(input_html=html_content)
                article.parse()
                
                if not article.title or not article.text:
                    logger.warning(f"No title or text found for URL: {url}")
                    return None
                
                scraped_article = Article(
                    url=url,
                    title=article.title.strip(),
                    content=article.text.strip(),
                    authors=article.authors or [],
                    # publish_date=article.publish_date,
                    top_image=article.top_image,
                    meta_description=article.meta_description or "",
                    meta_keywords=article.meta_keywords or [],
                    source_domain=urlparse(url).netloc
                )
                
                logger.success(f"Successfully scraped: {url}")
                
                if settings.rate_limit_delay > 0:
                    await asyncio.sleep(settings.rate_limit_delay)
                
                return scraped_article
                
            except Exception as e:
                logger.error(f"Error scraping {url}: {e}")
                return None

    async def scrape_urls(self, urls: List[str]) -> List[Article]:
        """
        Scrape multiple URLs concurrently.
        """
        logger.info(f"Starting to scrape {len(urls)} URLs")
        tasks = [self.scrape_url(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        articles = [res for res in results if isinstance(res, Article)]
        
        logger.info(f"Successfully scraped {len(articles)} out of {len(urls)} URLs")
        return articles

    async def extract_links_from_page(self, url: str, same_domain_only: bool = True) -> List[str]:
        """
        Extract article links from a webpage using Selenium.
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
        """Heuristic to determine if a URL likely points to an article."""
        article_patterns = [r'/\d{4}/\d{2}/', r'/story/', '/article/', '/news/']
        exclude_patterns = ['/category/', '/tag/', '/author/']
        url_path = urlparse(url).path.lower()
        if any(re.search(p, url_path) for p in exclude_patterns):
            return False
        return any(re.search(p, url_path) for p in article_patterns)

