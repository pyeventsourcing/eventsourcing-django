# Event Sourcing with Django

This package is a Django app that supports using the Python
[eventsourcing](https://github.com/pyeventsourcing/eventsourcing) library with the [Django ORM](https://www.djangoproject.com/).

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

Alternatively, add `eventsourcing_django` to your project's `pyproject.yaml`
or `requirements.txt` file and update your virtual environment accordingly.

## Event sourcing application

Define event-sourced aggregates and applications using the `Application` and
`Aggregate` classes from the `eventsourcing` package.

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

The event sourcing application can be developed and tested independently of Django.

Next, let's configure a Django project, and our event sourcing application, so
that events of the event sourcing application are stored in a Django database.

## Django project settings

Add `'eventsourcing_django'` to your Django project's `INSTALLED_APPS` setting.

    INSTALLED_APPS = [
        ...
        'eventsourcing_django',
    ]

This will make the Django models for storing events available in your Django project,
and allow Django to create tables in your database for storing events.

## Django database migration

Run Django's `manage.py migrate` command to create database tables for storing events.

    $ python manage.py migrate

Use the `--database` option to create tables in a non-default database. The database
alias must be a key in the `DATABASES` setting of your Django project.

    $ python manage.py migrate --database=postgres

Alternatively, after the Django framework has been set up for your project, you
can call Django's `call_command()` function to create the database tables.

```python
from django.core.management import call_command

call_command('migrate')
```

Use the `database` keyword argument to create tables in a non-default database.

```python
call_command('migrate', database='postgres')
```

To set up the Django framework for your Django project, `django.setup()` must have
been called after setting environment variable `DJANGO_SETTINGS_MODULE` to indicate the
settings module of your Django project. This is often done by a Django project's
`manage.py`, `wsgi.py`, and `asgi.py` files, and by tools that support Django users
such as test suite runners provided by IDEs that support Django. Django test suites
usually automatically create and migrate databases when tests are run.

## Event sourcing in Django

The event sourcing application can be configured to store events in the Django project's
database by setting the environment variable `PERSISTENCE_MODULE` to
`'eventsourcing_django'`. This step also depends on the Django framework having been
set up to for your Django project, but it doesn't depend on the database tables having
been created.

```python
training_school = TrainingSchool(
    env={'PERSISTENCE_MODULE': 'eventsourcing_django'},
)
```

Use the application environment variable `DJANGO_DB_ALIAS` to configure the application
to store events in a non-default Django project database. The value of `DJANGO_DB_ALIAS`
must correspond to one of the keys in the `DATABASES` setting of the Django project.

```python
training_school = TrainingSchool(
    env={
        'PERSISTENCE_MODULE': 'eventsourcing_django',
        'DJANGO_DB_ALIAS': 'postgres',
    }
)
```

You may wish to define your event sourcing application in a separate Django app,
and construct your event sourcing application in a Django `AppConfig` subclass
in its `apps.py` module.

```python
# In your apps.py file.
from django.apps import AppConfig

class TrainingSchoolConfig(AppConfig):
    name = '<django-project-name>.training_school'

    def ready(self):
        self.training_school = TrainingSchool(
            env={'PERSISTENCE_MODULE': 'eventsourcing_django'}
        )

```

You may also wish to centralize the definition of your event sourcing application's
environment variables in your Django project's settings module, and use this when
constructing the event sourcing application.

```python
# Create secret cipher key.
import os
from eventsourcing.cipher import AESCipher
os.environ['CIPHER_KEY'] = AESCipher.create_key(32)

# In your settings.py file.
import os

EVENT_SOURCING_APPLICATION = {
    'PERSISTENCE_MODULE': 'eventsourcing_django',
    'DJANGO_DB_ALIAS': 'postgres',
    'IS_SNAPSHOTTING_ENABLED': 'y',
    'COMPRESSOR_TOPIC': 'eventsourcing.compressor:ZlibCompressor',
    'CIPHER_TOPIC': 'eventsourcing.cipher:AESCipher',
    'CIPHER_KEY': os.environ['CIPHER_KEY'],
}

# In your apps.py file.
from django.apps import AppConfig
from django.conf import settings

class TrainingSchoolConfig(AppConfig):
    name = '<django-project-name>.training_school'

    def ready(self):
        self.training_school = TrainingSchool(env=settings.EVENT_SOURCING_APPLICATION)
```

The single instance of the event sourcing application can then be obtained in other
places, such as views, forms, management commands, and tests.

```python
from django.apps import apps

training_school = apps.get_app_config('training_school').training_school
```

The event sourcing application's methods can be called in views, forms,
management commands, and tests.

```python
training_school.register('Fido')

training_school.add_trick('Fido', 'roll over')
training_school.add_trick('Fido', 'play dead')

tricks = training_school.get_tricks('Fido')
assert tricks == ['roll over', 'play dead']
```

Events will be stored in the Django project's database, so long as the
database tables have been created before the event sourcing application
methods are called. If the database tables have not been created, an
`OperationalError` will be raised to indicate that the tables are not found.

## Summary

In summary, before constructing an event sourcing application with `eventsourcing_django`
as its persistence module, the Django framework must have been set up for a Django
project that has `'eventsourcing_django'` included in its `INSTALLED_APPS` setting.
And, before calling the methods of the event sourcing application, the Django project's
database must have been migrated.

For more information, please refer to the Python
[eventsourcing](https://github.com/johnbywater/eventsourcing) library
and the [Django](https://www.djangoproject.com/) project.


## Management commands

The `eventsourcing_django` package is a Django app which ships with the following
Django management commands. They are available in Django projects that have
`'eventsourcing_django'` included in their `INSTALLED_APPS` setting.

At the moment, there is only one management command: `sync_followers`.

The `sync_followers` management command helps users of the `eventsourcing.system`
module. Please refer to the `eventsourcing` package docs for more information
about the `eventsourcing.system` module.

### Synchronise followers

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
   name = 'my_event_sourced_app'
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
   EVENTSOURCING_RUNNER = 'my_event_sourced_app.runner'
   ```

2. Set `EVENTSOURCING_RUNNER` to a fully qualified function name. This function will be
   called without arguments and should return a `eventsourcing.system.Runner` instance.

   ```python
   # djangoproject/settings.py
   ...
   EVENTSOURCING_RUNNER = 'djangoproject.runner_utils.get_runner'
   ```
   ```python
   # djangoproject/runner_utils.py
   import eventsourcing.system


   def get_runner() -> eventsourcing.system.Runner:
      return ...
   ```

All runner classes shipped with the `eventsourcing` library are compatible.
