from django.contrib import admin
from .models import Cliente


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'numero_documento', 'telefono', 'es_generico', 'activo')
    list_filter = ('es_generico', 'activo')
    search_fields = ('nombre', 'numero_documento', 'telefono')