from django.urls import path
from .views import(
    generar_vale_pdf,
    inventario_list,
    operacion_almacen,
    movimiento_list,
    confirmar_movimiento_web,
    anular_movimiento,
    editar_movimiento,
    kardex_producto,
    api_consultar_stock,
    requerimiento_list,
    requerimiento_detail,
    requerimiento_create,
    reset_database,
    cerrar_requerimiento,
    generar_requerimiento_pdf, # <--- Importar vista
    exportar_inventario_excel,
    exportar_kardex_excel,
    api_crear_trabajador,
    api_buscar_trabajador,
    api_listar_activos,
    cambiar_almacen_sesion,
    limpiar_almacen_sesion, # <--- Importar nueva vista
    exportar_activos_externos_excel,
    reporte_transacciones, # <--- Importar nueva vista
    reporte_consumo_torre, # <--- Nuevos reportes
    reporte_backlog,
    reporte_epp_trabajador,
    reporte_reposicion,
    importar_datos_excel,
    descargar_plantilla_importacion
)

urlpatterns = [
    path('vale/<uuid:movimiento_id>/', generar_vale_pdf, name='generar_vale_pdf'),
    path('inventario/', inventario_list, name='inventario_list'),
    path('operacion/<str:tipo_accion>/<uuid:almacen_id>/', operacion_almacen, name='operacion_almacen'),
    path('movimientos/', movimiento_list, name='movimiento_list'),
    path('movimiento/confirmar/<uuid:movimiento_id>/', confirmar_movimiento_web, name='confirmar_movimiento_web'),
    path('movimiento/anular/<uuid:movimiento_id>/', anular_movimiento, name='anular_movimiento'),
    path('movimiento/editar/<uuid:movimiento_id>/', editar_movimiento, name='editar_movimiento'),
    path('kardex/<uuid:almacen_id>/<uuid:material_id>/', kardex_producto, name='kardex_producto'),
    path('requerimientos/', requerimiento_list, name='requerimiento_list'),
    path('requerimientos/nuevo/', requerimiento_create, name='requerimiento_create'),
    path('requerimientos/<uuid:req_id>/', requerimiento_detail, name='requerimiento_detail'),
    path('requerimientos/cerrar/<uuid:req_id>/', cerrar_requerimiento, name='cerrar_requerimiento'),
    path('requerimientos/pdf/<uuid:req_id>/', generar_requerimiento_pdf, name='generar_requerimiento_pdf'), # <--- Nueva ruta
    path('inventario/exportar/', exportar_inventario_excel, name='exportar_inventario_excel'),
    path('exportar/activos-externos/', exportar_activos_externos_excel, name='exportar_activos_externos_excel'),
    path('kardex/exportar/<uuid:almacen_id>/<uuid:material_id>/', exportar_kardex_excel, name='exportar_kardex_excel'),
    path('reportes/transacciones/', reporte_transacciones, name='reporte_transacciones'), # <--- Nueva ruta
    path('reportes/consumo-torre/', reporte_consumo_torre, name='reporte_consumo_torre'),
    path('reportes/backlog/', reporte_backlog, name='reporte_backlog'),
    path('reportes/epp-trabajador/', reporte_epp_trabajador, name='reporte_epp_trabajador'),
    path('reportes/reposicion/', reporte_reposicion, name='reporte_reposicion'),
    path('api/stock/<uuid:almacen_id>/<uuid:material_id>/', api_consultar_stock, name='api_consultar_stock'),
    path('api/trabajador/nuevo/', api_crear_trabajador, name='api_crear_trabajador'),
    path('api/trabajador/buscar/', api_buscar_trabajador, name='api_buscar_trabajador'),
    path('api/activos/listar/', api_listar_activos, name='api_listar_activos'),
    path('config/reset-db/', reset_database, name='reset_database'),
    path('config/cambiar-almacen/<uuid:almacen_id>/', cambiar_almacen_sesion, name='cambiar_almacen_sesion'), # <--- Nueva ruta
    path('config/limpiar-almacen/', limpiar_almacen_sesion, name='limpiar_almacen_sesion'),
    path('config/importar-datos/', importar_datos_excel, name='importar_datos_excel'),
    path('config/descargar-plantilla/', descargar_plantilla_importacion, name='descargar_plantilla_importacion'),
]