# -*- coding: utf-8 -*-
from django.apps import AppConfig


class EventsourcingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "eventsourcing_django"

    def ready(self):
        import eventsourcing_django
        import eventsourcing_django.factory

        eventsourcing_django.Factory = eventsourcing_django.factory.Factory
