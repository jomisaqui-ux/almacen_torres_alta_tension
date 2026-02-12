from .models import Configuracion

def empresa_config(request):
    """
    Inyecta la configuración de la empresa (Logo, Nombre) en todos los templates.
    """
    return {
        'config_empresa': Configuracion.objects.first()
    }