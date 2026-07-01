from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    class Rol(models.TextChoices):
        DUENO = 'DUENO', 'Dueño'
        EMPLEADO = 'EMPLEADO', 'Empleado'

    rol = models.CharField(
        max_length=10,
        choices=Rol.choices,
        default=Rol.EMPLEADO,
    )

    def __str__(self):
        return f'{self.username} ({self.get_rol_display()})'