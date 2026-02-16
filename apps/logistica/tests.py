from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from decimal import Decimal
from django.core.files.uploadedfile import SimpleUploadedFile

# Importamos modelos del sistema
from apps.logistica.models import Almacen, Stock, Movimiento, DetalleMovimiento, Requerimiento, DetalleRequerimiento
from apps.proyectos.models import Proyecto
from apps.catalogo.models import Material, Categoria
from apps.rrhh.models import Trabajador
from apps.logistica.services import KardexService
from apps.logistica.forms import ImportarDatosForm

class KardexReservaTest(TestCase):
    """
    Pruebas de Integridad del Kardex y Reglas de Negocio.
    Foco: Protección de Stock Reservado.
    """

    def setUp(self):
        # 1. Configuración Básica (Usuario, Proyecto, Almacén, Material)
        User = get_user_model()
        self.user = User.objects.create_user('tester', 'test@obra.com', 'password')
        self.proyecto = Proyecto.objects.create(codigo='PRJ-001', nombre='Proyecto Demo')
        self.almacen = Almacen.objects.create(proyecto=self.proyecto, nombre='Almacén Central', codigo='ALM-01')
        self.categoria = Categoria.objects.create(nombre='Albañilería', codigo='ALB')
        self.material = Material.objects.create(codigo='CEM-001', descripcion='Cemento Sol', unidad_medida='BOL', categoria=self.categoria)
        self.trabajador = Trabajador.objects.create(nombres='JUAN', apellidos='PEREZ', dni='12345678', activo=True)

        # 2. Crear un Requerimiento Aprobado (Pendiente de Atención)
        # Solicitamos 100 bolsas
        self.req = Requerimiento.objects.create(
            proyecto=self.proyecto,
            solicitante='Ingeniero Residente',
            fecha_solicitud='2024-01-01',
            creado_por=self.user,
            estado='PENDIENTE'
        )
        self.det_req = DetalleRequerimiento.objects.create(
            requerimiento=self.req,
            material=self.material,
            cantidad_solicitada=100,
            cantidad_ingresada=0, # Aún no llega nada
            cantidad_atendida=0
        )

    def test_proteccion_de_reserva(self):
        """
        ESCENARIO CRÍTICO:
        1. Llegan 80 bolsas destinadas ESPECÍFICAMENTE al Requerimiento (Reserva).
        2. Llegan 10 bolsas como Stock Libre.
        3. Total Físico = 90.
        4. Alguien intenta sacar 20 bolsas "Sin Requerimiento" (Stock Libre).
        5. El sistema debe BLOQUEARLO porque solo hay 10 libres (las otras 80 son del Req).
        """
        
        # --- PASO 1: Ingreso de la Reserva (80 unidades) ---
        ingreso_reserva = Movimiento.objects.create(
            proyecto=self.proyecto,
            tipo='INGRESO_COMPRA',
            almacen_destino=self.almacen,
            requerimiento=self.req, # Vinculamos al Req
            creado_por=self.user,
            documento_referencia='FAC-001'
        )
        DetalleMovimiento.objects.create(
            movimiento=ingreso_reserva,
            material=self.material,
            cantidad=80,
            costo_unitario=25,
            requerimiento=self.req # Vinculación explícita
        )
        KardexService.confirmar_movimiento(ingreso_reserva.id)

        # Verificación intermedia
        self.det_req.refresh_from_db()
        stock_fisico = Stock.objects.get(almacen=self.almacen, material=self.material)
        print(f"\n[TEST] Stock Físico: {stock_fisico.cantidad} | Reservado Req: {self.det_req.cantidad_ingresada}")
        
        # --- PASO 2: Ingreso de Stock Libre (10 unidades) ---
        ingreso_libre = Movimiento.objects.create(
            proyecto=self.proyecto,
            tipo='INGRESO_COMPRA',
            almacen_destino=self.almacen,
            creado_por=self.user,
            documento_referencia='FAC-002'
        )
        DetalleMovimiento.objects.create(
            movimiento=ingreso_libre,
            material=self.material,
            cantidad=10,
            costo_unitario=25,
            es_stock_libre=True
        )
        KardexService.confirmar_movimiento(ingreso_libre.id)

        # --- PASO 3: Intento de "Robo" (Sacar 20 libres) ---
        # Matemáticas: Físico (90) - Reservado (80) = Libres (10).
        # Pedido: 20. -> ERROR ESPERADO.
        
        salida_robo = Movimiento.objects.create(
            proyecto=self.proyecto,
            tipo='SALIDA_OFICINA',
            almacen_origen=self.almacen,
            trabajador=self.trabajador,
            creado_por=self.user,
            documento_referencia='VALE-INTENTO'
        )
        DetalleMovimiento.objects.create(
            movimiento=salida_robo,
            material=self.material,
            cantidad=20, # Pido más de lo libre
            es_stock_libre=True
        )

        with self.assertRaises(ValidationError) as context:
            KardexService.confirmar_movimiento(salida_robo.id)
        
        print(f"[TEST] ÉXITO: El sistema bloqueó la salida. Mensaje: {context.exception.message}")

class ImportarDatosFormTest(TestCase):
    def test_archivo_valido_xlsx(self):
        """Verifica que el formulario acepte archivos .xlsx"""
        file_data = SimpleUploadedFile("datos.xlsx", b"contenido_dummy", content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        form = ImportarDatosForm(files={'archivo_excel': file_data})
        self.assertTrue(form.is_valid())

    def test_archivo_invalido_txt(self):
        """Verifica que el formulario rechace archivos que no sean .xlsx"""
        file_data = SimpleUploadedFile("datos.txt", b"contenido_dummy", content_type="text/plain")
        form = ImportarDatosForm(files={'archivo_excel': file_data})
        
        self.assertFalse(form.is_valid())
        self.assertIn('archivo_excel', form.errors)
        self.assertEqual(form.errors['archivo_excel'][0], "Formato inválido. Solo se permiten archivos Excel (.xlsx).")