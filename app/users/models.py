from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    is_editor = models.BooleanField(default=False)
    is_data_admin = models.BooleanField(default=False)
    receive_contact_email = models.BooleanField(default=False)

    def get_access_level(self):
        if self.is_data_admin:
            return 4
        if self.is_editor:
            return 3
        return 2
