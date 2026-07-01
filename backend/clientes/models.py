from django.db import models


class Cliente(models.Model):
    NOMBRE_CLIENTE_FINAL = 'Cliente Final'

    nombre = models.CharField(max_length=150, unique=True)
    numero_documento = models.CharField(max_length=30, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    direccion = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    es_generico = models.BooleanField(default=False)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['nombre']
        constraints = [
            models.UniqueConstraint(
                fields=['es_generico'],
                condition=models.Q(es_generico=True),
                name='unico_cliente_generico',
            )
        ]

    def __str__(self):
        return self.nombre

    def puede_usarse_en_credito(self):
        """El cliente genérico (Cliente Final) no puede usarse en fiados ni préstamos."""
        return not self.es_generico

    @classmethod
    def get_cliente_final(cls):
        cliente, _ = cls.objects.get_or_create(
            es_generico=True,
            defaults={'nombre': cls.NOMBRE_CLIENTE_FINAL},
        )
        return cliente