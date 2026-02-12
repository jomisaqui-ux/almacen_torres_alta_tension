from django.urls import path
from .views import TrabajadorListView, TrabajadorCreateView, TrabajadorUpdateView, TrabajadorDetailView, generar_constancia_pdf

urlpatterns = [
    path('', TrabajadorListView.as_view(), name='trabajador_list'),
    path('nuevo/', TrabajadorCreateView.as_view(), name='trabajador_create'),
    path('editar/<uuid:pk>/', TrabajadorUpdateView.as_view(), name='trabajador_update'),
    path('detalle/<uuid:pk>/', TrabajadorDetailView.as_view(), name='trabajador_detail'),
    path('constancia/<uuid:pk>/', generar_constancia_pdf, name='generar_constancia_pdf'),
]