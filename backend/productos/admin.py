from django.contrib import admin
from .models import Categoria, Producto


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'activa')
    list_filter = ('activa',)
    search_fields = ('nombre',)


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = (
        'nombre', 'categoria', 'tipo_producto', 'subtipo_insumo', 'unidad_medida',
        'costo_compra', 'precio_detal', 'precio_mayorista',
        'disponible_mayorista', 'stock_actual', 'activo',
    )
    list_filter = ('tipo_producto', 'subtipo_insumo', 'categoria', 'disponible_mayorista', 'activo')
    search_fields = ('nombre',)