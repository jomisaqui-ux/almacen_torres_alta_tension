from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DetailView
from django.urls import reverse_lazy
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.utils import timezone
import qrcode
from io import BytesIO
import base64
from .models import Trabajador, EntregaEPP
from .forms import TrabajadorForm
from apps.core.models import Configuracion

class TrabajadorListView(ListView):
    """
    Vista para listar todos los trabajadores.
    """
    model = Trabajador
    template_name = 'rrhh/trabajador_list.html' # Le decimos qué template usar
    context_object_name = 'trabajadores' # Nombre para usar en el template
    paginate_by = 15 # Opcional: para paginar si hay muchos trabajadores
    ordering = ['apellidos', 'nombres'] # Ordenar por apellido y nombre

class TrabajadorCreateView(CreateView):
    model = Trabajador
    form_class = TrabajadorForm
    template_name = 'rrhh/trabajador_form.html'
    success_url = reverse_lazy('trabajador_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nuevo Trabajador'
        return context

class TrabajadorUpdateView(UpdateView):
    model = Trabajador
    form_class = TrabajadorForm
    template_name = 'rrhh/trabajador_form.html'
    success_url = reverse_lazy('trabajador_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Trabajador'
        return context

class TrabajadorDetailView(DetailView):
    model = Trabajador
    template_name = 'rrhh/trabajador_detail.html'
    context_object_name = 'trabajador'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Historial de EPPs (Leemos de la tabla consolidada EntregaEPP)
        context['epps'] = EntregaEPP.objects.filter(
            trabajador=self.object
        ).select_related('material', 'movimiento_origen').order_by('-fecha_entrega')
        
        # Activos en poder del trabajador (Deuda actual Global)
        context['activos_asignados'] = self.object.activos_actuales.select_related('material', 'kit').all().order_by('codigo')
        return context

def generar_constancia_pdf(request, pk):
    trabajador = get_object_or_404(Trabajador, pk=pk)
    activos_pendientes = trabajador.activos_actuales.all()
    
    # Definimos si es Libre Adeudo o Reporte de Deuda
    # Al ser una relación directa con Activo, esto busca en TODA la base de datos (Global)
    tiene_deuda = activos_pendientes.exists()
    
    if tiene_deuda:
        titulo = "REPORTE DE ADEUDOS PENDIENTES"
        subtitulo = "El trabajador mantiene los siguientes activos pendientes de devolución en los almacenes de la empresa:"
    else:
        titulo = "CONSTANCIA DE LIBRE ADEUDO"
        subtitulo = "Por medio de la presente se hace constar que el trabajador NO registra deudas de activos ni herramientas a la fecha."

    config = Configuracion.objects.first()

    # Generar Código QR
    qr_data = f"DOC: {titulo}\nTRABAJADOR: {trabajador.dni}\nFECHA: {timezone.now().strftime('%d/%m/%Y')}\nESTADO: {'CON DEUDA' if tiene_deuda else 'LIBRE'}"
    qr = qrcode.make(qr_data)
    buffer = BytesIO()
    qr.save(buffer, format="PNG")
    qr_img = base64.b64encode(buffer.getvalue()).decode()

    template_path = 'rrhh/constancia_pdf.html'
    context = {
        'trabajador': trabajador,
        'activos': activos_pendientes,
        'titulo': titulo,
        'subtitulo': subtitulo,
        'tiene_deuda': tiene_deuda,
        'config': config,
        'qr_code': qr_img
    }

    response = HttpResponse(content_type='application/pdf')
    filename = f"Constancia_{trabajador.dni}.pdf"
    response['Content-Disposition'] = f'inline; filename="{filename}"'

    template = get_template(template_path)
    html = template.render(context)
    pisa_status = pisa.CreatePDF(html, dest=response)

    if pisa_status.err:
       return HttpResponse('Error al generar PDF <pre>' + html + '</pre>')
    return response
