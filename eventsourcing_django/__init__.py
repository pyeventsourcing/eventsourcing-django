# -*- coding: utf-8 -*-
from typing import Any

from eventsourcing.persistence import (
    AggregateRecorder,
    ApplicationRecorder,
    InfrastructureFactory,
    OperationalError,
    ProcessRecorder,
)


class Factory(InfrastructureFactory):
    def __init__(self, **kwargs: Any) -> None:
        msg = (
            "Django app not ready. Please call django.setup() after setting "
            "environment variable DJANGO_SETTINGS_MODULE to the settings module of a "
            "Django project that has 'eventsourcing_django' included in its "
            "INSTALLED_APPS setting, and ensure the Django project's database has been "
            "migrated before calling the methods of your event sourcing application."
        )
        raise OperationalError(msg)

    def aggregate_recorder(self, purpose: str = "events") -> AggregateRecorder:
        raise NotImplementedError()

    def application_recorder(self) -> ApplicationRecorder:
        raise NotImplementedError()

    def process_recorder(self) -> ProcessRecorder:
        raise NotImplementedError()
