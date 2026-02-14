from django.db import models
import uuid
from apps.rrhh.models import Trabajador

class Kit(models.Model):
    """
    Agrupación lógica de herramientas (Ej: Kit de Soldadura, Kit de Altura).
    Facilita la asignación masiva.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codigo = models.CharField(max_length=20, unique=True, help_text="Ej: KIT-01")
    nombre = models.CharField(max_length=100, help_text="Ej: Kit de Herramientas Básicas")
    descripcion = models.TextField(blank=True)

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

    class Meta:
        verbose_name = "Kit de Herramientas"
        verbose_name_plural = "Kits de Herramientas"

class Activo(models.Model):
    """
    Equipos y Herramientas que se controlan por SERIE y se devuelven.
    """
    ESTADOS = [
        ('DISPONIBLE', 'Disponible'),
        ('ASIGNADO', 'Asignado (En uso)'),
        ('MANTENIMIENTO', 'En Mantenimiento'),
        ('BAJA', 'Dado de Baja'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codigo = models.CharField(max_length=50, unique=True, help_text="Código Interno (Ej: TAL-01)")
    serie = models.CharField(max_length=100, blank=True, help_text="Serie del Fabricante")
    nombre = models.CharField(max_length=100, help_text="Ej: Taladro Percutor")
    marca = models.CharField(max_length=50, blank=True)
    modelo = models.CharField(max_length=50, blank=True)
    
    estado = models.CharField(max_length=20, choices=ESTADOS, default='DISPONIBLE')
    
    # Pertenencia a un Kit
    kit = models.ForeignKey(
        Kit, 
        related_name='componentes', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="Si pertenece a un kit, se asignará junto con él."
    )

    # Control de ubicación actual
    ubicacion = models.ForeignKey(
        'logistica.Almacen',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activos_en_ubicacion',
        help_text="Almacén físico donde se encuentra actualmente"
    )

    # Control de ubicación actual
    trabajador_asignado = models.ForeignKey(
        Trabajador, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='activos_actuales',
        help_text="Quién lo tiene actualmente"
    )
    
    fecha_compra = models.DateField(null=True, blank=True)
    valor_compra = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    foto = models.ImageField(upload_to='activos/', null=True, blank=True, help_text="Foto referencial del equipo")
    
    ingreso_origen = models.ForeignKey(
        'logistica.Movimiento', 
        on_delete=models.PROTECT, 
        null=True, 
        blank=True, 
        related_name='activos_generados'
    )
    
    material = models.ForeignKey(
        'catalogo.Material',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='activos_fijos',
        help_text="Enlace al catálogo para control de stock"
    )

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

    class Meta:
        verbose_name = "Activo Fijo"
        verbose_name_plural = "Activos Fijos"

class AsignacionActivo(models.Model):
    """
    Historial de movimientos (Préstamos y Devoluciones).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    activo = models.ForeignKey(Activo, related_name='historial_asignaciones', on_delete=models.PROTECT)
    trabajador = models.ForeignKey(Trabajador, related_name='historial_activos', on_delete=models.PROTECT)
    
    fecha_asignacion = models.DateTimeField(auto_now_add=True)
    fecha_devolucion = models.DateTimeField(null=True, blank=True)
    
    observacion_entrega = models.TextField(blank=True)
    observacion_devolucion = models.TextField(blank=True)

    def __str__(self):
        return f"{self.activo.codigo} -> {self.trabajador.nombres}"
