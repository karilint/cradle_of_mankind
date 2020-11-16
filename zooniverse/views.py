import os
from django.conf import settings
from django.shortcuts import render
from django.contrib.auth.decorators import user_passes_test
from .forms import DataImportForm


def user_is_data_admin(user):
    return user.is_data_admin


def save_uploaded_file(f):
    try:
        os.mkdir(os.path.join(settings.MEDIA_ROOT, 'imports'))
    except:
        pass

    path_to_file = os.path.join(settings.MEDIA_ROOT, 'imports', f.name)
    with open(path_to_file, 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)


@user_passes_test(user_is_data_admin)
def import_data(request):
    if request.method == 'POST':
        form = DataImportForm(request.POST, request.FILES)
        if form.is_valid():
            f = request.FILES['file']
            save_uploaded_file(f)
    else:
        form = DataImportForm()
    return render(request, 'zooniverse/zooniverse_import.html', {'form': form})
