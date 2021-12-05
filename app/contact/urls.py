
from contact.views import contact_form
from django.urls import path


urlpatterns = [
    path('contact-form/', contact_form, name='contact_form'),
]
