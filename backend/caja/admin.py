from django.contrib import admin
from .models import MovimientoCaja


@admin.register(MovimientoCaja)
class MovimientoCajaAdmin(admin.ModelAdmin):
    list_display = (
        'creado_en', 'tipo_movimiento', 'origen', 'monto',
        'saldo_resultante', 'usuario', 'documento_referencia',
    )
    list_filter = ('tipo_movimiento', 'origen')
    search_fields = ('documento_referencia', 'descripcion')
    readonly_fields = ('saldo_resultante',)