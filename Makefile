.EXPORT_ALL_VARIABLES:

COMPOSE_FILE ?= docker/docker-compose-local.yml
COMPOSE_PROJECT_NAME ?= eventsourcing_django

POETRY_VERSION=2.1.2
POETRY ?= poetry@$(POETRY_VERSION)

DJANGO_SETTINGS_MODULE ?= tests.djangoproject.settings

DOTENV_BASE_FILE ?= .env-base
DOTENV_LOCAL_FILE ?= .env

POETRY_INSTALLER_URL ?= https://install.python-poetry.org

-include $(DOTENV_BASE_FILE)
-include $(DOTENV_LOCAL_FILE)

.PHONY: install-poetry
install-poetry:
	@pipx install --suffix="@$(POETRY_VERSION)" "poetry==$(POETRY_VERSION)"
	$(POETRY) --version

.PHONY: install-packages
install-packages:
	$(POETRY) install -vv $(opts)

.PHONY: install-pre-commit-hooks
install-pre-commit-hooks:
ifeq ($(opts),)
	$(POETRY) run pre-commit install
endif

.PHONY: uninstall-pre-commit-hooks
uninstall-pre-commit-hooks:
ifeq ($(opts),)
	$(POETRY) run pre-commit uninstall
endif

.PHONY: install
install:
	$(POETRY) sync --all-extras $(opts)

.PHONY: update
update: update-lock install

.PHONY: update-lock
update-lock:
	$(POETRY) update --lock -v

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
lint-python: lint-black lint-flake8 lint-isort lint-mypy

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

.PHONY: build
build:
	$(POETRY) build

.PHONY: publish
publish:
	$(POETRY) publish
