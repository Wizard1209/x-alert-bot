.PHONY: run dev lint format

run:
	uv run python -m bot.main

dev:
	uv sync --group dev

lint:
	uv run ruff check . --fix

format:
	uv run ruff format .
