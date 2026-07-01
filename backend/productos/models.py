from decimal import Decimal
from django.core.validators import MinValueValidator
from django.db import models


class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.CharField(max_length=255, blank=True, null=True)
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ['nombre']
        verbose_name_plural = 'Categorías'

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    class TipoProducto(models.TextChoices):
        INSUMO = 'INSUMO', 'Insumo'
        TERMINADO = 'TERMINADO', 'Terminado (reventa)'

    class SubtipoInsumo(models.TextChoices):
        ESENCIA = 'ESENCIA', 'Esencia'
        ENVASE = 'ENVASE', 'Envase'
        EXTRA = 'EXTRA', 'Extra (feromona, fijador, potencializador, etc.)'
        OTRO = 'OTRO', 'Otro insumo'

    class UnidadMedida(models.TextChoices):
        UNIDAD = 'UND', 'Unidad'
        MILILITRO = 'ML', 'Mililitro'
        GRAMO = 'G', 'Gramo'

    nombre = models.CharField(max_length=150, unique=True)
    categoria = models.ForeignKey(
        Categoria, on_delete=models.PROTECT, related_name='productos'
    )
    tipo_producto = models.CharField(max_length=10, choices=TipoProducto.choices)
    subtipo_insumo = models.CharField(
        max_length=10, choices=SubtipoInsumo.choices, blank=True, null=True,
        help_text='Solo aplica cuando el tipo de producto es Insumo.',
    )
    unidad_medida = models.CharField(max_length=5, choices=UnidadMedida.choices)

    costo_compra = models.PositiveIntegerField(default=0)

    precio_detal = models.PositiveIntegerField(default=0)
    margen_detal = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))

    precio_mayorista = models.PositiveIntegerField(blank=True, null=True)
    margen_mayorista = models.DecimalField(
        max_digits=6, decimal_places=2, blank=True, null=True
    )

    disponible_mayorista = models.BooleanField(default=False)

    stock_actual = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    stock_minimo = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
    )

    gramos_sugeridos = models.PositiveIntegerField(
        blank=True, null=True,
        help_text='Solo para envases: gramos de esencia sugeridos para ese tamaño (ej. 30ml → 13g). Editable al vender.',
    )

    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['nombre']

    def __str__(self):
        return self.nombre

    def calcular_margen(self, precio, costo):
        if not costo:
            return Decimal('0.00')
        return (Decimal(precio - costo) / Decimal(costo)) * 100

    def calcular_precio(self, margen, costo):
        return round(costo * (1 + (Decimal(margen) / 100)))