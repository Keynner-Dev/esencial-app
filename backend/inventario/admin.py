from django.contrib import admin
from .models import MovimientoStock


@admin.register(MovimientoStock)
class MovimientoStockAdmin(admin.ModelAdmin):
    list_display = (
        'producto', 'tipo_movimiento', 'cantidad',
        'stock_resultante', 'usuario', 'creado_en',
    )
    list_filter = ('tipo_movimiento', 'creado_en')
    search_fields = ('producto__nombre', 'documento_referencia')
    readonly_fields = ('stock_resultante',)