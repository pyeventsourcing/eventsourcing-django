# -*- coding: utf-8 -*-
from django.apps import AppConfig
from django.conf import settings

from tests.training_school.application import TrainingSchool


class TrainingSchoolConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tests.training_school"

    def ready(self) -> None:
        self.training_school = TrainingSchool(env=settings.EVENT_SOURCING_SETTINGS)
