from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from .models import Scan


admin.site.register(Scan, SimpleHistoryAdmin)
