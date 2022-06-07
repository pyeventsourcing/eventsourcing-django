# -*- coding: utf-8 -*-

from typing import cast

import eventsourcing.system
from django.apps import apps


def get_runner() -> eventsourcing.system.Runner:
    from tests.eventsourcing_runner_django.apps import EventSourcingSystemRunnerConfig

    app_config = cast(
        EventSourcingSystemRunnerConfig,
        apps.get_app_config("eventsourcing_runner_django"),
    )
    return app_config.es_runner


def get_extra_runner() -> eventsourcing.system.Runner:
    from tests.extra_eventsourcing_runner.apps import (
        ExtraEventSourcingSystemRunnerConfig,
    )

    app_config = cast(
        ExtraEventSourcingSystemRunnerConfig,
        apps.get_app_config("extra_eventsourcing_runner"),
    )
    return app_config.the_runner
