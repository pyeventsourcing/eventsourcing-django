from eventsourcing.persistence import (
    AggregateRecorder,
    ApplicationRecorder,
    InfrastructureFactory,
    ProcessRecorder,
)

from eventsourcingdjango.models import SnapshotRecord, StoredEventRecord
from eventsourcingdjango.recorders import (
    DjangoAggregateRecorder,
    DjangoApplicationRecorder,
    DjangoProcessRecorder,
)


class Factory(InfrastructureFactory):
    def aggregate_recorder(self, purpose: str = "events") -> AggregateRecorder:
        if purpose == "snapshots":
            model = SnapshotRecord
        else:
            model = StoredEventRecord
        return DjangoAggregateRecorder(
            application_name=self.application_name, model=model
        )

    def application_recorder(self) -> ApplicationRecorder:
        return DjangoApplicationRecorder(
            application_name=self.application_name, model=StoredEventRecord
        )

    def process_recorder(self) -> ProcessRecorder:
        return DjangoProcessRecorder(
            application_name=self.application_name, model=StoredEventRecord
        )
