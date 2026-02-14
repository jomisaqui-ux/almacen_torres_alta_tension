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

class EntregaEPP(models.Model):
    """
    Historial de EPPs entregados a un trabajador.
    Se llena automáticamente desde Logística cuando sale un material tipo 'EPP'.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trabajador = models.ForeignKey(Trabajador, related_name='epps_entregados', on_delete=models.CASCADE)
    material = models.ForeignKey('catalogo.Material', on_delete=models.PROTECT)
    cantidad = models.DecimalField(max_digits=12, decimal_places=2)
    fecha_entrega = models.DateTimeField(auto_now_add=True)
    movimiento_origen = models.ForeignKey('logistica.Movimiento', on_delete=models.CASCADE, related_name='registros_epp', null=True, blank=True)

    @property
    def movimiento(self):
        return self.movimiento_origen

    def __str__(self):
        return f"{self.trabajador} - {self.material} ({self.fecha_entrega.date()})"

    class Meta:
        verbose_name = "Historial de EPP"
        verbose_name_plural = "Historial de EPPs"
        ordering = ['-fecha_entrega']
