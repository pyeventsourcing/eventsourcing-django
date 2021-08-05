# Event Sourcing in Python with Django

This package supports using the Python [eventsourcing](https://github.com/johnbywater/eventsourcing) library with [Django](https://www.djangoproject.com/).

## Installation

Use pip to install the [stable distribution](https://pypi.org/project/eventsourcing_django/)
from the Python Package Index. Please note, it is recommended to
install Python packages into a Python virtual environment.

    $ pip install eventsourcing_django


## Synopsis

To use Django with your Python eventsourcing application, use the topic `eventsourcing_django.factory:Factory` as the `INFRASTRUCTURE_FACTORY`
environment variable.

First define a domain model and application, in the usual way.



```python
from eventsourcing.application import Application
from eventsourcing.domain import Aggregate, event


class World(Aggregate):
    def __init__(self):
        self.history = []

    @event("SomethingHappened")
    def make_it_so(self, what):
        self.history.append(what)


class Worlds(Application):
    is_snapshotting_enabled = True
    
    def create_world(self):
        world = World()
        self.save(world)
        return world.id

    def make_it_so(self, world_id, what):
        world = self.repository.get(world_id)
        world.make_it_so(what)
        self.save(world)

    def get_world_history(self, world_id):
        world = self.repository.get(world_id)
        return world.history
```

Setup Django.

```python
import os

import django
from django.core.management import call_command


os.environ.update({
    "DJANGO_SETTINGS_MODULE": "tests.djangoproject.settings",
})

django.setup()

call_command('migrate', 'eventsourcingdjango')
```

Set up environment variables for the event sourcing application.

```python

os.environ.update({
    "INFRASTRUCTURE_FACTORY": "eventsourcingdjango.factory:Factory",
})

```

The application environment variable can be used with others supported
by the library, for example to enable application-level compression and
encryption of stored events, set `COMPRESSOR_TOPIC` and `CIPHER_KEY`.

```python
from eventsourcing.cipher import AESCipher


# Generate a cipher key (keep this safe).
cipher_key = AESCipher.create_key(num_bytes=32)

# Set environment variables.
os.environ.update({
    "COMPRESSOR_TOPIC": "zlib",
    "CIPHER_KEY": cipher_key,
})
```


Construct and use the application.

```python
app = Worlds()
world_id = app.create_world()
app.make_it_so(world_id, "dinosaurs")
app.make_it_so(world_id, "trucks")
app.make_it_so(world_id, "internet")

history = app.get_world_history(world_id)
assert history == ["dinosaurs", "trucks", "internet"]
```


We can see the application is using the SQLAlchemy infrastructure,
and that compression and encryption are enabled, by checking the
attributes of the application object.

```python
from eventsourcingdjango.factory import Factory
from eventsourcingdjango.recorders import DjangoAggregateRecorder
from eventsourcingdjango.recorders import DjangoApplicationRecorder
from eventsourcingdjango.models import StoredEventRecord
from eventsourcingdjango.models import SnapshotRecord
import zlib

assert isinstance(app.factory, Factory)
assert isinstance(app.events.recorder, DjangoApplicationRecorder)
assert isinstance(app.snapshots.recorder, DjangoAggregateRecorder)
assert issubclass(app.events.recorder.model, StoredEventRecord)
assert issubclass(app.snapshots.recorder.model, SnapshotRecord)
assert isinstance(app.mapper.cipher, AESCipher)
assert app.mapper.compressor == zlib
```
