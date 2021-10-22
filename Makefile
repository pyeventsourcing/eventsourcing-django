.EXPORT_ALL_VARIABLES:

COMPOSE_FILE ?= docker/docker-compose-local.yml
COMPOSE_PROJECT_NAME ?= eventsourcing_django

POETRY_VERSION = 1.1.11
POETRY ?= poetry

DJANGO_SETTINGS_MODULE ?= tests.djangoproject.settings

DOTENV_BASE_FILE ?= .env-base
DOTENV_LOCAL_FILE ?= .env

POETRY_INSTALLER_URL ?= https://raw.githubusercontent.com/python-poetry/poetry/master/install-poetry.py

-include $(DOTENV_BASE_FILE)
-include $(DOTENV_LOCAL_FILE)

.PHONY: install-poetry
install-poetry:
	curl -sSL $(POETRY_INSTALLER_URL) | python3
	$(POETRY) --version

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

.PHONY: docker-up
docker-up:
	docker-compose up -d
	docker-compose ps

.PHONY: docker-down
docker-down:
	docker-compose stop

.PHONY: docker-logs
docker-logs:
	docker-compose logs --follow

.PHONY: docker-ps
docker-ps:
	docker-compose ps

.PHONY: migrate
migrate:
	$(POETRY) run django-admin migrate

.PHONY: migrations
migrations:
	$(POETRY) run django-admin makemigrations

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
	$(POETRY) run python -m pytest $(opts) $(call tests,.)
