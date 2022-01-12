# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Type

from eventsourcing.persistence import InfrastructureFactory
from eventsourcing.tests.infrastructure_factory import InfrastructureFactoryTestCase
from eventsourcing.utils import Environment

from eventsourcing_django.factory import Factory
from eventsourcing_django.recorders import (
    DjangoAggregateRecorder,
    DjangoApplicationRecorder,
    DjangoProcessRecorder,
)
from tests.test_recorders import DjangoTestCase


class TestFactory(DjangoTestCase, InfrastructureFactoryTestCase):
    def setUp(self) -> None:
        self.env = Environment("TestCase")
        self.env[InfrastructureFactory.PERSISTENCE_MODULE] = Factory.__module__
        super().setUp()

    def expected_factory_class(self) -> Type[Factory]:
        return Factory

    def expected_aggregate_recorder_class(self) -> Type[DjangoAggregateRecorder]:
        return DjangoAggregateRecorder

    def expected_application_recorder_class(self) -> Type[DjangoApplicationRecorder]:
        return DjangoApplicationRecorder

    def expected_process_recorder_class(self) -> Type[DjangoProcessRecorder]:
        return DjangoProcessRecorder


del InfrastructureFactoryTestCase
