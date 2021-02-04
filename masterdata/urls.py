from django.urls import path
from .views import import_data, source_list

urlpatterns = [
    path('import/', import_data, name='import-source-data'),
    path('source-list/', source_list, name='source-list')
]
