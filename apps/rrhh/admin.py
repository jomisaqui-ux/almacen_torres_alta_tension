from django.contrib import admin
from .models import Trabajador

@admin.register(Trabajador)
class TrabajadorAdmin(admin.ModelAdmin):
    list_display = ('dni', 'nombres', 'apellidos', 'cargo', 'activo')
    search_fields = ('dni', 'nombres', 'apellidos')
    list_filter = ('activo', 'cargo')
