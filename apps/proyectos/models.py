from django.db import models
import uuid

class Proyecto(models.Model):
    """
    Define la obra en general.
    Aquí configuramos si este proyecto específico llevará control de costos o no.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=200, help_text="Ej: Línea de Transmisión 500kV Mantaro")
    codigo = models.CharField(max_length=20, unique=True, help_text="Código interno, Ej: LT-500")
    
    # --- CONFIGURACIÓN FINANCIERA (TU REQUERIMIENTO) ---
    usa_control_costos = models.BooleanField(
        default=True, 
        verbose_name="¿Controlar Costos?",
        help_text="Si está activo, el sistema exigirá precios en las compras y calculará el PMP."
    )
    moneda = models.CharField(max_length=3, default='PEN', choices=[('PEN', 'Soles'), ('USD', 'Dólares')])
    
    fecha_inicio = models.DateField(null=True, blank=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

    class Meta:
        verbose_name = "Proyecto"
        verbose_name_plural = "Proyectos"


class Tramo(models.Model):
    """
    Subdivisión geográfica del proyecto (Ej: Tramo 1, Tramo Montaña, Frente Norte).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    proyecto = models.ForeignKey(Proyecto, related_name='tramos', on_delete=models.CASCADE)
    nombre = models.CharField(max_length=100, help_text="Ej: Tramo Km 0-20")
    codigo = models.CharField(max_length=20)
    
    def __str__(self):
        return f"{self.proyecto.codigo} | {self.nombre}"
    
    class Meta:
        unique_together = ('proyecto', 'codigo') # No repetir códigos en el mismo proyecto


class Torre(models.Model):
    """
    El CENTRO DE COSTO principal. 
    Aquí es donde imputaremos los materiales (cemento, perfiles, aisladores).
    """
    TIPO_TORRE = [
        ('SUSPENSION', 'Suspensión (Soporta peso)'),
        ('ANCLAJE', 'Anclaje (Soporta tensión)'),
        ('REMATE', 'Remate (Inicio/Fin)'),
        ('OFICINA', 'Oficina / Campamento'), # Para imputar gastos no constructivos
        ('OTROS', 'Otros Frentes'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tramo = models.ForeignKey(Tramo, related_name='torres', on_delete=models.PROTECT)
    codigo = models.CharField(max_length=20, help_text="Número o código de torre/estructura")
    tipo = models.CharField(max_length=20, choices=TIPO_TORRE)
    
    # Datos opcionales de ingeniería
    ubicacion_gps = models.CharField(max_length=100, blank=True, null=True, help_text="Latitud, Longitud")
    
    def __str__(self):
        return f"{self.tramo.codigo} - {self.codigo} ({self.get_tipo_display()})"

    class Meta:
        unique_together = ('tramo', 'codigo')
        ordering = ['codigo']