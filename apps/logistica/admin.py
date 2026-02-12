from django.contrib import admin, messages # Importamos messages
from .models import Almacen, Stock, Existencia, Movimiento, DetalleMovimiento, Requerimiento, DetalleRequerimiento
from .services import KardexService # Importamos nuestro servicio
from django.core.exceptions import ValidationError

class StockInline(admin.TabularInline):
    model = Stock
    extra = 0
    fields = ('material', 'cantidad', 'cantidad_minima', 'ubicacion_pasillo')
    readonly_fields = ('material', 'cantidad',) # Solo permitimos editar Mínimo y Ubicación

@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ('material', 'almacen', 'cantidad', 'cantidad_minima', 'estado_alerta', 'ubicacion_pasillo')
    list_filter = ('almacen',)
    search_fields = ('material__codigo', 'material__descripcion')
    # Esto permite editar el mínimo directamente desde la lista sin entrar uno por uno
    list_editable = ('cantidad_minima', 'ubicacion_pasillo') 
    readonly_fields = ('cantidad',) # La cantidad solo se mueve con Movimientos (Ingresos/Salidas)
    ordering = ('almacen', 'material')

@admin.register(Almacen)
class AlmacenAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'proyecto', 'es_principal')
    list_filter = ('proyecto',)
    inlines = [StockInline]

@admin.register(Existencia)
class ExistenciaAdmin(admin.ModelAdmin):
    list_display = ('material', 'proyecto', 'stock_total_proyecto', 'costo_promedio')
    list_filter = ('proyecto',)
    search_fields = ('material__codigo',)

# ==========================================
# GESTIÓN DE REQUERIMIENTOS
# ==========================================
class DetalleRequerimientoInline(admin.TabularInline):
    model = DetalleRequerimiento
    extra = 1

@admin.register(Requerimiento)
class RequerimientoAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'solicitante', 'proyecto', 'fecha_solicitud', 'estado', 'prioridad')
    list_filter = ('estado', 'prioridad', 'proyecto')
    search_fields = ('codigo', 'solicitante')
    inlines = [DetalleRequerimientoInline]
    
    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.creado_por = request.user
        super().save_model(request, obj, form, change)

class DetalleMovimientoInline(admin.TabularInline):
    model = DetalleMovimiento
    extra = 1

@admin.register(Movimiento)
class MovimientoAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'codigo_visual', 'tipo', 'requerimiento', 'proyecto', 'estado')
    list_filter = ('tipo', 'estado', 'proyecto')
    inlines = [DetalleMovimientoInline]
    actions = ['confirmar_movimientos'] # Registramos la acción
    readonly_fields = ('estado',)

    def codigo_visual(self, obj):
        return f"MOV-{str(obj.id)[:8]}"

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.creado_por = request.user
        super().save_model(request, obj, form, change)

    # --- ACCIÓN PERSONALIZADA ---
    @admin.action(description='CONFIRMAR movimientos seleccionados (Afectar Stock)')
    def confirmar_movimientos(self, request, queryset):
        procesados = 0
        for movimiento in queryset:
            try:
                KardexService.confirmar_movimiento(movimiento.id)
                procesados += 1
            except ValidationError as e:
                self.message_user(request, f"Error en {movimiento}: {e.message}", level=messages.ERROR)
            except Exception as e:
                self.message_user(request, f"Error crítico en {movimiento}: {str(e)}", level=messages.ERROR)
        
        if procesados > 0:
            self.message_user(request, f"Se confirmaron correctamente {procesados} movimientos.", level=messages.SUCCESS)