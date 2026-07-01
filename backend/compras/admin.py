from django.contrib import admin
from .models import Proveedor, Factura, DetalleFactura


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'numero_documento', 'telefono', 'activo')
    list_filter = ('activo',)
    search_fields = ('nombre', 'numero_documento')


class DetalleFacturaInline(admin.TabularInline):
    model = DetalleFactura
    extra = 1
    readonly_fields = ('subtotal',)


@admin.register(Factura)
class FacturaAdmin(admin.ModelAdmin):
    list_display = ('numero_factura', 'proveedor', 'fecha', 'total', 'usuario')
    list_filter = ('proveedor', 'fecha')
    search_fields = ('numero_factura', 'proveedor__nombre')
    readonly_fields = ('total',)
    inlines = [DetalleFacturaInline]