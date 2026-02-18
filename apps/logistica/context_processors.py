from .models import Almacen

def contexto_almacen(request):
    # Usamos la lista pre-calculada por el middleware si existe
    if hasattr(request, 'almacenes_permitidos'):
        lista = request.almacenes_permitidos.order_by('-es_principal', 'nombre')
    else:
        lista = Almacen.objects.none()

    return {
        'almacen_activo': getattr(request, 'almacen_activo', None),
        'lista_almacenes': lista
    }