from django.test import TransactionTestCase

from eventsourcingdjango.models import SnapshotRecord, StoredEventRecord
from eventsourcingdjango.recorders import (
    DjangoAggregateRecorder,
    DjangoApplicationRecorder,
    DjangoProcessRecorder,
)

from eventsourcing.tests.aggregaterecorder_testcase import (
    AggregateRecorderTestCase,
)
from eventsourcing.tests.applicationrecorder_testcase import (
    ApplicationRecorderTestCase,
)
from eventsourcing.tests.processrecorder_testcase import ProcessRecorderTestCase


class DjangoTestCase(TransactionTestCase):
    reset_sequences = True


class TestDjangoAggregateRecorder(DjangoTestCase, AggregateRecorderTestCase):
    def create_recorder(self):
        return DjangoAggregateRecorder(application_name="app", model=StoredEventRecord)


class TestDjangoSnapshotRecorder(DjangoTestCase, AggregateRecorderTestCase):
    def create_recorder(self):
        return DjangoAggregateRecorder(application_name="app", model=SnapshotRecord)


class TestDjangoApplicationRecorder(DjangoTestCase, ApplicationRecorderTestCase):
    def create_recorder(self):
        return DjangoApplicationRecorder(
            application_name="app", model=StoredEventRecord
        )


class TestDjangoProcessRecorder(DjangoTestCase, ProcessRecorderTestCase):
    def create_recorder(self):
        return DjangoProcessRecorder(application_name="app", model=StoredEventRecord)

    def test_performance(self):
        super().test_performance()


del AggregateRecorderTestCase
del ApplicationRecorderTestCase
del ProcessRecorderTestCase
