from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.core.urls')), # Core (Dashboard + Usuarios)
    path('logistica/', include('apps.logistica.urls')),
    path('rrhh/', include('apps.rrhh.urls')),
    path('activos/', include('apps.activos.urls')),
    
    # URL de Login de Django por defecto (para no hacer una custom por ahora)
    path('accounts/', include('django.contrib.auth.urls')), 
]

# Servir archivos media en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)