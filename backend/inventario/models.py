from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class MovimientoStock(models.Model):
    class TipoMovimiento(models.TextChoices):
        ENTRADA_COMPRA = 'ENTRADA_COMPRA', 'Entrada por compra'
        SALIDA_VENTA_DETAL = 'SALIDA_VENTA_DETAL', 'Salida por venta al detal'
        SALIDA_VENTA_MAYORISTA = 'SALIDA_VENTA_MAYORISTA', 'Salida por venta al mayor'
        SALIDA_AUTOCONSUMO = 'SALIDA_AUTOCONSUMO', 'Salida por autoconsumo (receta)'
        AJUSTE_POSITIVO = 'AJUSTE_POSITIVO', 'Ajuste positivo'
        AJUSTE_NEGATIVO = 'AJUSTE_NEGATIVO', 'Ajuste negativo'

    ENTRADAS = {TipoMovimiento.ENTRADA_COMPRA, TipoMovimiento.AJUSTE_POSITIVO}
    SALIDAS = {
        TipoMovimiento.SALIDA_VENTA_DETAL,
        TipoMovimiento.SALIDA_VENTA_MAYORISTA,
        TipoMovimiento.SALIDA_AUTOCONSUMO,
        TipoMovimiento.AJUSTE_NEGATIVO,
    }

    producto = models.ForeignKey(
        'productos.Producto', on_delete=models.PROTECT, related_name='movimientos'
    )
    tipo_movimiento = models.CharField(max_length=25, choices=TipoMovimiento.choices)
    cantidad = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    stock_resultante = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    motivo = models.CharField(max_length=255, blank=True, null=True)
    documento_referencia = models.CharField(max_length=100, blank=True, null=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='movimientos_stock'
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-creado_en']

    def __str__(self):
        return f'{self.producto} | {self.get_tipo_movimiento_display()} | {self.cantidad}'

    def save(self, *args, **kwargs):
        if self.pk is None:
            producto = self.producto

            if self.tipo_movimiento in self.ENTRADAS:
                producto.stock_actual += self.cantidad
            elif self.tipo_movimiento in self.SALIDAS:
                if self.cantidad > producto.stock_actual:
                    raise ValueError(
                        f'Stock insuficiente en "{producto.nombre}". '
                        f'Disponible: {producto.stock_actual}, solicitado: {self.cantidad}.'
                    )
                producto.stock_actual -= self.cantidad
            else:
                raise ValueError('Tipo de movimiento no reconocido.')

            self.stock_resultante = producto.stock_actual
            producto.save(update_fields=['stock_actual'])

        super().save(*args, **kwargs)