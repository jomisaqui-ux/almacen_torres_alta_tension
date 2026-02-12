from django.db import models
import uuid

class Trabajador(models.Model):
    """
    Personal de obra al que se le asignan activos o EPPs.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dni = models.CharField(max_length=8, unique=True, verbose_name="DNI")
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    cargo = models.CharField(max_length=100, blank=True)
    
    # Datos para EPP (Tallas)
    talla_zapato = models.CharField(max_length=10, blank=True, help_text="Ej: 40, 42")
    talla_ropa = models.CharField(max_length=10, blank=True, help_text="Ej: M, L, XL")
    
    activo = models.BooleanField(default=True, help_text="¿Sigue trabajando en la empresa?")

    def __str__(self):
        return f"{self.nombres} {self.apellidos}"

    class Meta:
        verbose_name = "Trabajador"
        verbose_name_plural = "Trabajadores"
