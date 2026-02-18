from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db.models import Sum, Count, F
from django.db.models.functions import TruncDate
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal # <--- ESTA IMPORTACIÓN ES CRÍTICA
from django.contrib.auth import get_user_model
from .forms import UsuarioForm

# Importamos modelos para sacar métricas
from apps.proyectos.models import Proyecto, Torre
from apps.logistica.models import Movimiento, Existencia, Stock, Requerimiento

@login_required
def dashboard(request):
    """
    Vista principal con KPIs estratégicos.
    """
    # 1. Total invertido en Stock (Suma de todos los proyectos)
    # Nota: Esto suma el valor financiero inmovilizado en almacenes
    valor_stock_total = Existencia.objects.aggregate(
        total=Sum(F('stock_total_proyecto') * F('costo_promedio'))
    )['total'] or 0

    # 2. Cantidad de Movimientos Pendientes (Borradores)
    pendientes = Movimiento.objects.filter(estado='BORRADOR').count()

    # 3. Costo asignado a Torres (Gasto real ejecutado)
    # Buscamos movimientos de salida a obra confirmados y sumamos sus detalles
    # (Esta consulta es simplificada, en producción usaríamos una tabla de hechos pre-calculada)

    # 4. Alertas de Stock (Stock físico <= Mínimo configurado)
    # CRITICO: Stock actual es menor o igual al mínimo
    alertas_criticas = Stock.objects.filter(
        cantidad__lte=F('cantidad_minima'), 
        cantidad_minima__gt=0
    ).count()

    # ADVERTENCIA: Stock es mayor al mínimo pero menor al mínimo + 20%
    alertas_advertencia = Stock.objects.filter(
        cantidad__gt=F('cantidad_minima'),
        cantidad__lte=F('cantidad_minima') * Decimal('1.2'),
        cantidad_minima__gt=0
    ).count()

    # 5. Requerimientos Pendientes (Solicitudes de obra no atendidas)
    req_pendientes = Requerimiento.objects.filter(estado__in=['PENDIENTE', 'PARCIAL']).count()
    
    # 6. DATOS PARA EL GRÁFICO (Últimos 7 días)
    hoy = timezone.now().date()
    inicio_semana = hoy - timedelta(days=6)
    
    # Estructura base para los 7 días
    labels = []
    data_ingresos = []
    data_salidas = []
    datos_por_dia = {}

    for i in range(7):
        dia = inicio_semana + timedelta(days=i)
        labels.append(dia.strftime('%d/%m'))
        datos_por_dia[dia] = {'ingresos': 0, 'salidas': 0}

    # Consulta agrupada
    movimientos_semana = Movimiento.objects.filter(
        fecha__date__gte=inicio_semana,
        estado='CONFIRMADO'
    ).annotate(dia=TruncDate('fecha')).values('dia', 'tipo').annotate(total=Count('id'))

    for m in movimientos_semana:
        dia = m['dia']
        if dia in datos_por_dia:
            if 'INGRESO' in m['tipo'] or 'DEVOLUCION' in m['tipo']:
                datos_por_dia[dia]['ingresos'] += m['total']
            else:
                datos_por_dia[dia]['salidas'] += m['total']

    # Aplanar listas para Chart.js
    for i in range(7):
        dia = inicio_semana + timedelta(days=i)
        data_ingresos.append(datos_por_dia[dia]['ingresos'])
        data_salidas.append(datos_por_dia[dia]['salidas'])

    context = {
        'valor_stock': valor_stock_total,
        'pendientes': pendientes,
        'proyectos_activos': Proyecto.objects.filter(activo=True).count(),
        'torres_total': Torre.objects.count(),
        'alertas_stock': alertas_criticas,      # Rojo
        'alertas_advertencia': alertas_advertencia, # Amarillo
        'req_pendientes': req_pendientes,
        # Datos Gráfico
        'chart_labels': labels,
        'chart_ingresos': data_ingresos,
        'chart_salidas': data_salidas,
    }
    return render(request, 'core/dashboard.html', context)

# ==========================================
# GESTIÓN DE USUARIOS (ADMINISTRACIÓN)
# ==========================================

User = get_user_model()

class SuperUserRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_superuser

class UsuarioListView(LoginRequiredMixin, SuperUserRequiredMixin, ListView):
    model = User
    template_name = 'core/usuario_list.html'
    context_object_name = 'usuarios'
    queryset = User.objects.all().order_by('username')

class UsuarioCreateView(LoginRequiredMixin, SuperUserRequiredMixin, CreateView):
    model = User
    form_class = UsuarioForm
    template_name = 'core/usuario_form.html'
    success_url = reverse_lazy('usuario_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Crear Nuevo Usuario'
        return context

class UsuarioUpdateView(LoginRequiredMixin, SuperUserRequiredMixin, UpdateView):
    model = User
    form_class = UsuarioForm
    template_name = 'core/usuario_form.html'
    success_url = reverse_lazy('usuario_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = f'Editar Usuario: {self.object.username}'
        return context

class UsuarioDeleteView(LoginRequiredMixin, SuperUserRequiredMixin, DeleteView):
    model = User
    template_name = 'core/usuario_confirm_delete.html'
    success_url = reverse_lazy('usuario_list')