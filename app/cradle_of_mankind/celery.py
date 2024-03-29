import os

from celery import Celery, signals

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cradle_of_mankind.settings")

app = Celery("cradle_of_mankind")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")


@signals.setup_logging.connect
def on_celery_setup_logging(**kwargs):
    pass


# Load task modules from all registered Django apps.
app.autodiscover_tasks()
