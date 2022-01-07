# -*- coding: utf-8 -*-
from django.apps import AppConfig


class EventsourcingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "eventsourcing_django"

    def ready(self) -> None:
        import eventsourcing_django
        from eventsourcing_django.factory import Factory

        eventsourcing_django.Factory = Factory  # type: ignore
