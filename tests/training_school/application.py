# -*- coding: utf-8 -*-
from typing import List
from uuid import UUID

from eventsourcing.application import Application

from tests.training_school.domain import Dog


class TrainingSchool(Application[UUID]):
    def register(self, name: str) -> None:
        dog = Dog(name)
        self.save(dog)

    def add_trick(self, name: str, trick: str) -> None:
        dog: Dog = self.repository.get(Dog.create_id(name))
        dog.add_trick(trick)
        self.save(dog)

    def get_tricks(self, name: str) -> List[str]:
        dog: Dog = self.repository.get(Dog.create_id(name))
        return dog.tricks
