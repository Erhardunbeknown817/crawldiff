# Contributing to crawldiff

Thanks for your interest in contributing! Here's how to get started.

## Setup

```bash
# Clone the repo
git clone https://github.com/GeoRouv/crawldiff.git
cd crawldiff

# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in development mode with all dependencies
pip install -e ".[dev]"
```

## Development workflow

```bash
# Run tests
pytest tests/ -q

# Run linter
ruff check src/ tests/

# Run type checker
mypy src/crawldiff --strict

# Auto-fix lint issues
ruff check src/ tests/ --fix
```

All three checks (tests, ruff, mypy) must pass before merging. CI runs them automatically on every push and PR.

## Project structure

```
src/crawldiff/
├── cli.py              # Typer app entry point
├── commands/           # CLI command implementations
├── core/               # Business logic (cloudflare API, differ, storage, summarizer)
├── output/             # Output formatters (terminal, JSON, markdown)
└── utils/              # Shared utilities (config, URL normalization, duration parsing)

tests/                  # Mirrors src/ structure
```

## Code style

- Python 3.12+ — use modern syntax (`X | Y` unions, etc.)
- Type hints on all function signatures — enforced by `mypy --strict`
- `snake_case` everywhere (PEP 8)
- Functions over classes; dataclasses for structured data
- `async/await` for all I/O
- User-facing errors via `rich`, not raw tracebacks

## Writing tests

- Use `pytest` with `pytest-asyncio` for async tests
- Use `respx` to mock `httpx` requests
- Use the `tmp_db` fixture from `conftest.py` for database tests
- Tests should be fast and not require network access

## Submitting changes

1. Fork the repo and create a feature branch
2. Make your changes
3. Ensure all checks pass: `pytest && ruff check src/ tests/ && mypy src/crawldiff --strict`
4. Open a pull request with a clear description of what changed and why

## Reporting bugs

Open an issue at [github.com/GeoRouv/crawldiff/issues](https://github.com/GeoRouv/crawldiff/issues) with:
- What you expected to happen
- What actually happened
- Steps to reproduce
- `crawldiff --version` output
