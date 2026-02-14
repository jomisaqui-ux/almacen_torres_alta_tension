from django.contrib import admin
from .models import Trabajador, EntregaEPP

@admin.register(Trabajador)
class TrabajadorAdmin(admin.ModelAdmin):
    list_display = ('dni', 'nombres', 'apellidos', 'cargo', 'activo')
    search_fields = ('dni', 'nombres', 'apellidos')
    list_filter = ('activo', 'cargo')

@admin.register(EntregaEPP)
class EntregaEPPAdmin(admin.ModelAdmin):
    list_display = ('trabajador', 'material', 'cantidad', 'fecha_entrega', 'movimiento_origen')
    list_filter = ('material', 'fecha_entrega')
    search_fields = ('trabajador__nombres', 'trabajador__apellidos', 'material__codigo')
    date_hierarchy = 'fecha_entrega'
