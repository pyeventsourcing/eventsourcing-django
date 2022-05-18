# Event Sourcing with Django

This package supports using the Python
[eventsourcing](https://github.com/pyeventsourcing/eventsourcing) library
with [Django ORM](https://www.djangoproject.com/).

To use Django with your Python eventsourcing applications:
* install the Python package `eventsourcing_django`
* add `'eventsourcing_django'` to your Django project's `INSTALLED_APPS` setting
* migrate your database for this Django app
* set the environment variable `PERSISTENCE_MODULE` to `'eventsourcing_django'`

See below for more information.


## Installation

Use pip to install the [stable distribution](https://pypi.org/project/eventsourcing_django/)
from the Python Package Index. Please note, it is recommended to
install Python packages into a Python virtual environment.

    $ pip install eventsourcing_django


## Django

If you are using Django 3.2 or later, add `'eventsourcing_django'`
to your Django project's `INSTALLED_APPS` setting.

    INSTALLED_APPS = [
        ...
        'eventsourcing_django',
    ]

If you are using Django 2.2, 3.0 or 3.1, please add
`'eventsourcing_django.apps.EventsourcingConfig'` to your Django
project's `INSTALLED_APPS` setting.

    INSTALLED_APPS = [
        ...
        'eventsourcing_django.apps.EventsourcingConfig',
    ]


To migrate your database, please run Django's `manage.py migrate` command.

    $ python manage.py migrate eventsourcing_django


## Event sourcing

Define aggregates and applications in the usual way.

```python
from eventsourcing.application import Application
from eventsourcing.domain import Aggregate, event
from uuid import uuid5, NAMESPACE_URL


class TrainingSchool(Application):
    def register(self, name):
        dog = Dog(name)
        self.save(dog)

    def add_trick(self, name, trick):
        dog = self.repository.get(Dog.create_id(name))
        dog.add_trick(trick)
        self.save(dog)

    def get_tricks(self, name):
        dog = self.repository.get(Dog.create_id(name))
        return dog.tricks


class Dog(Aggregate):
    @event('Registered')
    def __init__(self, name):
        self.name = name
        self.tricks = []

    @staticmethod
    def create_id(name):
        return uuid5(NAMESPACE_URL, f'/dogs/{name}')

    @event('TrickAdded')
    def add_trick(self, trick):
        self.tricks.append(trick)
```
Construct and use the application in the usual way.
Set `PERSISTENCE_MODULE` to `'eventsourcing_django'`
in the application's environment.
You may wish to construct the application object on a signal
when the Django project is "ready". You can use the `ready()`
method of the `AppConfig` class in the `apps.py` module of a
Django app.

```python
school = TrainingSchool(env={
    "PERSISTENCE_MODULE": "eventsourcing_django",
})
```

The application's methods may be called from Django views and forms.

```python
school.register('Fido')
school.add_trick('Fido', 'roll over')
school.add_trick('Fido', 'play dead')
tricks = school.get_tricks('Fido')
assert tricks == ['roll over', 'play dead']
```

For more information, please refer to the Python
[eventsourcing](https://github.com/johnbywater/eventsourcing) library
and the [Django](https://www.djangoproject.com/) project.


## Management Commands

The Django app `eventsourcing_django` ships with the following management commands.

### Synchronise Followers

Manually synchronise followers (i.e. `ProcessApplication` instances) with all of their
leaders, as defined in the `eventsourcing.system.System`'s pipes.

#### Usage

```shell
$ python manage.py sync_followers [-n] [-v {0,1,2,3}] [follower [follower ...]]
```

Where `follower` denotes the name of a follower to synchronize. Not specifying any means
synchronising *all followers* found in the system.

Relevant options:

  - `-n`, `--dry-run`: Load and process all unseen events for the selected followers,
    but roll back all changes at the end.
  - `-v {0,1,2,3}`, `--verbosity {0,1,2,3}`: Verbosity level; 0=minimal output, 1=normal
    output, 2=verbose output, 3=very verbose output.

For a full list of options, pass the `--help` flag to the command.

#### Examples

  - To synchronise all followers found in the runner:

      ```shell
      $ python manage.py sync_followers
      ```

  - To synchronise a single follower:

      ```shell
      $ python manage.py sync_followers TrainingSchool
      ```

The command supports the regular `-v/--verbosity` optional argument, as well as a
`-n/--dry-run` flag.

Note that running the command in dry-run mode *will* pull and process every new
event, though the changes will eventually be rolled back.

#### Error handling

Each selected follower should have its own chance at synchronisation. Therefore, the
command will catch some exceptions on a per-follower basis and continue with the
remaining followers.

The base Django exceptions that are caught are `EmptyResultSet`, `FieldDoesNotExist`,
`FieldError`, `MultipleObjectsReturned`, and `ObjectDoesNotExist`. The base exception
`EventSourcingError` from the `eventsourcing` library is also caught per follower.

### Configuration

This command needs to access a `eventsourcing.system.Runner` instance to query and act
on its followers. The runner's system is additionally the one defining the pipes between
leaders and followers.

The default behaviour, without additional configuration, is to inspect all installed
Django apps and look for an instance of `eventsourcing.system.Runner`. The attribute
name does not matter as long as it is public (i.e. not start with an underscore).

```python
# djangoproject/apps/my_es_app/apps.py
import eventsourcing.system
from django.apps import AppConfig


class MyEventSourcedAppConfig(AppConfig):
   name = "my_event_sourced_app"
   runner: eventsourcing.system.Runner

   def ready(self) -> None:
       self.runner = eventsourcing.system.SingleThreadedRunner(
           eventsourcing.system.System(...)
       )
```

This is usually enough unless you i) have multiple runners defined in one or more apps,
or ii) do not hold the runner(s) in Django apps. In which case, you should configure the
Django setting `EVENTSOURCING_RUNNER` in one of two ways:

1. Set `EVENTSOURCING_RUNNER` to an app name's attribute. This attribute must be a
   `eventsourcing.system.Runner` instance.

   ```python
   # djangoproject/settings.py
   ...
   EVENTSOURCING_RUNNER = "my_event_sourced_app.runner"
   ```

2. Set `EVENTSOURCING_RUNNER` to a fully qualified function name. This function will be
   called without arguments and should return a `eventsourcing.system.Runner` instance.

   ```python
   # djangoproject/settings.py
   ...
   EVENTSOURCING_RUNNER = "djangoproject.runner_utils.get_runner"
   ```
   ```python
   # djangoproject/runner_utils.py
   import eventsourcing.system


   def get_runner() -> eventsourcing.system.Runner:
      return ...
   ```

All runner classes shipped with the `eventsourcing` library are compatible.
