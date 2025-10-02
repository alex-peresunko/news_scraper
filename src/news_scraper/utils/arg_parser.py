import argparse


class ArgParser:
    """Encapsulate the CLI argument definition for the news scraper entry point."""

    def __init__(self, description="News Scraper Application"):
        """Initialise the parser with the shared description used across tooling.

        Args:
            description: Short text displayed in ``--help`` output.
        """
        self.parser = argparse.ArgumentParser(description=description)
        self._add_arguments()

    def _add_arguments(self):
        """Register scraping and query flags on the underlying parser."""
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
        """Parse known arguments and provide an ``argparse.Namespace`` for consumers.

        Returns:
            argparse.Namespace: Parsed CLI arguments.
        """
        return self.parser.parse_args()


# Create a single instance for easy import
arg_parser = ArgParser()
