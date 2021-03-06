from cradle_of_mankind.decorators import remember_last_query_params
from users.views import user_is_data_admin
from json import load
from django.contrib import messages

from django.db.models.query_utils import Q
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.urls import reverse
from .models import Scan
from .forms import ScanDataImportForm, ScanEditForm
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    UserPassesTestMixin,
)
from django.views.generic import (
    ListView,
    DetailView,
    UpdateView,
)


class ScanListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Scan
    template_name = 'scan_list.html'
    context_object_name = 'scans'
    paginate_by = 10

    def test_func(self):
        user = self.request.user
        return user.is_data_admin or user.is_editor


class ScanSearchView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Scan
    template_name = 'scans/scan_search.html'
    context_object_name = 'scans'
    paginate_by = 10

    def get_queryset(self):
        query = self.request.GET.get('query')
        type = self.request.GET.get('type')
        status = self.request.GET.get('status')
        if type == '':
            scan_list = Scan.objects.filter(
                Q(type__icontains=type),
                Q(status__icontains=status),
                Q(id__iexact=query) |
                Q(text__icontains=query)
            )
        else:
            scan_list = Scan.objects.filter(
                Q(type__iexact=type),
                Q(status__icontains=status),
                Q(id__iexact=query) |
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

    def test_func(self):
        user = self.request.user
        return user.is_data_admin or user.is_editor


class ScanDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Scan

    def test_func(self):
        user = self.request.user
        return user.is_data_admin or user.is_editor


class ScanEditView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Scan
    form_class = ScanEditForm
    context_object_name = 'scan'

    def get_success_url(self):
        return reverse('scan-detail', kwargs={'pk': self.object.pk})

    def test_func(self):
        user = self.request.user
        return user.is_data_admin or user.is_editor


@login_required
@user_passes_test(user_is_data_admin)
def import_scans(request):
    if request.method == 'POST':
        form = ScanDataImportForm(request.POST, request.FILES)
        if form.is_valid():
            save_json_to_database(request.FILES['file'], request.user)
            messages.success(request, "Upload succesful!")
            return redirect('index')
    else:
        form = ScanDataImportForm()
    return render(request, 'scans/scan_import.html', {'form': form})


def save_json_to_database(json_file, user):
    data = load(json_file)
    data = data['rows']
    for scan in data:
        try:
            s = Scan.objects.get(id=scan['id'])
        except ObjectDoesNotExist:
            s = Scan()
            s.id = scan['id']
            s.type = scan['card_type']
            s.status = scan['STG_STATUS']
            s.image = f"scans/{s.id}.jpg"
            if not scan['txt']:
                s.text = ''
            else:
                s.text = scan['txt']
            s.created_by = user
            s.modified_by = user
            s.save()
        print(f"Scan (id: {s.id}) saved")
