from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    email = models.EmailField("email", unique=True)
    phone = models.CharField("телефон", max_length=20, blank=True)
    city = models.CharField("город", max_length=100, blank=True)
    avatar = models.ImageField("аватар", upload_to="avatars/", blank=True, null=True)
    bio = models.TextField("о себе", blank=True)

    class Meta:
        verbose_name = "пользователь"
        verbose_name_plural = "пользователи"

    def __str__(self):
        return self.username
