from django.db import models
from django.conf import settings # Para referenciar al Usuario
import uuid
from django.core.exceptions import ValidationError
from decimal import Decimal

# Importamos modelos de otras apps
from apps.proyectos.models import Proyecto, Torre
from apps.catalogo.models import Material
from apps.rrhh.models import Trabajador

# ==========================================
# 1. DEFINICIÓN DE ALMACENES
# ==========================================

class Almacen(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    proyecto = models.ForeignKey(Proyecto, related_name='almacenes', on_delete=models.CASCADE)
    nombre = models.CharField(max_length=100)
    codigo = models.CharField(max_length=20)
    es_principal = models.BooleanField(default=False, help_text="¿Es el almacén central del proyecto?")
    ubicacion = models.CharField(max_length=200, blank=True)
    
    def __str__(self):
        return f"[{self.proyecto.codigo}] {self.nombre}"

    class Meta:
        unique_together = ('proyecto', 'codigo')
        verbose_name = "Almacén"
        verbose_name_plural = "Almacenes"

# ==========================================
# 2. CONTROL FINANCIERO Y FÍSICO (EL CEREBRO)
# ==========================================

class Existencia(models.Model):
    """
    TABLA MAESTRA DE COSTOS POR PROYECTO.
    Aquí vive el Precio Promedio Ponderado (PMP) de un material DENTRO de un proyecto específico.
    Si el proyecto 'usa_control_costos=False', estos valores serán 0.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    proyecto = models.ForeignKey(Proyecto, related_name='existencias', on_delete=models.CASCADE)
    material = models.ForeignKey(Material, related_name='existencias_proyecto', on_delete=models.PROTECT)
    
    # Datos Financieros (Globales para el proyecto)
    costo_promedio = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    ultimo_costo_compra = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    
    # Datos Físicos Agregados (Suma de todos los almacenes del proyecto)
    stock_total_proyecto = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        unique_together = ('proyecto', 'material')
        verbose_name = "Existencia (Costo/Stock Global)"
        verbose_name_plural = "Existencias (Costos/Stocks)"

class Stock(models.Model):
    """
    STOCK FÍSICO POR ALMACÉN.
    Dice cuánto hay exactamente en cada bodega.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    almacen = models.ForeignKey(Almacen, related_name='stocks', on_delete=models.CASCADE)
    material = models.ForeignKey(Material, related_name='stocks_almacen', on_delete=models.PROTECT)
    cantidad = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cantidad_minima = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Punto de reorden (Alerta)")
    ubicacion_pasillo = models.CharField(max_length=50, blank=True, help_text="Ej: Estante A1")

    def __str__(self):
        return f"{self.material.codigo} en {self.almacen.nombre}: {self.cantidad}"

    @property
    def estado_alerta(self):
        """Devuelve el estado del semáforo: CRITICO, ADVERTENCIA, OK"""
        if self.cantidad_minima > 0:
            if self.cantidad <= self.cantidad_minima:
                return 'CRITICO' # Rojo
            elif self.cantidad <= self.cantidad_minima * Decimal('1.2'):
                return 'ADVERTENCIA' # Amarillo (Stock <= Mínimo + 20%)
        return 'OK' # Verde

    class Meta:
        unique_together = ('almacen', 'material')
        verbose_name = "Stock Físico"

# ==========================================
# 2.5 GESTIÓN DE REQUERIMIENTOS
# ==========================================

class Requerimiento(models.Model):
    """
    Solicitud formal de materiales. Paso previo obligatorio a la Salida.
    """
    ESTADOS = [
        ('PENDIENTE', 'Pendiente'),
        ('PARCIAL', 'Atendido Parcial'),
        ('TOTAL', 'Atendido Total'),
        ('CANCELADO', 'Cancelado'),
    ]
    
    PRIORIDADES = [
        ('BAJA', 'Baja'),
        ('MEDIA', 'Media'),
        ('ALTA', 'Alta'),
        ('URGENTE', 'Urgente'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    proyecto = models.ForeignKey(Proyecto, related_name='requerimientos', on_delete=models.PROTECT)
    codigo = models.CharField(max_length=20, unique=True, blank=True, help_text="Autogenerado: REQ-0001")
    
    solicitante = models.CharField(max_length=100, help_text="Persona que solicita el material")
    fecha_solicitud = models.DateField()
    fecha_necesaria = models.DateField(null=True, blank=True, help_text="Fecha límite requerida")
    prioridad = models.CharField(max_length=10, choices=PRIORIDADES, default='MEDIA')
    
    estado = models.CharField(max_length=20, choices=ESTADOS, default='PENDIENTE')
    observacion = models.TextField(blank=True)
    
    # Auditoría
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.codigo and self.proyecto:
            # Generador de código simple: REQ-0001
            count = Requerimiento.objects.filter(proyecto=self.proyecto).count()
            self.codigo = f"REQ-{str(count + 1).zfill(5)}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.codigo} - {self.solicitante} ({self.get_estado_display()})"

class DetalleRequerimiento(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    requerimiento = models.ForeignKey(Requerimiento, related_name='detalles', on_delete=models.CASCADE)
    material = models.ForeignKey(Material, on_delete=models.PROTECT)
    
    cantidad_solicitada = models.DecimalField(max_digits=12, decimal_places=2)
    cantidad_ingresada = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Cantidad recibida en almacén (Compras)")
    cantidad_atendida = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    @property
    def cantidad_pendiente(self):
        return max(Decimal('0'), self.cantidad_solicitada - self.cantidad_atendida)

    def __str__(self):
        return f"{self.material.codigo} - Sol: {self.cantidad_solicitada}"

# ==========================================
# 3. KARDEX / MOVIMIENTOS
# ==========================================

class Movimiento(models.Model):
    """
    Cabecera del movimiento. Representa la 'Hoja de Entrada/Salida'.
    """
    TIPOS_MOVIMIENTO = [
        ('INGRESO_COMPRA', 'Ingreso por Compra'),
        ('SALIDA_OBRA', 'Salida a Obra (Consumo Torre)'),
        ('SALIDA_EPP', 'Entrega de EPP / Ropa'),
        ('SALIDA_OFICINA', 'Salida a Oficina/Gasto'),
        ('TRANSFERENCIA_SALIDA', 'Transferencia (Salida)'),
        ('TRANSFERENCIA_ENTRADA', 'Transferencia (Entrada)'),
        ('DEVOLUCION_OBRA', 'Reingreso por Devolución de Obra'),
        ('DEVOLUCION_LIMA', 'Devolución a Sede Central (Salida)'),
        ('REINGRESO_LIMA', 'Reingreso de Sede Central (Entrada)'),
        ('AJUSTE_INVENTARIO', 'Ajuste de Inventario'),
    ]

    ESTADOS = [
        ('BORRADOR', 'Borrador'),
        ('CONFIRMADO', 'Confirmado (Procesado)'),
        ('CANCELADO', 'Cancelado'),
    ]
    estado = models.CharField(max_length=20, choices=ESTADOS, default='BORRADOR')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    proyecto = models.ForeignKey(Proyecto, related_name='movimientos', on_delete=models.PROTECT)
    tipo = models.CharField(max_length=30, choices=TIPOS_MOVIMIENTO)
    fecha = models.DateTimeField(auto_now_add=True)
    
    # Referencias
    documento_referencia = models.CharField(max_length=50, help_text="Nro Guía, Factura, Vale")
    
    requerimiento = models.ForeignKey(Requerimiento, related_name='salidas', on_delete=models.PROTECT, null=True, blank=True, help_text="Requerimiento aprobado que justifica esta salida")
    # Origen / Destino (Lógica flexible)
    almacen_origen = models.ForeignKey(Almacen, related_name='salidas', on_delete=models.PROTECT, null=True, blank=True)
    almacen_destino = models.ForeignKey(Almacen, related_name='ingresos', on_delete=models.PROTECT, null=True, blank=True)
    
    # Solo para Salidas a Obra
    torre_destino = models.ForeignKey(Torre, related_name='consumos', on_delete=models.PROTECT, null=True, blank=True)
    trabajador = models.ForeignKey(Trabajador, related_name='movimientos', on_delete=models.PROTECT, null=True, blank=True, help_text="Trabajador solicitante o beneficiario")
    
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    observacion = models.TextField(blank=True)

    nota_ingreso = models.CharField(
        max_length=20, 
        blank=True, 
        null=True, 
        verbose_name="Nota de Ingreso",
        help_text="Correlativo interno autogenerado"
    )

    def save(self, *args, **kwargs):
        # Lógica para autogenerar Nota de Ingreso (NI) si es compra y no tiene código
        if self.tipo == 'INGRESO_COMPRA' and not self.nota_ingreso:
            # Contamos cuántos ingresos existen en ESTE proyecto
            # Nota: Si el proyecto es None al inicio (borrador), se asignará después
            if self.proyecto:
                correlativo = Movimiento.objects.filter(
                    proyecto=self.proyecto, 
                    tipo='INGRESO_COMPRA'
                ).count() + 1
                
                # Formato: NI-0001, NI-0002...
                self.nota_ingreso = f"NI-{str(correlativo).zfill(5)}"
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.documento_referencia}"
    
    def clean(self):
        # Validación básica de lógica de negocio
        if self.tipo == 'SALIDA_OBRA' and not self.torre_destino:
            raise ValidationError('Para una Salida a Obra, debes especificar la Torre Destino.')
        if self.tipo in ['SALIDA_EPP', 'SALIDA_OBRA', 'SALIDA_OFICINA'] and not self.trabajador:
            raise ValidationError('Para cualquier Salida, debes seleccionar al Trabajador responsable.')
    
    def codigo_visual(self):
        if self.id:
            return f"MOV-{str(self.id)[:8].upper()}"
        return "NUEVO"

class DetalleMovimiento(models.Model):
    """
    Los ítems dentro del movimiento.
    Aquí se guarda el PRECIO HISTÓRICO (Snapshot) del momento de la transacción.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    movimiento = models.ForeignKey(Movimiento, related_name='detalles', on_delete=models.CASCADE)
    material = models.ForeignKey(Material, on_delete=models.PROTECT)
    cantidad = models.DecimalField(max_digits=12, decimal_places=2)
    
    # El costo unitario se guarda aquí para la historia, aunque cambie el PMP mañana.
    costo_unitario = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    marca = models.CharField(max_length=100, blank=True, verbose_name="Marca/Modelo")
    series_temporales = models.TextField(blank=True, help_text="Series separadas por coma para activos fijos (Solo Ingresos)")
    
    # Nuevo campo para vincular salida de activo fijo específico
    activo = models.ForeignKey(
        'activos.Activo', 
        on_delete=models.PROTECT, 
        null=True, 
        blank=True, 
        related_name='movimientos',
        help_text="Activo fijo específico entregado (Solo para Salidas)"
    )
    
    # Nuevo: Permite asignar esta línea específica a un requerimiento distinto al de la cabecera
    requerimiento = models.ForeignKey(
        Requerimiento, 
        on_delete=models.PROTECT, 
        null=True, 
        blank=True, 
        related_name='detalles_movimiento_asignados',
        help_text="Si se especifica, esta línea atiende/ingresa a este requerimiento específico."
    )
    
    es_stock_libre = models.BooleanField(default=False, help_text="Si es True, evita la asignación automática (FIFO) y entra como stock libre.")

    def subtotal(self):
        return self.cantidad * self.costo_unitario
        
    def __str__(self):
        return f"{self.cantidad} x {self.material.codigo}"
