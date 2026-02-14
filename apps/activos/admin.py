from django.contrib import admin
from .models import Activo, AsignacionActivo, Kit

# Si tienes otros modelos (ej: Kit, CategoriaActivo), mantenlos registrados aquí.

@admin.register(Activo)
class ActivoAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'serie', 'nombre', 'marca', 'estado', 'trabajador_asignado')
    list_filter = ('estado', 'marca')
    search_fields = ('codigo', 'serie', 'nombre', 'trabajador_asignado__nombres', 'trabajador_asignado__dni')
    
    # Hacemos readonly los campos que vienen de Logística para evitar desincronización al editar
    readonly_fields = ('material', 'ingreso_origen', 'fecha_compra', 'valor_compra', 'codigo', 'serie')

    def has_add_permission(self, request):
        """
        BLOQUEO DE SEGURIDAD:
        Deshabilitamos el botón 'Agregar Activo' (Nuevo Equipo).
        
        Motivo: Los activos deben crearse AUTOMÁTICAMENTE al registrar un 
        'Ingreso por Compra' en el módulo de Logística. 
        Crearlos aquí generaría un activo 'huérfano' sin stock físico ni costo en el Kardex.
        """
        return False

    def has_delete_permission(self, request, obj=None):
        # Permitimos borrar para correcciones manuales, pero la creación es lo crítico.
        return super().has_delete_permission(request, obj)

@admin.register(AsignacionActivo)
class AsignacionActivoAdmin(admin.ModelAdmin):
    list_display = ('activo', 'trabajador')
    search_fields = ('activo__codigo', 'trabajador__nombres')
    
    def has_add_permission(self, request):
        """
        BLOQUEO DE SEGURIDAD:
        Las asignaciones deben hacerse vía 'Vale de Salida' en Logística
        para generar el documento PDF firmado y validar disponibilidad.
        """
        return False

@admin.register(Kit)
class KitAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'descripcion')
    search_fields = ('codigo', 'nombre')