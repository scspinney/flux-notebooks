.PHONY: venv fmt lint test build

venv:
	python -m venv .venv && . .venv/bin/activate && pip install -U pip && pip install -e .

fmt:
	ruff --fix .
	black .

lint:
	ruff .
	black --check .
	mypy src

test:
	pytest -q

build:
	python -m build
