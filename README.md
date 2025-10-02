# News Scraper

An automated pipeline that scrapes news articles with Selenium, enriches them with OpenAI-powered summarisation, and stores structured insights in a Chroma vector database for semantic querying via LlamaIndex.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Key Features](#key-features)
3. [Architecture](#architecture)
4. [Prerequisites](#prerequisites)
5. [Installation](#installation)
6. [Configuration](#configuration)
7. [Usage](#usage)
8. [Data & Storage](#data--storage)
9. [Logging](#logging)
10. [Generating Documentation](#generating-documentation)
11. [Troubleshooting](#troubleshooting)
12. [Project Structure](#project-structure)
13. [Support & Contributions](#support--contributions)

---

## Project Overview

News Scraper automates the collection and post-processing of news content. The system downloads pages with Selenium, extracts the key article information with `newspaper3k`, calls OpenAI to produce a concise summary and topic list, and stores everything in ChromaDB so you can query the corpus semantically.

The application targets **Python 3.12** and has been validated with OpenAI model `gpt-5-nano`. Other Python or model versions may require additional verification.

## Key Features

- **Automated scraping** of news websites using headless Chromium.
- **AI-assisted enrichment** with OpenAI to summarise content and extract topical keywords.
- **Vector search** powered by ChromaDB and LlamaIndex for semantic querying of scraped articles.
- **Configurable concurrency** and throttling safeguards to avoid overloading target sites.
- **Structured logging** with rotation for production diagnostics.

## Architecture

| Layer | Responsibility |
| --- | --- |
| `news_scraper/core/scraper.py` | Drives Selenium to fetch pages and orchestrates article parsing. |
| `news_scraper/core/genai.py` | Calls OpenAI asynchronously to generate summaries and topics. |
| `news_scraper/db/chroma_client.py` | Persists articles in ChromaDB with automatic chunking for long texts. |
| `news_scraper/core/llamaindex.py` | Exposes a query engine backed by Chroma and OpenAI embeddings. |
| `news_scraper/main.py` | CLI entry point that wires scraping and querying workflows. |

The application keeps data under `./data`, logs under `./logs`, and loads configuration from `.env` (via Pydantic `BaseSettings`).

## Prerequisites

- Python **3.12.x** (3.12.3 tested)
- Google Chrome or Chromium (Selenium + `chromedriver-autoinstaller` rely on a local browser install)
- OpenAI API credentials with access to the configured model (default: `gpt-5-nano`)
- Optional: `make` (or PowerShell) for convenience scripts

## Installation

```powershell
git clone https://github.com/alex-peresunko/news_scraper.git
cd news_scraper
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r .\src\news_scraper\requirements.txt
pip install -e .
```

> **Note:** The project uses an editable install (`pip install -e .`) so that local changes under `src/` are immediately reflected in the runtime environment.

## Configuration

1. Copy the sample environment file and update the values:

	```powershell
	copy .\config\.env.example .\.env
	```

2. Provide at least the following variables in `.env`:

	| Variable | Description |
	| --- | --- |
	| `OPENAI_API_KEY` | Personal OpenAI API token. |
	| `OPENAI_MODEL` | Chat model used for summarisation (`gpt-5-nano` tested). |
	| `VECTOR_DB_PATH` | Directory for Chroma persistent storage (defaults to `./data/chroma_db`). |
	| `USER_AGENT` | User agent string presented to scraped sites. |
	| `MAX_CONCURRENT_REQUESTS` | Number of URLs scraped simultaneously.

	Additional options (logging, rate limits, embeddings) can be tuned in `.env.example`.

## Usage

### 1. Scrape articles from a URL list

Prepare a text file that contains one URL per line (see `sample_url_list.txt` for an example) and run:

```powershell
python -m src.news_scraper.main --urls-file sample_url_list.txt
```

The scraper will:

1. Download each URL with Selenium.
2. Parse titles, authors, text, and metadata via `newspaper3k`.
3. Enrich the article with an OpenAI summary and topics.
4. Persist the article (and any necessary chunks) in ChromaDB under `./data/db`.

### 2. Query the knowledge base interactively

Once you have scraped content, launch the query workflow:

```powershell
python -m src.news_scraper.main --query
```

You will be prompted for natural-language questions. Answers are generated via LlamaIndex’s query engine, which retrieves from ChromaDB and synthesises responses using the configured OpenAI model. Type `exit` to leave the prompt.

### 3. Combining scraping and querying

You can run both workflows sequentially in a single session, e.g. scrape a new batch and then launch the query prompt. Each step reads from and writes to the same Chroma collection configured by `VECTOR_DB_COLLECTION_NAME`.

## Data & Storage

- **ChromaDB**: Stored under `./data/db` (configurable). Large articles are split into token-aware chunks with metadata describing the source document and chunk order.
- **Artifacts**: Raw parsed content is not stored separately; the persisted document combines title and text.
- **Backups**: Because the collection lives on disk, include `data/` in your backup routine if persistence matters.

## Logging

Log files live under `./logs` and rotate based on `.env` settings. Levels follow Loguru conventions (`DEBUG`, `INFO`, `SUCCESS`, etc.). Adjust verbosity by editing `LOG_LEVEL`.

## Generating Documentation

The project is docstring-rich and compatible with `pdoc`. To regenerate the API docs locally:

```powershell
pdoc -o docs .\src\news_scraper\main .\src\news_scraper\config .\src\news_scraper\core .\src\news_scraper\db .\src\news_scraper\models .\src\news_scraper\utils
```

The HTML output is emitted under `./docs`.

## Troubleshooting

| Issue | Resolution |
| --- | --- |
| Selenium cannot locate Chrome | Ensure Google Chrome/Chromium is installed and accessible in PATH. `chromedriver-autoinstaller` matches the local browser version. |
| OpenAI authentication errors | Confirm `OPENAI_API_KEY` is valid and not rate-limited. |
| Empty vector store results | Confirm articles were scraped successfully and that `VECTOR_DB_PATH` points to the same directory used by the query engine. |
| Permission issues on Windows | Run the terminal as Administrator if Selenium or filesystem operations fail due to access restrictions. |

## Project Structure

```
news_scraper/
├── config/              # Environment templates and configuration helpers
├── data/                # ChromaDB storage (created at runtime)
├── docs/                # Generated documentation (optional)
├── logs/                # Rotating log files
├── sample_url_list.txt  # Example input list of news URLs
├── src/
│   └── news_scraper/
│       ├── core/        # Scraper, GenAI, and query integrations
│       ├── db/          # Chroma client wrapper
│       ├── models/      # Pydantic data models
│       ├── utils/       # CLI, logging, and helper utilities
│       └── main.py      # CLI entry point
└── tests/               # (Reserved for future automated tests)
```

## Support & Contributions

- For feature requests or bug reports, please open an issue in the repository.
- Contributions are welcome—see [`DEVELOPER.md`](DEVELOPER.md) for coding standards, testing guidelines, and release notes.

Happy scraping! 🗞️