from django.urls import path
from .views import master_data_edit, master_field_delete, master_field_edit, import_data, master_field_edit_display_order, master_fields, master_list, source_list, edit_master, create_master

urlpatterns = [
    path('import/', import_data, name='import-source-data'),
    path('source-list/', source_list, name='source-list'),
    path('edit-master/', edit_master, name='edit-master'),
    path('create-master/<int:source_pk>', create_master, name='create-master'),
    path('master-fields/', master_fields, name='master-fields'),
    path('master-fields/edit/<int:master_field_pk>',
         master_field_edit, name='master-field-edit'),
    path('master-fields/delete/<int:master_field_pk>',
         master_field_delete, name='master-field-delete'),
    path('master-fields/edit/display-order',
         master_field_edit_display_order, name='master-field-edit-display-order'),
    path('master-list/', master_list, name='master-list'),
    path('master-list/edit/<int:master_data_pk>',
         master_data_edit, name='master-data-edit')
]
