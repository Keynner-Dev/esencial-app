from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.signals import pre_delete, post_delete
from django.dispatch import receiver

from clientes.models import Cliente
from productos.models import Producto
from inventario.models import MovimientoStock


class Venta(models.Model):
    class TipoVenta(models.TextChoices):
        DETAL = 'DETAL', 'Al detal'
        MAYORISTA = 'MAYORISTA', 'Al por mayor'

    class FormaPago(models.TextChoices):
        CONTADO = 'CONTADO', 'Contado'
        CREDITO = 'CREDITO', 'Fiado / Crédito'

    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='ventas')
    tipo_venta = models.CharField(max_length=10, choices=TipoVenta.choices)
    forma_pago = models.CharField(max_length=10, choices=FormaPago.choices)
    fecha = models.DateField()
    total = models.PositiveIntegerField(default=0, editable=False)
    pagada_en_caja = models.BooleanField(default=False, editable=False)
    observaciones = models.CharField(max_length=255, blank=True, null=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='ventas_registradas'
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha', '-creado_en']

    def __str__(self):
        return f'Venta #{self.pk} - {self.cliente} - {self.fecha}'

    def clean(self):
        if self.forma_pago == self.FormaPago.CREDITO and not self.cliente.puede_usarse_en_credito():
            raise ValueError(
                'El cliente "Cliente Final" no puede usarse en ventas a crédito. '
                'Selecciona o crea un cliente real.'
            )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def recalcular_total(self):
        total_productos = self.items_producto.aggregate(suma=models.Sum('subtotal'))['suma'] or 0
        total_perfumes = self.items_perfume.aggregate(suma=models.Sum('subtotal'))['suma'] or 0
        self.total = total_productos + total_perfumes
        self.save(update_fields=['total'])

    def registrar_pago_caja(self):
        """
        Se llama UNA SOLA VEZ, después de haber creado todos los items de la venta
        (esto lo dispara la vista de la API, no el usuario manualmente).
        Si la venta es a crédito o ya se registró antes, no hace nada.
        """
        if self.forma_pago != self.FormaPago.CONTADO or self.pagada_en_caja or self.total == 0:
            return

        from caja.models import MovimientoCaja
        MovimientoCaja.objects.create(
            tipo_movimiento=MovimientoCaja.TipoMovimiento.ENTRADA,
            origen=MovimientoCaja.Origen.VENTA_CONTADO,
            monto=self.total,
            documento_referencia=f'Venta #{self.pk}',
            usuario=self.usuario,
        )
        self.pagada_en_caja = True
        self.save(update_fields=['pagada_en_caja'])
        
        def registrar_fiado(self):
            """
            Se llama UNA SOLA VEZ, después de haber creado todos los items de la venta,
            solo si la venta es a crédito. Crea el registro de Fiado correspondiente.
            """
            if self.forma_pago != self.FormaPago.CREDITO or self.total == 0:
                return

            from finanzas.models import Fiado
            Fiado.crear_desde_venta(self)


class DetalleVentaProducto(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='items_producto')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name='ventas_detalle')
    cantidad = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    precio_unitario = models.PositiveIntegerField()
    costo_unitario = models.PositiveIntegerField(editable=False)
    subtotal = models.PositiveIntegerField(editable=False)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f'{self.producto} x {self.cantidad} - Venta #{self.venta_id}'

    def save(self, *args, **kwargs):
        if self.venta.tipo_venta == Venta.TipoVenta.MAYORISTA and not self.producto.disponible_mayorista:
            raise ValueError(
                f'"{self.producto.nombre}" no está habilitado para venta al por mayor.'
            )

        es_nuevo = self.pk is None
        if es_nuevo:
            self.costo_unitario = self.producto.costo_compra
        self.subtotal = round(self.cantidad * self.precio_unitario)
        super().save(*args, **kwargs)

        if es_nuevo:
            tipo_mov = (
                MovimientoStock.TipoMovimiento.SALIDA_VENTA_MAYORISTA
                if self.venta.tipo_venta == Venta.TipoVenta.MAYORISTA
                else MovimientoStock.TipoMovimiento.SALIDA_VENTA_DETAL
            )
            MovimientoStock.objects.create(
                producto=self.producto,
                tipo_movimiento=tipo_mov,
                cantidad=self.cantidad,
                documento_referencia=f'Venta #{self.venta_id}',
                usuario=self.venta.usuario,
            )
            self.venta.recalcular_total()


class DetalleVentaPerfume(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='items_perfume')
    esencia = models.ForeignKey(
        Producto, on_delete=models.PROTECT, related_name='ventas_esencia',
        limit_choices_to={'subtipo_insumo': Producto.SubtipoInsumo.ESENCIA},
    )
    gramos_esencia = models.PositiveIntegerField()
    envase = models.ForeignKey(
        Producto, on_delete=models.PROTECT, related_name='ventas_envase',
        limit_choices_to={'subtipo_insumo': Producto.SubtipoInsumo.ENVASE},
    )
    gramos_combo_extra = models.PositiveIntegerField(default=0)
    valor_combo_extra = models.PositiveIntegerField(default=0)
    valor_preparacion = models.PositiveIntegerField(default=0)
    cantidad = models.PositiveIntegerField(default=1)

    costo_unitario = models.PositiveIntegerField(editable=False)
    precio_venta = models.PositiveIntegerField(editable=False)
    subtotal = models.PositiveIntegerField(editable=False)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f'{self.esencia} en {self.envase} - Venta #{self.venta_id}'

    def save(self, *args, **kwargs):
        if self.venta.tipo_venta == Venta.TipoVenta.MAYORISTA:
            if not self.esencia.disponible_mayorista or not self.envase.disponible_mayorista:
                raise ValueError(
                    'La esencia o el envase seleccionados no están habilitados '
                    'para venta al por mayor.'
                )

        es_nuevo = self.pk is None

        gramos_totales = self.gramos_esencia + self.gramos_combo_extra
        costo_esencia = gramos_totales * self.esencia.costo_compra
        costo_envase = self.envase.costo_compra
        self.costo_unitario = costo_esencia + costo_envase

        self.precio_venta = self.costo_unitario + self.valor_combo_extra + self.valor_preparacion
        self.subtotal = self.precio_venta * self.cantidad

        super().save(*args, **kwargs)

        if es_nuevo:
            tipo_mov = (
                MovimientoStock.TipoMovimiento.SALIDA_VENTA_MAYORISTA
                if self.venta.tipo_venta == Venta.TipoVenta.MAYORISTA
                else MovimientoStock.TipoMovimiento.SALIDA_VENTA_DETAL
            )
            MovimientoStock.objects.create(
                producto=self.esencia,
                tipo_movimiento=tipo_mov,
                cantidad=Decimal(gramos_totales * self.cantidad),
                documento_referencia=f'Venta #{self.venta_id} (perfume armado)',
                usuario=self.venta.usuario,
            )
            MovimientoStock.objects.create(
                producto=self.envase,
                tipo_movimiento=tipo_mov,
                cantidad=Decimal(self.cantidad),
                documento_referencia=f'Venta #{self.venta_id} (perfume armado)',
                usuario=self.venta.usuario,
            )
            self.venta.recalcular_total()


@receiver(pre_delete, sender=DetalleVentaProducto)
def revertir_stock_producto(sender, instance, **kwargs):
    MovimientoStock.objects.create(
        producto=instance.producto,
        tipo_movimiento=MovimientoStock.TipoMovimiento.AJUSTE_POSITIVO,
        cantidad=instance.cantidad,
        motivo=f'Reversión por eliminación de línea en Venta #{instance.venta_id}',
        documento_referencia=f'Venta #{instance.venta_id}',
        usuario=instance.venta.usuario,
    )


@receiver(post_delete, sender=DetalleVentaProducto)
def recalcular_total_tras_borrar_producto(sender, instance, **kwargs):
    try:
        instance.venta.recalcular_total()
    except Venta.DoesNotExist:
        pass


@receiver(pre_delete, sender=DetalleVentaPerfume)
def revertir_stock_perfume(sender, instance, **kwargs):
    gramos_totales = instance.gramos_esencia + instance.gramos_combo_extra
    MovimientoStock.objects.create(
        producto=instance.esencia,
        tipo_movimiento=MovimientoStock.TipoMovimiento.AJUSTE_POSITIVO,
        cantidad=Decimal(gramos_totales * instance.cantidad),
        motivo=f'Reversión por eliminación de línea en Venta #{instance.venta_id}',
        documento_referencia=f'Venta #{instance.venta_id}',
        usuario=instance.venta.usuario,
    )
    MovimientoStock.objects.create(
        producto=instance.envase,
        tipo_movimiento=MovimientoStock.TipoMovimiento.AJUSTE_POSITIVO,
        cantidad=Decimal(instance.cantidad),
        motivo=f'Reversión por eliminación de línea en Venta #{instance.venta_id}',
        documento_referencia=f'Venta #{instance.venta_id}',
        usuario=instance.venta.usuario,
    )


@receiver(post_delete, sender=DetalleVentaPerfume)
def recalcular_total_tras_borrar_perfume(sender, instance, **kwargs):
    try:
        instance.venta.recalcular_total()
    except Venta.DoesNotExist:
        pass