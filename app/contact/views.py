from django.contrib.auth.decorators import login_required
from django.contrib import messages
from users.models import User
from django.http.response import HttpResponseRedirect
from django.shortcuts import redirect
from django.core.mail import send_mail
from .models import Contact


@login_required
def contact_form(request):
    if request.method == "POST":
        contact = Contact()
        if request.user.is_authenticated:
            contact.user = request.user
        contact.name = request.POST.get('name')
        contact.email = request.POST.get('email')
        contact.subject = request.POST.get('subject')
        contact.message = request.POST.get('message')
        contact.url = request.POST.get('url')
        contact.save()
        send_email(contact)
        messages.info(
            request, "Your message has been received. Thank you for contacting us.")
        prev_url = request.POST.get('url', '/')
        return HttpResponseRedirect(prev_url)
    return redirect('index')


def send_email(contact):
    subject = f"CoH: Contact request from {contact.name} ({contact.id})"
    message = f"""A new contact request from Cradle of Humanity. It can also been seen at admin page (ID={contact.id}).

Contact information:
Name: {contact.name}
Email: {contact.email}
URL: {contact.url}

Feedback:
Subject: {contact.subject}
Message: {contact.message}"""

    recipient_list = User.objects.filter(
        receive_contact_email=True).values_list('email', flat=True)
    send_mail(subject, message, None, recipient_list)
