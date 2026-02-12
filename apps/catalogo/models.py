from django.db import models
import uuid

class Categoria(models.Model):
    """
    Agrupa materiales: Eléctricos, Ferretería, EPP, Herramientas.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=100)
    codigo = models.CharField(max_length=10, unique=True, help_text="Ej: ELE, FER, EPP")
    
    def __str__(self):
        return f"{self.codigo} - {self.nombre}"
    
    class Meta:
        verbose_name = "Categoría"

class Material(models.Model):
    """
    Catálogo MAESTRO Global.
    Define QUÉ es el ítem, pero NO cuánto cuesta ni cuánto hay.
    Es puramente técnico.
    """
    TIPO_MATERIAL = [
        ('CONSUMIBLE', 'Consumible (Cemento, Pernos)'), # Se gasta
        ('ACTIVO_FIJO', 'Activo Fijo (Taladros, Equipos)'), # Se devuelve/deprecia
        ('EPP', 'EPP (Cascos, Guantes)'), # Se asigna a persona
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codigo = models.CharField(max_length=20, unique=True, help_text="Código único global. Ej: MAT-001")
    descripcion = models.CharField(max_length=255)
    unidad_medida = models.CharField(max_length=10, help_text="UND, M, KG, BLS")
    
    categoria = models.ForeignKey(Categoria, related_name='materiales', on_delete=models.PROTECT)
    tipo = models.CharField(max_length=20, choices=TIPO_MATERIAL, default='CONSUMIBLE')
    
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.codigo} - {self.descripcion}"
        
    class Meta:
        verbose_name = "Material"
        verbose_name_plural = "Materiales"
        ordering = ['codigo']