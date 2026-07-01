from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from clientes.models import Cliente
from ventas.models import Venta
from caja.models import MovimientoCaja


class Fiado(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = 'PENDIENTE', 'Pendiente'
        PAGADO = 'PAGADO', 'Pagado'

    venta = models.OneToOneField(Venta, on_delete=models.CASCADE, related_name='fiado')
    monto_total = models.PositiveIntegerField(editable=False)
    saldo_pendiente = models.PositiveIntegerField(editable=False)
    estado = models.CharField(
        max_length=10, choices=Estado.choices, default=Estado.PENDIENTE, editable=False
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-creado_en']

    def __str__(self):
        return f'Fiado - Venta #{self.venta_id} - {self.venta.cliente} - saldo ${self.saldo_pendiente}'

    @classmethod
    def crear_desde_venta(cls, venta):
        if hasattr(venta, 'fiado'):
            return venta.fiado
        return cls.objects.create(
            venta=venta,
            monto_total=venta.total,
            saldo_pendiente=venta.total,
        )


class AbonoFiado(models.Model):
    fiado = models.ForeignKey(Fiado, on_delete=models.PROTECT, related_name='abonos')
    monto = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    fecha = models.DateField()
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='abonos_fiado'
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha', '-creado_en']

    def __str__(self):
        return f'Abono ${self.monto} - Fiado #{self.fiado_id}'

    def save(self, *args, **kwargs):
        es_nuevo = self.pk is None
        if es_nuevo and self.monto > self.fiado.saldo_pendiente:
            raise ValueError(
                f'El abono (${self.monto}) supera el saldo pendiente '
                f'(${self.fiado.saldo_pendiente}).'
            )
        super().save(*args, **kwargs)

        if es_nuevo:
            self.fiado.saldo_pendiente -= self.monto
            self.fiado.estado = (
                Fiado.Estado.PAGADO if self.fiado.saldo_pendiente == 0 else Fiado.Estado.PENDIENTE
            )
            self.fiado.save(update_fields=['saldo_pendiente', 'estado'])

            MovimientoCaja.objects.create(
                tipo_movimiento=MovimientoCaja.TipoMovimiento.ENTRADA,
                origen=MovimientoCaja.Origen.ABONO_FIADO,
                monto=self.monto,
                documento_referencia=f'Fiado #{self.fiado_id} (Venta #{self.fiado.venta_id})',
                usuario=self.usuario,
            )


class Prestamo(models.Model):
    class Direccion(models.TextChoices):
        OTORGADO = 'OTORGADO', 'Otorgado (Esencial le presta a alguien)'
        RECIBIDO = 'RECIBIDO', 'Recibido (alguien le presta a Esencial)'

    class Estado(models.TextChoices):
        ACTIVO = 'ACTIVO', 'Activo'
        PAGADO = 'PAGADO', 'Pagado'

    direccion = models.CharField(max_length=10, choices=Direccion.choices)
    persona = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='prestamos')
    monto_capital = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    tasa_interes = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text='Porcentaje de interés total acordado (ej. 10 = 10%). Déjalo en 0 si no aplica.',
    )
    monto_total_a_pagar = models.PositiveIntegerField(editable=False)
    saldo_pendiente = models.PositiveIntegerField(editable=False)
    estado = models.CharField(
        max_length=10, choices=Estado.choices, default=Estado.ACTIVO, editable=False
    )
    fecha = models.DateField()
    observaciones = models.CharField(max_length=255, blank=True, null=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='prestamos_registrados'
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha', '-creado_en']

    def __str__(self):
        return f'Préstamo {self.get_direccion_display()} - {self.persona} - ${self.monto_total_a_pagar}'

    def clean(self):
        if not self.persona.puede_usarse_en_credito():
            raise ValueError(
                'El "Cliente Final" no puede usarse en préstamos. Selecciona una persona real.'
            )

    def save(self, *args, **kwargs):
        self.clean()
        es_nuevo = self.pk is None
        if es_nuevo:
            interes = round(self.monto_capital * (self.tasa_interes / 100))
            self.monto_total_a_pagar = self.monto_capital + interes
            self.saldo_pendiente = self.monto_total_a_pagar
        super().save(*args, **kwargs)

        if es_nuevo:
            if self.direccion == self.Direccion.OTORGADO:
                MovimientoCaja.objects.create(
                    tipo_movimiento=MovimientoCaja.TipoMovimiento.SALIDA,
                    origen=MovimientoCaja.Origen.PRESTAMO_OTORGADO,
                    monto=self.monto_capital,
                    documento_referencia=f'Préstamo #{self.pk}',
                    usuario=self.usuario,
                )
            else:
                MovimientoCaja.objects.create(
                    tipo_movimiento=MovimientoCaja.TipoMovimiento.ENTRADA,
                    origen=MovimientoCaja.Origen.PRESTAMO_RECIBIDO,
                    monto=self.monto_capital,
                    documento_referencia=f'Préstamo #{self.pk}',
                    usuario=self.usuario,
                )


class AbonoPrestamo(models.Model):
    prestamo = models.ForeignKey(Prestamo, on_delete=models.PROTECT, related_name='abonos')
    monto = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    fecha = models.DateField()
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='abonos_prestamo'
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha', '-creado_en']

    def __str__(self):
        return f'Abono ${self.monto} - Préstamo #{self.prestamo_id}'

    def save(self, *args, **kwargs):
        es_nuevo = self.pk is None
        if es_nuevo and self.monto > self.prestamo.saldo_pendiente:
            raise ValueError(
                f'El abono (${self.monto}) supera el saldo pendiente '
                f'(${self.prestamo.saldo_pendiente}).'
            )
        super().save(*args, **kwargs)

        if es_nuevo:
            self.prestamo.saldo_pendiente -= self.monto
            self.prestamo.estado = (
                Prestamo.Estado.PAGADO if self.prestamo.saldo_pendiente == 0
                else Prestamo.Estado.ACTIVO
            )
            self.prestamo.save(update_fields=['saldo_pendiente', 'estado'])

            if self.prestamo.direccion == Prestamo.Direccion.OTORGADO:
                # Nos están devolviendo un préstamo que otorgamos → entra plata a caja
                MovimientoCaja.objects.create(
                    tipo_movimiento=MovimientoCaja.TipoMovimiento.ENTRADA,
                    origen=MovimientoCaja.Origen.COBRO_PRESTAMO,
                    monto=self.monto,
                    documento_referencia=f'Préstamo #{self.prestamo_id}',
                    usuario=self.usuario,
                )
            else:
                # Estamos pagando un préstamo que nos hicieron → sale plata de caja
                MovimientoCaja.objects.create(
                    tipo_movimiento=MovimientoCaja.TipoMovimiento.SALIDA,
                    origen=MovimientoCaja.Origen.PAGO_PRESTAMO,
                    monto=self.monto,
                    documento_referencia=f'Préstamo #{self.prestamo_id}',
                    usuario=self.usuario,
                )