from django.urls import path
from scans.views import (
    ScanListView,
    ScanSearchView,
    ScanDetailView,
    ScanEditView,
    import_scan_images,
    import_scans,
)


urlpatterns = [
    path('', ScanListView.as_view(), name='scan-list'),
    path('search/', ScanSearchView.as_view(), name='scan-search'),
    path('<int:pk>/', ScanDetailView.as_view(), name='scan-detail'),
    path('<int:pk>/edit/',
         ScanEditView.as_view(template_name="scans/scan_edit.html"),
         name='scan-edit'),
    path('import/', import_scans, name='scan-import'),
    path('import-images/', import_scan_images, name='import-scan-images'),
]
