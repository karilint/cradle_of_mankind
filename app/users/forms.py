from allauth.account.forms import SignupForm, ResetPasswordForm
from allauth.core import ratelimit
from allauth.socialaccount.forms import SignupForm as SocialSignupForm
from django import forms
from users.models import User
from django.contrib.auth.forms import UserCreationForm

from .captcha import TurnstileField


class CaptchaSignupForm(SignupForm):
    captcha = TurnstileField()


class CaptchaResetPasswordForm(ResetPasswordForm):
    captcha = TurnstileField()


class CaptchaSocialSignupForm(SocialSignupForm):
    captcha = TurnstileField()

    def try_save(self, request):
        # allauth doesn't rate limit this view itself
        if not ratelimit.consume(request, action="social_signup"):
            return None, ratelimit.respond_429(request)
        return super().try_save(request)


class UserSignUpForm(UserCreationForm):
    first_name = forms.CharField(max_length=50)
    last_name = forms.CharField(max_length=50)
    email = forms.EmailField()

    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "password1",
            "password2",
        ]


class EditorSignUpForm(UserCreationForm):
    first_name = forms.CharField(max_length=50)
    last_name = forms.CharField(max_length=50)
    email = forms.EmailField()

    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "password1",
            "password2",
        ]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_editor = True
        if commit:
            user.save()
        return user


class DataAdminSignUpForm(UserCreationForm):
    first_name = forms.CharField(max_length=50)
    last_name = forms.CharField(max_length=50)
    email = forms.EmailField()

    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "password1",
            "password2",
        ]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_data_admin = True
        if commit:
            user.save()
        return user
