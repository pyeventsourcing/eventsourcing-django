import os

from eventsourcing.tests.test_application_with_popo import (
    TIMEIT_FACTOR,
    TestApplicationWithPOPO,
)

from tests.test_recorders import DjangoTestCase


class TestApplicationWithDjango(DjangoTestCase, TestApplicationWithPOPO):
    timeit_number = 5 * TIMEIT_FACTOR
    expected_factory_topic = "eventsourcing_django.factory:Factory"
    django_db_alias = ""

    def setUp(self) -> None:
        super().setUp()
        os.environ["INFRASTRUCTURE_FACTORY"] = "eventsourcing_django.factory:Factory"
        os.environ["DJANGO_DB_ALIAS"] = self.django_db_alias

    def tearDown(self) -> None:
        del os.environ["INFRASTRUCTURE_FACTORY"]
        del os.environ["DJANGO_DB_ALIAS"]
        super().tearDown()


class TestWithSQLiteFileDb(TestApplicationWithDjango):
    django_db_alias = "sqlite_filedb"
    databases = {"default", "sqlite_filedb"}


class TestWithPostgres(TestApplicationWithDjango):
    django_db_alias = "postgres"
    databases = {"default", "postgres"}



del TestApplicationWithPOPO
