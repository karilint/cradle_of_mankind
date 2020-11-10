from users.forms import UserSignUpForm, EditorSignUpForm, DataAdminSignUpForm
from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect


def index(request):
    return render(request, 'index.html')


def signup(request):
    return render(request, 'users/signup.html')


def normal_signup(request):
    if request.method == 'POST':
        form = UserSignUpForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            raw_password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=raw_password)
            login(request, user)
            return redirect('index')
    else:
        form = UserSignUpForm()
    return render(request, 'users/normal_signup.html', {'form': form})


def editor_signup(request):
    if request.method == 'POST':
        form = EditorSignUpForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            raw_password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=raw_password)
            login(request, user)
            return redirect('index')
    else:
        form = EditorSignUpForm()
    return render(request, 'users/editor_signup.html', {'form': form})


def data_admin_signup(request):
    if request.method == 'POST':
        form = DataAdminSignUpForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            raw_password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=raw_password)
            login(request, user)
            return redirect('index')
    else:
        form = DataAdminSignUpForm()
    return render(request, 'users/data_admin_signup.html', {'form': form})
