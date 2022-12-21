from django.urls import path
from .views import import_data

urlpatterns = [path("import/", import_data, name="import-data")]
