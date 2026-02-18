from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Configuracion, PerfilUsuario

class PerfilUsuarioInline(admin.StackedInline):
    model = PerfilUsuario
    can_delete = False
    verbose_name_plural = 'Perfil de Acceso a Almacenes'

admin.site.register(User, UserAdmin) # Puedes personalizar UserAdmin para incluir el inline si deseas, pero registrarlo aparte también funciona o usar un Inline en UserAdmin es mejor.

@admin.register(Configuracion)
class ConfiguracionAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        # Solo permitir crear si no existe ninguno (Singleton)
        if self.model.objects.exists():
            return False
        return super().has_add_permission(request)

@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'get_almacenes')
    search_fields = ('usuario__username', 'usuario__first_name')
    filter_horizontal = ('almacenes',)

    def get_almacenes(self, obj):
        return ", ".join([a.nombre for a in obj.almacenes.all()])
    get_almacenes.short_description = 'Almacenes Permitidos'