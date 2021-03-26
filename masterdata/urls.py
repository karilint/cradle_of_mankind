from django.urls import path
from .views import import_data, master_fields, master_list, source_list, edit_master, create_master

urlpatterns = [
    path('import/', import_data, name='import-source-data'),
    path('source-list/', source_list, name='source-list'),
    path('edit-master/', edit_master, name='edit-master'),
    path('create-master/<int:source_pk>', create_master, name='create-master'),
    path('master-fields/', master_fields, name='master-fields'),
    path('master-list/', master_list, name='master-list')
]
