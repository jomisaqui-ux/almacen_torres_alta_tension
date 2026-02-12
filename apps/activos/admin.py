from django.contrib import admin
from .models import Activo, AsignacionActivo

@admin.register(Activo)
class ActivoAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'marca', 'estado', 'trabajador_asignado')
    list_filter = ('estado', 'marca')
    search_fields = ('codigo', 'nombre', 'serie')

@admin.register(AsignacionActivo)
class AsignacionActivoAdmin(admin.ModelAdmin):
    list_display = ('activo', 'trabajador', 'fecha_asignacion', 'fecha_devolucion')
    list_filter = ('fecha_asignacion',)
    search_fields = ('activo__codigo', 'trabajador__nombres', 'trabajador__apellidos')
    readonly_fields = ('fecha_asignacion',)
