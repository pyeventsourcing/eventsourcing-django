.EXPORT_ALL_VARIABLES:

POETRY_VERSION = 1.1.8
POETRY ?= $(HOME)/.poetry/bin/poetry

DJANGO_SETTINGS_MODULE ?= tests.djangoproject.settings

DOTENV_BASE_FILE ?= .env-base
DOTENV_LOCAL_FILE ?= .env

-include $(DOTENV_BASE_FILE)
-include $(DOTENV_LOCAL_FILE)

.PHONY: install-poetry
install-poetry:
	curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python

.PHONY: install-packages
install-packages:
	$(POETRY) install -vv $(opts)

.PHONY: install-pre-commit-hooks
install-pre-commit-hooks:
ifeq ($(opts),)
	$(POETRY) run pre-commit install
endif

.PHONY: install
install: install-poetry install-packages install-pre-commit-hooks

.PHONY: lock-packages
lock-packages:
	$(POETRY) lock -vv --no-update

.PHONY: update-packages
update-packages:
	$(POETRY) update -vv

.PHONY: lint-bandit
lint-bandit:
	$(POETRY) run bandit --ini .bandit --recursive

.PHONY: lint-black
lint-black:
	$(POETRY) run black --check --diff .

.PHONY: lint-flake8
lint-flake8:
	$(POETRY) run flake8

.PHONY: lint-isort
lint-isort:
	$(POETRY) run isort --check-only --diff .

.PHONY: lint-mypy
lint-mypy:
	$(POETRY) run mypy

.PHONY: lint-python
lint-python: lint-bandit lint-black lint-flake8 lint-isort lint-mypy

.PHONY: lint
lint: lint-python

.PHONY: fmt-black
fmt-black:
	$(POETRY) run black .

.PHONY: fmt-isort
fmt-isort:
	$(POETRY) run isort .

.PHONY: fmt
fmt: fmt-black fmt-isort

.PHONY: test
test:
	$(POETRY) run pytest $(opts) $(call tests,.)
