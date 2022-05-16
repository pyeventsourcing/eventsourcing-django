# -*- coding: utf-8 -*-
from functools import singledispatchmethod

from eventsourcing.application import ProcessingEvent
from eventsourcing.domain import AggregateEvent
from eventsourcing.persistence import Transcoder
from eventsourcing.system import ProcessApplication
from eventsourcing.tests.application import EmailAddressAsStr
from eventsourcing.tests.domain import BankAccount

from tests.emails.domain import EmailNotification


class FormalEmailProcess(ProcessApplication):
    def register_transcodings(self, transcoder: Transcoder) -> None:
        super().register_transcodings(transcoder)
        transcoder.register(EmailAddressAsStr())

    @singledispatchmethod
    def policy(
        self, domain_event: AggregateEvent, processing_event: ProcessingEvent
    ) -> None:
        """Default policy"""

    @policy.register
    def _(
        self,
        domain_event: BankAccount.Opened,
        processing_event: ProcessingEvent,
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


class InformalEmailProcess(ProcessApplication):
    def register_transcodings(self, transcoder: Transcoder) -> None:
        super().register_transcodings(transcoder)
        transcoder.register(EmailAddressAsStr())

    @singledispatchmethod
    def policy(
        self, domain_event: AggregateEvent, processing_event: ProcessingEvent
    ) -> None:
        """Default policy"""

    @policy.register
    def _(
        self,
        domain_event: BankAccount.Opened,
        processing_event: ProcessingEvent,
    ) -> None:
        notification = EmailNotification.create(
            to=domain_event.email_address,
            subject="Your New Account",
            message="Hi {}, your account is ready.".format(domain_event.full_name),
        )
        processing_event.collect_events(notification)
