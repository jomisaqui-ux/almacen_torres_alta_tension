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
    reset_database,
    cerrar_requerimiento,
    exportar_inventario_excel,
    exportar_kardex_excel
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
    path('requerimientos/<uuid:req_id>/', requerimiento_detail, name='requerimiento_detail'),
    path('requerimientos/cerrar/<uuid:req_id>/', cerrar_requerimiento, name='cerrar_requerimiento'),
    path('inventario/exportar/', exportar_inventario_excel, name='exportar_inventario_excel'),
    path('kardex/exportar/<uuid:almacen_id>/<uuid:material_id>/', exportar_kardex_excel, name='exportar_kardex_excel'),
    path('api/stock/<uuid:almacen_id>/<uuid:material_id>/', api_consultar_stock, name='api_consultar_stock'),
    path('config/reset-db/', reset_database, name='reset_database'),
]