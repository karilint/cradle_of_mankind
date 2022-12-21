from django.urls import path
from .views import task_list, task_view, task_terminate

urlpatterns = [
    path("list", task_list, name="task-list"),
    path("view/<str:task_id>", task_view, name="task-view"),
    path("terminate/<str:task_id>", task_terminate, name="task-terminate"),
]
