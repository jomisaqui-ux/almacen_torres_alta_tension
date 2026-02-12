from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Configuracion

admin.site.register(User, UserAdmin)

@admin.register(Configuracion)
class ConfiguracionAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        # Solo permitir crear si no existe ninguno (Singleton)
        if self.model.objects.exists():
            return False
        return super().has_add_permission(request)