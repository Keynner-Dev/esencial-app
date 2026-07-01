from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.signals import post_delete, pre_delete
from django.dispatch import receiver

from inventario.models import MovimientoStock


class Proveedor(models.Model):
    nombre = models.CharField(max_length=150, unique=True)
    numero_documento = models.CharField(max_length=30, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    direccion = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Factura(models.Model):
    proveedor = models.ForeignKey(
        Proveedor, on_delete=models.PROTECT, related_name='facturas'
    )
    numero_factura = models.CharField(max_length=50)
    fecha = models.DateField()
    total = models.PositiveIntegerField(default=0, editable=False)
    observaciones = models.CharField(max_length=255, blank=True, null=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='facturas_registradas'
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha', '-creado_en']
        constraints = [
            models.UniqueConstraint(
                fields=['proveedor', 'numero_factura'],
                name='unica_factura_por_proveedor',
            )
        ]

    def __str__(self):
        return f'Factura {self.numero_factura} - {self.proveedor}'

    def recalcular_total(self):
        total = self.detalles.aggregate(suma=models.Sum('subtotal'))['suma'] or 0
        self.total = total
        self.save(update_fields=['total'])


class DetalleFactura(models.Model):
    factura = models.ForeignKey(Factura, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(
        'productos.Producto', on_delete=models.PROTECT, related_name='detalles_factura'
    )
    cantidad = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    costo_unitario = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    subtotal = models.PositiveIntegerField(editable=False)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f'{self.producto} x {self.cantidad} - Factura {self.factura.numero_factura}'

    def save(self, *args, **kwargs):
        if self.pk:
            original = DetalleFactura.objects.get(pk=self.pk)
            campos_criticos_cambiaron = (
                original.cantidad != self.cantidad
                or original.costo_unitario != self.costo_unitario
                or original.producto_id != self.producto_id
            )
            if campos_criticos_cambiaron:
                raise ValueError(
                    'No se puede modificar cantidad, costo o producto de un detalle '
                    'ya guardado. Elimínalo y créalo de nuevo si necesitas corregirlo.'
                )

        es_nuevo = self.pk is None
        self.subtotal = round(self.cantidad * self.costo_unitario)
        super().save(*args, **kwargs)

        if es_nuevo:
            MovimientoStock.objects.create(
                producto=self.producto,
                tipo_movimiento=MovimientoStock.TipoMovimiento.ENTRADA_COMPRA,
                cantidad=self.cantidad,
                documento_referencia=f'Factura #{self.factura.numero_factura}',
                usuario=self.factura.usuario,
            )

            self.producto.costo_compra = self.costo_unitario
            self.producto.save(update_fields=['costo_compra'])

            self.factura.recalcular_total()


@receiver(pre_delete, sender=DetalleFactura)
def revertir_stock_al_eliminar_detalle(sender, instance, **kwargs):
    """
    Antes de borrar un detalle de factura, revierte el stock que había entrado.
    Si el producto ya fue vendido y no hay suficiente stock para revertir,
    MovimientoStock lanza un error y la eliminación se cancela (transacción atómica).
    """
    MovimientoStock.objects.create(
        producto=instance.producto,
        tipo_movimiento=MovimientoStock.TipoMovimiento.AJUSTE_NEGATIVO,
        cantidad=instance.cantidad,
        motivo=f'Reversión por eliminación de detalle en Factura #{instance.factura.numero_factura}',
        documento_referencia=f'Factura #{instance.factura.numero_factura}',
        usuario=instance.factura.usuario,
    )


@receiver(post_delete, sender=DetalleFactura)
def recalcular_total_al_eliminar_detalle(sender, instance, **kwargs):
    """
    Después de borrar el detalle, recalcula el total de la factura.
    Si la factura completa también se está borrando (cascada), esto no falla:
    Django borra los hijos antes que el padre, así que la factura aún existe
    en este punto.
    """
    try:
        instance.factura.recalcular_total()
    except Factura.DoesNotExist:
        pass