from langchain_core.tools import tool
from playwright.async_api import Browser
import trafilatura

class PageInteractionError(Exception):
    """Custom exception for errors during page interaction."""
    pass

@tool
async def get_and_extract_article_content(url: str, browser: Browser) -> str:
    """
    Navigates to the given URL and extracts the main article content and title
    using the trafilatura library. This is the most reliable tool for getting
    article text.
    """
    page = None
    try:
        page = await browser.new_page()
        
        # Go to the page and wait for network activity to cease
        await page.goto(url, wait_until="networkidle", timeout=60000)

        # Some sites have cookie banners that can interfere.
        # This is a heuristic to try and click an accept button.
        accept_selectors = [
            "button:has-text('Accept')",
            "button:has-text('Agree')",
            "button:has-text('Consent')",
            "button:has-text('I understand')",
        ]
        for selector in accept_selectors:
            try:
                await page.locator(selector).click(timeout=2000)
                break # Stop after the first successful click
            except Exception:
                pass # Selector not found, continue

        html_content = await page.content()
        
        # Use trafilatura to extract the main content
        # The 'include_comments=False' and 'include_tables=False' are good defaults
        extracted_text = trafilatura.extract(
            html_content,
            include_comments=False,
            include_tables=False,
            output_format='text'
        )
        
        if not extracted_text:
            raise PageInteractionError("Trafilatura could not extract content.")
            
        return extracted_text

    except Exception as e:
        return f"Error interacting with page at {url}: {e}"
    finally:
        if page:
            await page.close()