from django.contrib import admin
from .models import Proyecto, Tramo, Torre

class TramoInline(admin.TabularInline):
    model = Tramo
    extra = 1

@admin.register(Proyecto)
class ProyectoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'codigo', 'usa_control_costos', 'activo')
    inlines = [TramoInline] # Permite crear tramos dentro de la pantalla del Proyecto

@admin.register(Torre)
class TorreAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'tipo', 'tramo_nombre', 'proyecto_nombre')
    list_filter = ('tipo', 'tramo__proyecto')
    search_fields = ('codigo', 'tramo__nombre')

    def tramo_nombre(self, obj):
        return obj.tramo.nombre
    
    def proyecto_nombre(self, obj):
        return obj.tramo.proyecto.nombre