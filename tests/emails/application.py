# -*- coding: utf-8 -*-
from uuid import UUID

from eventsourcing.application import ProcessingEvent
from eventsourcing.dispatch import singledispatchmethod
from eventsourcing.domain import DomainEventProtocol
from eventsourcing.persistence import JSONTranscoder
from eventsourcing.system import ProcessApplication
from eventsourcing.tests.application import EmailAddressAsStr
from eventsourcing.tests.domain import BankAccount

from tests.emails.domain import EmailNotification


class FormalEmailProcess(ProcessApplication[UUID]):
    def register_transcodings(self, transcoder: JSONTranscoder) -> None:
        super().register_transcodings(transcoder)
        transcoder.register(EmailAddressAsStr())

    def policy(
        self,
        domain_event: DomainEventProtocol[UUID],
        processing_event: ProcessingEvent[UUID],
    ) -> None:
        self._policy(domain_event, processing_event)

    @singledispatchmethod
    def _policy(
        self,
        domain_event: DomainEventProtocol[UUID],
        processing_event: ProcessingEvent[UUID],
    ) -> None:
        """Default policy"""

    @_policy.register
    def _(
        self,
        domain_event: BankAccount.Opened,
        processing_event: ProcessingEvent[UUID],
    ) -> None:
        notification = EmailNotification.create(
            to=domain_event.email_address,
            subject="Your New Account",
            message=(
                "Dear {}, we have successfully created an account in your name.".format(
                    domain_event.full_name
                )
            ),
        )
        processing_event.collect_events(notification)


class InformalEmailProcess(ProcessApplication[UUID]):
    def register_transcodings(self, transcoder: JSONTranscoder) -> None:
        super().register_transcodings(transcoder)
        transcoder.register(EmailAddressAsStr())

    def policy(
        self,
        domain_event: DomainEventProtocol[UUID],
        processing_event: ProcessingEvent[UUID],
    ) -> None:
        self._policy(domain_event, processing_event)

    @singledispatchmethod
    def _policy(
        self,
        domain_event: DomainEventProtocol[UUID],
        processing_event: ProcessingEvent[UUID],
    ) -> None:
        """Default policy"""

    @_policy.register
    def _(
        self,
        domain_event: BankAccount.Opened,
        processing_event: ProcessingEvent[UUID],
    ) -> None:
        notification = EmailNotification.create(
            to=domain_event.email_address,
            subject="Your New Account",
            message="Hi {}, your account is ready.".format(domain_event.full_name),
        )
        processing_event.collect_events(notification)
