from django.db import models
from apps.qras.models.access import Role, Department
from apps.qras.models.employee  import Employee
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    role          = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True, related_name='users')
    department    = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='system_users')
    employee      = models.OneToOneField(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name='system_user')
    first_name    = models.CharField(max_length=100)
    last_name     = models.CharField(max_length=100)
    email         = models.EmailField(unique=True)
    is_online     = models.BooleanField(default=False)
    must_change_password = models.BooleanField(default=False)
    groups               = models.ManyToManyField('auth.Group', related_name='qras_user_set', blank=True)
    user_permissions     = models.ManyToManyField('auth.Permission', related_name='qras_user_set', blank=True)
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}".strip() or self.username