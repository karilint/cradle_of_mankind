from django.urls import path
from .views import *

urlpatterns = [
    path("import/", import_source_data_view, name="import-source-data"),
    path(
        "import/update-existing-source",
        update_existing_source,
        name="update-existing-source",
    ),
    path(
        "import/new/<int:stage>", import_new_source, name="import-new-source"
    ),
    path("manage/", manage_masters, name="manage-masters"),
    path(
        "create/<int:source_pk>/stage-<int:stage>",
        create_master,
        name="create-master",
    ),
    path("delete/<int:source_pk>", delete_master_view, name="delete-master"),
    path(
        "edit/<int:source_pk>/stage-<int:stage>",
        edit_master,
        name="edit-master",
    ),
    path("master-fields/", master_fields, name="master-fields"),
    path(
        "master-fields/edit/<int:master_field_pk>",
        master_field_edit,
        name="master-field-edit",
    ),
    path(
        "master-fields/delete/<int:master_field_pk>",
        master_field_delete,
        name="master-field-delete",
    ),
    path(
        "master-fields/edit/display-order",
        master_field_edit_display_order,
        name="master-field-edit-display-order",
    ),
    path("source-list/", source_list, name="source-list"),
    path("master-list/", master_list, name="master-list"),
    path(
        "master-list/view/<int:master_entity_pk>",
        master_entity_view,
        name="master-entity-view",
    ),
    path(
        "master-list/view/<int:master_entity_pk>/split/<int:source_entity_pk>",
        master_entity_split,
        name="master-entity-split",
    ),
    path(
        "master-list/view/<int:master_entity_pk>/edit/<int:source_entity_pk>",
        master_entity_choose_edit,
        name="master-entity-choose-edit",
    ),
    path(
        "master-list/view/<int:master_entity_pk>/edit/<int:source_entity_pk>/<int:master_field_pk>",
        master_entity_edit,
        name="master-entity-edit",
    ),
    path(
        "master-list/view/<int:master_entity_pk>/merge/<int:source_entity_pk>",
        master_entity_merge,
        name="master-entity-merge",
    ),
    path("", index, name="masterdata-index"),
    path("sources/view/<int:source_pk>", source_view, name="source-view"),
    path("export", export_masterdata, name="export"),
    path("export/view/<int:export_pk>", export_view, name="export-view"),
]
