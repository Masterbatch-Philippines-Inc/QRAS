from django.db import models


class Department(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'access_departments'


class Position(models.Model):
    title      = models.CharField(max_length=100)
    is_active  = models.BooleanField(default=True)
    department = models.ForeignKey(Department, on_delete=models.PROTECT, null=True)

    def __str__(self):
        return self.title

    class Meta:
        db_table = 'access_positions'



class Role(models.Model):
    name        = models.CharField(max_length=100, unique=True)
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Module(models.Model):
    name    = models.CharField(max_length=100)
    code    = models.CharField(max_length=100, unique=True)
    order   = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.name


class RolePermission(models.Model):
    role        = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='permissions')
    module      = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='permissions')
    can_create  = models.BooleanField(default=False)
    can_read    = models.BooleanField(default=False)
    can_update  = models.BooleanField(default=False)
    can_delete  = models.BooleanField(default=False)

    class Meta:
        unique_together = ('role', 'module')

    def __str__(self):
        return f"{self.role.name} — {self.module.name}"