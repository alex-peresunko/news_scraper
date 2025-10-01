import argparse

class ArgParser:
    """Application argument parser."""

    def __init__(self, description="News Scraper Application"):
        """Initializes the argument parser."""
        self.parser = argparse.ArgumentParser(description=description)
        self._add_arguments()

    def _add_arguments(self):
        """Adds arguments to the parser."""
        self.parser.add_argument(
            "--urls-file",
            type=str,
            required=False,
            help="Path to a text file containing URLs to scrape (one URL per line).",
        )
        self.parser.add_argument(
            "--query",
            type=str,
            required=False,
            default="What are the latest news articles?",
            nargs="?",
            help="Query string to ask the LLM about the scraped articles.",
        )

    def parse_args(self):
        """Parses and returns command-line arguments."""
        return self.parser.parse_args()

# Create a single instance for easy import
arg_parser = ArgParser()