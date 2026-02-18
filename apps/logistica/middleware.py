from .models import Almacen
from apps.core.models import PerfilUsuario

class AlmacenContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 1. Intentar obtener el ID de la sesión
        almacen_id = request.session.get('almacen_activo_id')
        request.almacen_activo = None

        # Lógica de Seguridad de Almacenes
        if request.user.is_authenticated:
            # 1. Obtener almacenes permitidos
            if request.user.is_superuser:
                qs_permitidos = Almacen.objects.all()
            else:
                # Si no tiene perfil, creamos uno vacío o asumimos vacío
                try:
                    perfil = request.user.perfil
                    qs_permitidos = perfil.almacenes.all()
                except PerfilUsuario.DoesNotExist:
                    qs_permitidos = Almacen.objects.none()

            # 2. Validar el almacén de la sesión
            if almacen_id:
                try:
                    almacen = Almacen.objects.get(id=almacen_id)
                    # Verificar si tiene permiso
                    if request.user.is_superuser or qs_permitidos.filter(id=almacen.id).exists():
                        request.almacen_activo = almacen
                    else:
                        # Si no tiene permiso, limpiamos la sesión (Security Breach)
                        del request.session['almacen_activo_id']
                        request.almacen_activo = None
                except Almacen.DoesNotExist:
                    # ID inválido en sesión
                    del request.session['almacen_activo_id']
            
            # Inyectamos la lista de permitidos en el request para usarla en vistas/context_processors
            request.almacenes_permitidos = qs_permitidos

            # --- NUEVO: AUTO-SELECCIÓN PARA NO-ADMINS ---
            # Si no es admin y no tiene almacén activo (está en el limbo), le asignamos el primero permitido
            if not request.user.is_superuser and not request.almacen_activo:
                primer = qs_permitidos.first()
                if primer:
                    request.session['almacen_activo_id'] = str(primer.id)
                    request.almacen_activo = primer

        
        response = self.get_response(request)
        return response