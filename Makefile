.PHONY: help install install-dev test test-legacy lint format clean build upload docs

help:  ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install package in development mode
	pip install -e .

install-dev:  ## Install package with development dependencies
	pip install -e .[dev]
	pip install pre-commit
	pre-commit install

test:  ## Run tests with pytest
	pytest tests/ -v

test-legacy:  ## Run legacy test runner
	python run_tests.py

test-all:  ## Run all tests (pytest + legacy)
	pytest tests/ -v

lint:  ## Run linting checks
	flake8 tabbedboxmaker tests
	mypy tabbedboxmaker

format:  ## Format code with black
	black tabbedboxmaker tests *.py

format-check:  ## Check if code formatting is correct
	black --check tabbedboxmaker tests *.py

clean:  ## Clean up build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -delete

build:  ## Build package
	python -m build

upload-test:  ## Upload to Test PyPI
	python -m twine upload --repository testpypi dist/*

upload:  ## Upload to PyPI
	python -m twine upload dist/*

docs:  ## Generate documentation (placeholder)
	@echo "Documentation generation not yet implemented"

check:  ## Run all checks (format, lint, test)
	make format-check
	make lint
	make test
