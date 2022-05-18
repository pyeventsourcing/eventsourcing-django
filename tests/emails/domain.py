# -*- coding: utf-8 -*-
from __future__ import annotations

import dataclasses
from uuid import uuid4

from eventsourcing.domain import Aggregate


@dataclasses.dataclass
class EmailNotification(Aggregate):
    to: str
    subject: str
    message: str

    @classmethod
    def create(cls, to: str, subject: str, message: str) -> EmailNotification:
        return cls._create(
            cls.Created,
            id=uuid4(),
            to=to,
            subject=subject,
            message=message,
        )

    class Created(Aggregate.Created):
        to: str
        subject: str
        message: str
