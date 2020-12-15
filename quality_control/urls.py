from django.urls import path
from quality_control.views import (
    specimen_numbers_check, specimen_numbers_list,
)


urlpatterns = [
    path('specimen-numbers/', specimen_numbers_list,
         name='specimen-numbers'),
    path('specimen-numbers/<int:pk>/', specimen_numbers_check,
         name='specimen-numbers-check')
]
