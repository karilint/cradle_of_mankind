from typing import Callable
from django.contrib import admin
from .models import (
    Import,
    Retirement,
    Workflow,
    Classification,
    Annotation,
    Subject,
)

admin.site.register(Import)
admin.site.register(Workflow)
admin.site.register(Classification)
admin.site.register(Annotation)
admin.site.register(Subject)
admin.site.register(Retirement)
