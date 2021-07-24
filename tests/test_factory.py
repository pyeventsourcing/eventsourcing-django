import os

from eventsourcing.persistence import InfrastructureFactory
from eventsourcing.tests.infrastructure_testcases import (
    InfrastructureFactoryTestCase,
)
from eventsourcing.utils import get_topic

from eventsourcingdjango.factory import Factory
from eventsourcingdjango.recorders import (
    DjangoAggregateRecorder,
    DjangoApplicationRecorder,
    DjangoProcessRecorder,
)
from tests.test_recorders import DjangoTestCase


class TestFactory(DjangoTestCase, InfrastructureFactoryTestCase):
    def expected_factory_class(self):
        return Factory

    def expected_aggregate_recorder_class(self):
        return DjangoAggregateRecorder

    def expected_application_recorder_class(self):
        return DjangoApplicationRecorder

    def expected_process_recorder_class(self):
        return DjangoProcessRecorder

    def setUp(self) -> None:
        os.environ[InfrastructureFactory.TOPIC] = get_topic(Factory)
        super().setUp()


del InfrastructureFactoryTestCase
