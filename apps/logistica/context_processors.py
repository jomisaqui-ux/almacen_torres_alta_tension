from .models import Almacen

def contexto_almacen(request):
    return {
        'almacen_activo': getattr(request, 'almacen_activo', None),
        'lista_almacenes': Almacen.objects.all().order_by('-es_principal', 'nombre')
    }