from django.db import models
from django.db.models.deletion import SET_NULL
from users.models import User


class Contact(models.Model):
    user = models.ForeignKey(User, null=True, default=None, on_delete=SET_NULL)
    name = models.CharField(max_length=255)
    email = models.EmailField()
    subject = models.CharField(max_length=255)
    message = models.TextField()
    url = models.URLField()
