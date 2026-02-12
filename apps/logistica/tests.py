from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.logistica.models import Almacen, Stock, Movimiento, DetalleMovimiento, Requerimiento, DetalleRequerimiento, Existencia
from apps.catalogo.models import Material, Categoria
from apps.proyectos.models import Proyecto, Tramo, Torre
from apps.logistica.services import KardexService

User = get_user_model()

class PruebasIntegralesLogistica(TestCase):
    def setUp(self):
        """
        Configuración inicial de datos maestros para las pruebas.
        """
        # 1. Usuario y Proyecto
        self.user = User.objects.create_user(username='tester', password='123')
        self.proyecto = Proyecto.objects.create(nombre="Proyecto Test", codigo="PRO-001", usa_control_costos=True)
        
        # 2. Infraestructura (Almacén y Torre)
        self.almacen = Almacen.objects.create(proyecto=self.proyecto, nombre="Almacén Central", codigo="ALM-001")
        self.tramo = Tramo.objects.create(proyecto=self.proyecto, nombre="Tramo 1", codigo="T1")
        self.torre = Torre.objects.create(tramo=self.tramo, codigo="T-01", tipo="SUSPENSION")
        
        # 3. Catálogo
        self.categoria = Categoria.objects.create(nombre="Materiales", codigo="MAT")
        self.material = Material.objects.create(
            codigo="CEMENTO", 
            descripcion="Cemento Portland", 
            unidad_medida="BLS",
            categoria=self.categoria
        )

    def test_ciclo_completo_requerimiento_ingreso_salida(self):
        """
        Prueba Integral del Flujo Principal:
        1. Crear Requerimiento (Pedido).
        2. Ingreso de Compra (Atendiendo el pedido) -> Sube Stock y actualiza Pedido.
        3. Salida a Obra (Consumiendo el pedido) -> Baja Stock y cierra Pedido.
        """
        
        # ====================================================
        # PASO 1: CREACIÓN DE REQUERIMIENTO
        # ====================================================
        req = Requerimiento.objects.create(
            proyecto=self.proyecto,
            solicitante="Ingeniero Residente",
            fecha_solicitud="2024-01-01",
            creado_por=self.user
        )
        
        DetalleRequerimiento.objects.create(
            requerimiento=req,
            material=self.material,
            cantidad_solicitada=50,
            cantidad_ingresada=0 # Aún no llega nada
        )
        
        self.assertEqual(req.estado, 'PENDIENTE')

        # ====================================================
        # PASO 2: INGRESO DE MATERIAL (COMPRA)
        # ====================================================
        # Simulamos que el proveedor trae el material para este requerimiento
        ingreso = Movimiento.objects.create(
            proyecto=self.proyecto,
            tipo='INGRESO_COMPRA',
            almacen_destino=self.almacen,
            requerimiento=req, # Vinculación explícita
            creado_por=self.user,
            nota_ingreso='NI-0001'
        )
        
        DetalleMovimiento.objects.create(
            movimiento=ingreso,
            material=self.material,
            cantidad=50,
            costo_unitario=20.00 # S/. 20 por bolsa
        )
        
        # Ejecutamos la lógica de negocio
        KardexService.confirmar_movimiento(ingreso.id)
        
        # Validaciones Paso 2
        stock = Stock.objects.get(almacen=self.almacen, material=self.material)
        self.assertEqual(stock.cantidad, 50, "El stock físico debió subir a 50")
        
        # Verificamos que el requerimiento sepa que ya llegó su material
        req.refresh_from_db()
        det_req = req.detalles.first()
        self.assertEqual(det_req.cantidad_ingresada, 50, "El requerimiento debe registrar el ingreso físico")

        # ====================================================
        # PASO 3: SALIDA A OBRA (DESPACHO)
        # ====================================================
        salida = Movimiento.objects.create(
            proyecto=self.proyecto,
            tipo='SALIDA_OBRA',
            almacen_origen=self.almacen,
            torre_destino=self.torre,
            requerimiento=req,
            creado_por=self.user,
            nota_ingreso='VS-0001'
        )
        
        DetalleMovimiento.objects.create(
            movimiento=salida,
            material=self.material,
            cantidad=50
        )
        
        KardexService.confirmar_movimiento(salida.id)
        
        # Validaciones Paso 3
        stock.refresh_from_db()
        self.assertEqual(stock.cantidad, 0, "El stock debió quedar en 0 tras la salida")
        
        req.refresh_from_db()
        self.assertEqual(req.estado, 'TOTAL', "El requerimiento debió pasar a estado ATENDIDO TOTAL")
