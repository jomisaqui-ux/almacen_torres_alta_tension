from .models import Almacen

class AlmacenContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 1. Intentar obtener el ID de la sesión
        almacen_id = request.session.get('almacen_activo_id')
        request.almacen_activo = None

        if almacen_id:
            try:
                # 2. Buscar el almacén y adjuntarlo al request (memoria)
                request.almacen_activo = Almacen.objects.filter(id=almacen_id).first()
            except:
                pass
        
        response = self.get_response(request)
        return response