from django.urls import path
from .views import ActivoListView, ActivoUpdateView, ActivoDetailView, asignar_activo, devolver_activo, KitListView, KitCreateView, asignar_kit, administrar_kit

urlpatterns = [
    path('', ActivoListView.as_view(), name='activo_list'),
    path('editar/<uuid:pk>/', ActivoUpdateView.as_view(), name='activo_update'),
    path('detalle/<uuid:pk>/', ActivoDetailView.as_view(), name='activo_detail'),
    path('asignar/<uuid:pk>/', asignar_activo, name='activo_asignar'),
    path('devolver/<uuid:pk>/', devolver_activo, name='activo_devolver'),
    
    # URLs de Kits
    path('kits/', KitListView.as_view(), name='kit_list'),
    path('kits/nuevo/', KitCreateView.as_view(), name='kit_create'),
    path('kits/asignar/<uuid:pk>/', asignar_kit, name='kit_asignar'),
    path('kits/administrar/<uuid:pk>/', administrar_kit, name='kit_administrar'),
]