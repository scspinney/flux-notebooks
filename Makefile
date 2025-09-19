.PHONY: venv fmt lint test build sync book book-clean book-serve clean

# --- tooling paths
VENV_DIR ?= .venv
PYTHON   ?= python3
PY       := $(VENV_DIR)/bin/python
PIP      := $(VENV_DIR)/bin/pip
RUFF     := $(VENV_DIR)/bin/ruff
BLACK    := $(VENV_DIR)/bin/black
MYPY     := $(VENV_DIR)/bin/mypy
PYTEST   := $(VENV_DIR)/bin/pytest
JUPYTEXT := $(VENV_DIR)/bin/jupytext
JB       := $(VENV_DIR)/bin/jupyter-book

# --- runtime config (used by your Settings.from_env)
FLUX_DATASET_ROOT ?=
FLUX_OUTDIR       ?= $(CURDIR)/book/notebooks

venv:
	$(PYTHON) -m venv $(VENV_DIR)
	$(PIP) install -U pip
	$(PIP) install -e .
	$(PIP) install jupytext jupyter-book

fmt:
	$(RUFF) --fix .
	$(BLACK) .

lint:
	$(RUFF) .
	$(BLACK) --check .
	$(MYPY) src

test:
	$(PYTEST) -q

build:
	$(PY) -m build

# Sync .py (percent) <-> .ipynb (paired) before building the book
sync:
	find book -maxdepth 2 -name "*.py" -exec $(JUPYTEXT) --sync {} +

# Build the Jupyter Book (executes notebooks)
book: sync
	FLUX_DATASET_ROOT="$(FLUX_DATASET_ROOT)" FLUX_OUTDIR="$(FLUX_OUTDIR)" \
	$(JB) build book

# Remove generated HTML and paired notebooks
book-clean:
	rm -rf book/_build
	find book -maxdepth 2 -name "*.ipynb" -delete

# Simple local server for the built HTML
book-serve:
	python3 -m http.server -d book/_build/html 8000

# General project clean
clean: book-clean
	rm -rf dist .pytest_cache .ruff_cache .mypy_cache
