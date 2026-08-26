import requests
from django import forms
from django.conf import settings
from django.utils.html import format_html

TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


class TurnstileWidget(forms.Widget):
    template_name = None

    def render(self, name, value, attrs=None, renderer=None):
        return format_html(
            '<div class="cf-turnstile" data-sitekey="{}"></div>',
            settings.TURNSTILE_SITE_KEY,
        )

    def value_from_datadict(self, data, files, name):
        # token arrives under Cloudflare's field name, not django's name
        return data.get("cf-turnstile-response")


class TurnstileField(forms.CharField):
    widget = TurnstileWidget

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("label", "")
        kwargs.setdefault("required", True)
        super().__init__(*args, **kwargs)

    def validate(self, value):
        super().validate(value)
        try:
            response = requests.post(
                TURNSTILE_VERIFY_URL,
                data={
                    "secret": settings.TURNSTILE_SECRET_KEY,
                    "response": value,
                },
                timeout=5,
            )
            response.raise_for_status()
            result = response.json()
        except (requests.RequestException, ValueError):
            # fail closed
            raise forms.ValidationError(
                "CAPTCHA verification failed, please try again."
            )

        if not result.get("success"):
            raise forms.ValidationError(
                "CAPTCHA verification failed, please try again."
            )
