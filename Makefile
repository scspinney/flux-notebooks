.PHONY: venv fmt lint test build sync book book-clean book-open clean

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

# --- runtime config
FLUX_DATASET_ROOT ?= $(PWD)/superdemo
FLUX_OUTDIR       ?= $(CURDIR)/book/notebooks

venv:
	$(PYTHON) -m venv $(VENV_DIR)
	$(PIP) install -U pip
	# If you have dev extras, prefer: pip install -e ".[dev]"
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

# Keep .py/.ipynb pairs synced
sync:
	find book -maxdepth 2 -name "*.py" -exec $(JUPYTEXT) --sync {} +

FLUX_DATASET_ROOT ?= $(PWD)/superdemo
FLUX_OUTDIR       ?= $(CURDIR)/book/notebooks

# Build the book (depends on sync)
book: sync
	FLUX_DATASET_ROOT="$(FLUX_DATASET_ROOT)" \
	FLUX_OUTDIR="$(FLUX_OUTDIR)" \
	$(JB) build book


book-clean:
	$(JB) clean book --all

book-open:
	xdg-open book/_build/html/index.html 2>/dev/null || open book/_build/html/index.html 2>/dev/null || true

clean: book-clean
	find book -maxdepth 3 -name "*.ipynb" -delete || true
