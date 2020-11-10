from django.db.models.query_utils import Q
from django.shortcuts import render
from django.urls import reverse
from .models import Scan
from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    UserPassesTestMixin,
)
from django.views.generic import (
    ListView,
    DetailView,
    UpdateView,
)


class ScanListView(LoginRequiredMixin, ListView):
    model = Scan
    template_name = 'scan_list.html'
    context_object_name = 'scans'
    paginate_by = 10


class ScanSearchView(LoginRequiredMixin, ListView):
    model = Scan
    template_name = 'scans/scan_search.html'
    context_object_name = 'scans'
    paginate_by = 10

    def get_queryset(self):
        query = self.request.GET.get('query')
        type = self.request.GET.get('type')
        status = self.request.GET.get('status')
        scan_list = Scan.objects.filter(
            Q(type__icontains=type),
            Q(status__icontains=status),
            Q(id__icontains=query) |
            Q(text__icontains=query)
        )
        return scan_list

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('query')
        context['type'] = self.request.GET.get('type')
        context['status'] = self.request.GET.get('status')
        context['whole_query'] = f"?query={context['query']}&type={context['type']}&status={context['status']}"
        return context


class ScanDetailView(LoginRequiredMixin, DetailView):
    model = Scan


class ScanEditView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Scan
    context_object_name = 'scan'
    fields = ['type', 'status', 'text']

    def get_success_url(self):
        return reverse('scan-detail', kwargs={'pk': self.object.pk})

    def test_func(self):
        user = self.request.user
        if user.is_editor or user.is_data_admin:
            return True
        return False
