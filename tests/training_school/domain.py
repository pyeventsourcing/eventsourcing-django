# -*- coding: utf-8 -*-
from typing import List
from uuid import NAMESPACE_URL, UUID, uuid5

from eventsourcing.domain import Aggregate, event


class Dog(Aggregate):
    @event("Registered")
    def __init__(self, name: str) -> None:
        self.name = name
        self.tricks: List[str] = []

    @staticmethod
    def create_id(name: str) -> UUID:
        return uuid5(NAMESPACE_URL, f"/dogs/{name}")

    @event("TrickAdded")
    def add_trick(self, trick: str) -> None:
        self.tricks.append(trick)
