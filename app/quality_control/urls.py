from django.urls import path
from quality_control.views import (
    quality_control_list,
    quality_control_check,
    summary_list,
    summary_check,
)


urlpatterns = [
    path("", quality_control_list, name="quality-control-list"),
    path(
        "<int:workflow_pk>/<int:scan_pk>/",
        quality_control_check,
        name="quality-control-check",
    ),
    path("summary", summary_list, name="summary-list"),
    path("summary/<int:scan_pk>/", summary_check, name="summary-check"),
]
