from django.contrib import admin
from .models import Categoria, Material, Proveedor

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre')
    search_fields = ('nombre', 'codigo')

@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'descripcion', 'unidad_medida', 'categoria', 'tipo', 'activo')
    list_filter = ('categoria', 'tipo', 'activo')
    search_fields = ('codigo', 'descripcion')
    list_per_page = 20

@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ('ruc', 'razon_social', 'contacto', 'telefono', 'activo')
    search_fields = ('ruc', 'razon_social')
    list_filter = ('activo',)