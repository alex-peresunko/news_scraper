"""Initializes and provides the PlayWrightBrowserToolkit for the LangChain agent."""

import asyncio
from langchain_community.agent_toolkits.playwright.toolkit import PlayWrightBrowserToolkit
from playwright.async_api import async_playwright
from news_scraper.config.settings import settings_instance as settings


class ToolkitManager:
    """Manages the creation and retrieval of the PlayWrightBrowserToolkit."""

    _toolkit = None
    _browser = None
    _playwright = None
    _lock = asyncio.Lock()  # Add a lock for thread-safe initialization

    @classmethod
    async def get_toolkit(cls) -> PlayWrightBrowserToolkit:
        """
        Initializes and returns a singleton instance of the PlayWrightBrowserToolkit.
        Uses a lock to prevent race conditions during concurrent initialization.
        """
        if cls._toolkit is None:
            async with cls._lock:
                # Double-check if another coroutine initialized it while we were waiting for the lock
                if cls._toolkit is None:
                    # Start playwright and launch the browser correctly
                    cls._playwright = await async_playwright().start()
                    cls._browser = await cls._playwright.chromium.launch(headless=True)
                    context = await cls._browser.new_context(user_agent=settings.user_agent)
                    cls._toolkit = PlayWrightBrowserToolkit.from_browser(async_browser=cls._browser)
        return cls._toolkit

    @classmethod
    async def close_browser(cls):
        """Closes the browser and stops the playwright instance if they are running."""
        if cls._browser:
            await cls._browser.close()
        if cls._playwright:
            await cls._playwright.stop()

        cls._browser = None
        cls._toolkit = None
        cls._playwright = None


