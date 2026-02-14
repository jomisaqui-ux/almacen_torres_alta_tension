from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Activo, AsignacionActivo

@admin.register(Activo)
class ActivoAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'marca', 'estado', 'trabajador_asignado', 'link_ingreso')
    list_filter = ('estado', 'marca')
    search_fields = ('codigo', 'nombre', 'serie', 'ingreso_origen__nota_ingreso')
    readonly_fields = ('ingreso_origen',)

    def link_ingreso(self, obj):
        if obj.ingreso_origen:
            url = reverse('admin:logistica_movimiento_change', args=[obj.ingreso_origen.id])
            return format_html('<a href="{}">{}</a>', url, obj.ingreso_origen.nota_ingreso or "Ver Ingreso")
        return "-"
    link_ingreso.short_description = "Origen (Nota Ingreso)"

@admin.register(AsignacionActivo)
class AsignacionActivoAdmin(admin.ModelAdmin):
    list_display = ('activo', 'trabajador', 'fecha_asignacion', 'fecha_devolucion')
    list_filter = ('fecha_asignacion',)
    search_fields = ('activo__codigo', 'trabajador__nombres', 'trabajador__apellidos')
    readonly_fields = ('fecha_asignacion',)
