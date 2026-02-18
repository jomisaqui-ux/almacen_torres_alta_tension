from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    """
    Usuario personalizado del sistema.
    Podemos extenderlo con roles específicos más adelante.
    """
    dni = models.CharField(max_length=8, unique=True, null=True, blank=True)
    cargo = models.CharField(max_length=100, null=True, blank=True)
    
    # Aquí podríamos agregar 'almacen_asignado' en el futuro
    
    def __str__(self):
        return f"{self.username} - {self.get_full_name()}"

class Configuracion(models.Model):
    """
    Modelo Singleton para datos de la empresa y branding.
    """
    nombre_empresa = models.CharField(max_length=200, default="Mi Empresa S.A.C.")
    ruc = models.CharField(max_length=11, blank=True, help_text="RUC de la empresa")
    direccion = models.CharField(max_length=255, blank=True)
    logo = models.ImageField(upload_to='empresa/', null=True, blank=True, help_text="Logo para reportes (Recomendado: 300x100px)")
    
    def __str__(self):
        return self.nombre_empresa

    class Meta:
        verbose_name = "Configuración General"
        verbose_name_plural = "Configuración General"

class PerfilUsuario(models.Model):
    """
    Extensión del usuario para controlar permisos de acceso a almacenes.
    """
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    almacenes = models.ManyToManyField('logistica.Almacen', blank=True, related_name='usuarios_permitidos', help_text="Almacenes a los que tiene acceso este usuario.")

    def __str__(self):
        return f"Perfil de {self.usuario.username}"