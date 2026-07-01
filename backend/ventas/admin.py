from django.contrib import admin
from .models import Venta, DetalleVentaProducto, DetalleVentaPerfume


class DetalleVentaProductoInline(admin.TabularInline):
    model = DetalleVentaProducto
    extra = 1
    readonly_fields = ('costo_unitario', 'subtotal')


class DetalleVentaPerfumeInline(admin.TabularInline):
    model = DetalleVentaPerfume
    extra = 1
    readonly_fields = ('costo_unitario', 'precio_venta', 'subtotal')


@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ('id', 'cliente', 'tipo_venta', 'forma_pago', 'fecha', 'total', 'usuario')
    list_filter = ('tipo_venta', 'forma_pago', 'fecha')
    search_fields = ('cliente__nombre',)
    readonly_fields = ('total',)
    inlines = [DetalleVentaProductoInline, DetalleVentaPerfumeInline]