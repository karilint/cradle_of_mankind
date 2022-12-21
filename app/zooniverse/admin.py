from typing import Callable
from django.contrib import admin
from .models import (
    Retirement,
    Workflow,
    Classification,
    Annotation,
    Subject,
)

admin.site.register(Workflow)
admin.site.register(Classification)
admin.site.register(Annotation)
admin.site.register(Subject)
admin.site.register(Retirement)
