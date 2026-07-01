from django.contrib import admin
from .models import Fiado, AbonoFiado, Prestamo, AbonoPrestamo


class AbonoFiadoInline(admin.TabularInline):
    model = AbonoFiado
    extra = 1


@admin.register(Fiado)
class FiadoAdmin(admin.ModelAdmin):
    list_display = ('id', 'venta', 'monto_total', 'saldo_pendiente', 'estado')
    list_filter = ('estado',)
    readonly_fields = ('monto_total', 'saldo_pendiente', 'estado')
    inlines = [AbonoFiadoInline]


class AbonoPrestamoInline(admin.TabularInline):
    model = AbonoPrestamo
    extra = 1


@admin.register(Prestamo)
class PrestamoAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'direccion', 'persona', 'monto_capital',
        'tasa_interes', 'monto_total_a_pagar', 'saldo_pendiente', 'estado', 'fecha',
    )
    list_filter = ('direccion', 'estado')
    search_fields = ('persona__nombre',)
    readonly_fields = ('monto_total_a_pagar', 'saldo_pendiente', 'estado')
    inlines = [AbonoPrestamoInline]