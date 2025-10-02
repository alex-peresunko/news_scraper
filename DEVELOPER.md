# Developer Guide

A companion document for engineers contributing to the News Scraper project. It covers environment setup, tooling, conventions, and common workflows.

---

## Table of Contents

1. [Onboarding](#onboarding)
2. [Development Workflow](#development-workflow)
3. [Tooling & Commands](#tooling--commands)
4. [Coding Standards](#coding-standards)
5. [Testing Strategy](#testing-strategy)
6. [Documentation](#documentation)
7. [Data & Secrets](#data--secrets)
8. [Release Checklist](#release-checklist)
9. [Troubleshooting Tips](#troubleshooting-tips)

---

## Onboarding

1. **Clone and create a virtual environment** (PowerShell shown):
   ```powershell
   git clone https://github.com/alex-peresunko/news_scraper.git
   cd news_scraper
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
2. **Install dependencies**:
   ```powershell
   python -m pip install --upgrade pip
   pip install -r .\src\news_scraper\requirements.txt
   pip install -e .
   ```
3. **Configure environment variables**:
   ```powershell
   copy .\config\.env.example .\.env
   # Edit .env to add your OpenAI key and any overrides
   ```
4. Run a quick smoke test to ensure the CLI boots:
   ```powershell
   python -m src.news_scraper.main --help
   ```

## Development Workflow

- **Branching**: use feature branches named `feature/<summary>` or `bugfix/<summary>`.
- **Commits**: follow Conventional Commits (`feat:`, `fix:`, `docs:`, etc.) to keep history readable and support changelog automation.
- **Pull Requests**: include a summary, testing evidence, and screenshots/logs when relevant. Reference GitHub issues using `Fixes #<id>` to auto-close.

## Tooling & Commands

| Purpose | Command |
| --- | --- |
| Format code (Black target py312) | `python -m black src/news_scraper` |
| Static type hints check (optional) | `python -m mypy src/news_scraper` |
| Quick syntax sanity check | `python -m compileall src/news_scraper` |
| Run scraper on sample data | `python -m src.news_scraper.main --urls-file sample_url_list.txt` |
| Launch interactive query workflow | `python -m src.news_scraper.main --query` |
| Regenerate API docs | `pdoc -o docs .\src\news_scraper\core ...` |

> Tip: create PowerShell aliases or scripts in `scripts/` for repetitive tasks.

## Coding Standards

- **Python version**: target 3.12; use modern typing (PEP 604 unions, `typing.Annotated` when helpful).
- **Docstrings**: every public class and method requires an informative docstring (keep doc/design decisions in sync).
- **Logging**: rely on `loguru` via `news_scraper.utils.logging.setup_logging`; prefer structured, contextual messages.
- **Configuration**: extend `Settings` in `config/settings.py`; avoid reading environment variables ad-hoc.
- **Error handling**: raise descriptive exceptions or log with context IDs (see `analyze_article_content`).
- **Imports**: group standard library, third-party, then local modules.

## Testing Strategy

Formal pytest suites are not yet in place. For now:

1. **Static checks**: run `python -m compileall src/news_scraper` before opening a PR.
2. **Manual e2e**: execute a scrape using `sample_url_list.txt` and verify that articles persist under `./data/db`.
3. **Interactive QA**: run the query workflow and ensure responses return expected metadata.

When adding new functionality, include pytest-based tests under `tests/` and update `pyproject.toml` accordingly.

## Documentation

- Project-wide usage details live in [`README.md`](README.md).
- API documentation is generated from docstrings using `pdoc`; keep docstrings accurate and concise.
- Architectural decisions worth preserving should be captured in `docs/decisions/<YYYY-MM-DD>-<topic>.md` (create this hierarchy as needed).

## Data & Secrets

- ChromaDB files are stored under `./data/db` by default. They are environment-specific; do **not** commit them.
- Logs rotate in `./logs`. Inspect recent entries when debugging scraping failures.
- Never commit `.env` or actual API keys. Add new secrets to `.env.example` with sensible defaults or placeholders.

## Release Checklist

1. Update version and changelog (if/when a CHANGELOG.md is added).
2. Run scrapers on a smoke dataset and confirm the query engine still works.
3. Regenerate documentation: `pdoc -o docs ...`.
4. Tag the release: `git tag vX.Y.Z && git push --tags`.
5. Publish binaries or Docker images if distribution evolves.

## Troubleshooting Tips

| Symptom | Diagnostic Steps |
| --- | --- |
| Selenium timeouts | Increase `REQUEST_TIMEOUT`/`RATE_LIMIT_DELAY`, confirm the site is reachable manually. |
| OpenAI quota errors | Check account usage; reduce concurrency or lower the crawl size. |
| Chroma schema mismatch | Delete `./data/db` (or use `ChromaDBClient.reset_collection`) and re-ingest. |
| Missing logs | Ensure `.env` points `LOG_FILE` to a writeable location. |

Feel free to extend this guide as the project evolves—up-to-date developer docs keep the team fast and confident.
