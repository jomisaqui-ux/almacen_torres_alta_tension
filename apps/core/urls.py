from django.urls import path
from .views import dashboard, UsuarioListView, UsuarioCreateView, UsuarioUpdateView, UsuarioDeleteView

urlpatterns = [
    path('', dashboard, name='dashboard'),
    path('usuarios/', UsuarioListView.as_view(), name='usuario_list'),
    path('usuarios/nuevo/', UsuarioCreateView.as_view(), name='usuario_create'),
    path('usuarios/editar/<int:pk>/', UsuarioUpdateView.as_view(), name='usuario_update'),
    path('usuarios/eliminar/<int:pk>/', UsuarioDeleteView.as_view(), name='usuario_delete'),
]