from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class MovimientoCaja(models.Model):
    class TipoMovimiento(models.TextChoices):
        ENTRADA = 'ENTRADA', 'Entrada'
        SALIDA = 'SALIDA', 'Salida'

    class Origen(models.TextChoices):
        VENTA_CONTADO = 'VENTA_CONTADO', 'Venta de contado'
        ABONO_FIADO = 'ABONO_FIADO', 'Abono a fiado'
        PRESTAMO_RECIBIDO = 'PRESTAMO_RECIBIDO', 'Préstamo recibido'
        COMPRA_CONTADO = 'COMPRA_CONTADO', 'Compra de contado'
        GASTO = 'GASTO', 'Gasto'
        PRESTAMO_OTORGADO = 'PRESTAMO_OTORGADO', 'Préstamo otorgado'
        PAGO_PRESTAMO = 'PAGO_PRESTAMO', 'Pago de préstamo recibido'
        AJUSTE = 'AJUSTE', 'Ajuste manual'

    tipo_movimiento = models.CharField(max_length=10, choices=TipoMovimiento.choices)
    origen = models.CharField(max_length=25, choices=Origen.choices)
    monto = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    saldo_resultante = models.IntegerField(editable=False)
    descripcion = models.CharField(max_length=255, blank=True, null=True)
    documento_referencia = models.CharField(max_length=100, blank=True, null=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='movimientos_caja'
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-creado_en', '-id']

    def __str__(self):
        return f'{self.get_tipo_movimiento_display()} - {self.get_origen_display()} - ${self.monto}'

    @classmethod
    def saldo_actual(cls):
        ultimo = cls.objects.order_by('-creado_en', '-id').first()
        return ultimo.saldo_resultante if ultimo else 0

    def save(self, *args, **kwargs):
        if self.pk is None:
            saldo_anterior = MovimientoCaja.saldo_actual()
            if self.tipo_movimiento == self.TipoMovimiento.ENTRADA:
                self.saldo_resultante = saldo_anterior + self.monto
            else:
                if self.monto > saldo_anterior:
                    raise ValueError(
                        f'Saldo insuficiente en caja. Disponible: ${saldo_anterior}, '
                        f'se intenta sacar: ${self.monto}.'
                    )
                self.saldo_resultante = saldo_anterior - self.monto
        super().save(*args, **kwargs)