# -*- coding: utf-8 -*-
from typing import Type
from uuid import UUID

import eventsourcing.system
from django.apps import AppConfig
from eventsourcing.tests.application import BankAccounts

from tests.emails.application import FormalEmailProcess, InformalEmailProcess


class EventSourcingSystemRunnerConfig(AppConfig):
    name = "tests.eventsourcing_runner_django"
    es_runner: eventsourcing.system.Runner[UUID]

    def ready(self) -> None:
        self.make_runner()

    def make_runner(
        self,
        runner_cls: Type[
            eventsourcing.system.Runner[UUID]
        ] = eventsourcing.system.SingleThreadedRunner[UUID],
    ) -> eventsourcing.system.Runner[UUID]:
        self.es_runner = runner_cls(
            eventsourcing.system.System(
                [
                    [BankAccounts, FormalEmailProcess],
                    [BankAccounts, InformalEmailProcess],
                ]
            )
        )
        return self.es_runner
