import os

from eventsourcing.tests.test_application_with_popo import (
    TIMEIT_FACTOR,
    TestApplicationWithPOPO,
)

from tests.test_recorders import DjangoTestCase


class TestApplicationWithDjango(DjangoTestCase, TestApplicationWithPOPO):
    timeit_number = 5 * TIMEIT_FACTOR
    expected_factory_topic = "eventsourcingdjango.factory:Factory"

    def setUp(self) -> None:
        super().setUp()

        os.environ["INFRASTRUCTURE_FACTORY"] = "eventsourcingdjango.factory:Factory"

    def tearDown(self) -> None:
        del os.environ["INFRASTRUCTURE_FACTORY"]
        super().tearDown()


del TestApplicationWithPOPO
