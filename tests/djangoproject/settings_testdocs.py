# -*- coding: utf-8 -*-
from eventsourcing.cipher import AESCipher

from tests.djangoproject.settings import *  # noqa: F403

INSTALLED_APPS = INSTALLED_APPS + ["tests.training_school"]  # noqa: F405

EVENT_SOURCING_SETTINGS = EVENT_SOURCING_APPLICATION = {
    "PERSISTENCE_MODULE": "eventsourcing_django",
    "DJANGO_DB_ALIAS": "postgres",
    "IS_SNAPSHOTTING_ENABLED": "y",
    "COMPRESSOR_TOPIC": "eventsourcing.compressor:ZlibCompressor",
    "CIPHER_TOPIC": "eventsourcing.cipher:AESCipher",
    "CIPHER_KEY": AESCipher.create_key(num_bytes=32),
}
