from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, CreateView, UpdateView, DetailView
from django.urls import reverse_lazy
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import Activo, AsignacionActivo, Kit
from .forms import ActivoForm, AsignacionForm, DevolucionForm, KitForm, AsignarKitForm
from apps.logistica.models import Movimiento, DetalleMovimiento, Almacen
from apps.logistica.services import KardexService

class ActivoListView(ListView):
    model = Activo
    template_name = 'activos/activo_list.html'
    context_object_name = 'activos'
    paginate_by = 20
    ordering = ['codigo']

    def get_queryset(self):
        # Optimizamos con select_related para traer la ubicación en una sola consulta
        queryset = super().get_queryset().select_related('ubicacion', 'trabajador_asignado')
        q = self.request.GET.get('q')
        estado = self.request.GET.get('estado')
        ubicacion = self.request.GET.get('ubicacion') # Nuevo filtro

        # FILTRO AUTOMÁTICO POR SESIÓN
        if hasattr(self.request, 'almacen_activo') and self.request.almacen_activo:
            # Ahora mostramos:
            # 1. Lo que está físicamente (DISPONIBLE/MANTENIMIENTO)
            # 2. Lo que salió de aquí a campo (ASIGNADO)
            # Gracias al cambio en services.py, ambos tienen ubicacion=almacen_activo
            queryset = queryset.filter(
                Q(ubicacion=self.request.almacen_activo) |
                Q(estado='EN_TRANSITO', ubicacion=self.request.almacen_activo)
            )

        if q:
            queryset = queryset.filter(
                Q(codigo__icontains=q) | 
                Q(nombre__icontains=q) |
                Q(serie__icontains=q)
            )
        
        if estado:
            queryset = queryset.filter(estado=estado)
        
        if ubicacion:
            queryset = queryset.filter(ubicacion_id=ubicacion)
            
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['q'] = self.request.GET.get('q', '')
        context['estado_filtro'] = self.request.GET.get('estado', '')
        context['ubicacion_filtro'] = self.request.GET.get('ubicacion', '')
        context['estados'] = Activo.ESTADOS # Pasamos las opciones al template
        context['almacenes'] = Almacen.objects.all() # Para llenar el select de filtro
        return context

class ActivoUpdateView(UpdateView):
    model = Activo
    form_class = ActivoForm
    template_name = 'activos/activo_form.html'
    success_url = reverse_lazy('activo_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Activo'
        return context

class ActivoDetailView(DetailView):
    model = Activo
    template_name = 'activos/activo_detail.html'
    context_object_name = 'activo'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Ordenamos el historial del más reciente al más antiguo
        context['historial'] = self.object.historial_asignaciones.select_related('trabajador').order_by('-fecha_asignacion')
        context['pertenece_a_kit'] = self.object.kit  # Pasamos la información del kit al template
        return context

def asignar_activo(request, pk):
    activo = get_object_or_404(Activo, pk=pk)
    
    if activo.kit:
        messages.error(request, f'El activo pertenece al Kit "{activo.kit.nombre}". Debe asignar el Kit completo o retirar el ítem del Kit primero.')
        return redirect('activo_list')

    if activo.estado != 'DISPONIBLE':
        messages.warning(request, f'El activo {activo.codigo} no está disponible para asignación.')
        return redirect('activo_list')

    if request.method == 'POST':
        form = AsignacionForm(request.POST)
        if form.is_valid():
            trabajador = form.cleaned_data['trabajador']
            observacion = form.cleaned_data['observacion']
            
            try:
                with transaction.atomic():
                    # INTENTO AUTOMÁTICO: Generar Movimiento de Salida (Documento VS)
                    # Usamos SALIDA_OFICINA para que no exija Torre, pero vinculamos al trabajador.
                    if activo.material and activo.ubicacion:
                        mov = Movimiento.objects.create(
                            proyecto=activo.ubicacion.proyecto,
                            tipo='SALIDA_OFICINA', # Salida interna (Asignación)
                            almacen_origen=activo.ubicacion,
                            trabajador=trabajador,
                            fecha=timezone.now(),
                            creado_por=request.user,
                            observacion=f"Asignación directa de activo: {observacion}",
                            documento_referencia=f"ASIG-{activo.codigo}"
                        )
                        
                        DetalleMovimiento.objects.create(
                            movimiento=mov,
                            material=activo.material,
                            cantidad=1,
                            costo_unitario=activo.valor_compra,
                            activo=activo # El servicio se encargará de cambiar estado a ASIGNADO
                        )
                        
                        KardexService.confirmar_movimiento(mov.id)
                        messages.success(request, f'Activo asignado y Vale de Salida {mov.nota_ingreso} generado.')
                    else:
                        # FALLBACK MANUAL (Si el activo no tiene material vinculado o ubicación)
                        activo.estado = 'ASIGNADO'
                        activo.trabajador_asignado = trabajador
                        activo.save()
                        
                        AsignacionActivo.objects.create(
                            activo=activo,
                            trabajador=trabajador,
                            observacion_entrega=observacion
                        )
                        messages.warning(request, f'Activo asignado manualmente (Sin Vale de Salida porque falta material/ubicación).')
                
                return redirect('activo_list')
            except Exception as e:
                messages.error(request, f'Error al asignar: {e}')
    else:
        form = AsignacionForm()

    context = {
        'activo': activo,
        'form': form,
        'titulo': f'Asignar Activo: {activo.nombre}'
    }
    return render(request, 'activos/asignar_form.html', context)

def devolver_activo(request, pk):
    activo = get_object_or_404(Activo, pk=pk)
    
    if activo.estado != 'ASIGNADO':
        messages.warning(request, f'El activo {activo.codigo} no está asignado actualmente.')
        return redirect('activo_list')

    if request.method == 'POST':
        form = DevolucionForm(request.POST)
        if form.is_valid():
            observacion = form.cleaned_data['observacion']
            
            try:
                with transaction.atomic():
                    # DETERMINAR ALMACÉN DE RETORNO
                    almacen_destino = getattr(request, 'almacen_activo', None)
                    if not almacen_destino:
                        almacen_destino = Almacen.objects.filter(es_principal=True).first()
                    if not almacen_destino:
                        almacen_destino = activo.ubicacion

                    # INTENTO AUTOMÁTICO: Generar Movimiento de Devolución (Documento NI)
                    if activo.material and almacen_destino:
                            # Crear Movimiento de Devolución
                            mov = Movimiento.objects.create(
                                proyecto=almacen_destino.proyecto,
                                tipo='DEVOLUCION_OBRA',
                                almacen_destino=almacen_destino,
                                fecha=timezone.now(),
                                creado_por=request.user,
                                observacion=f"Devolución: {observacion}",
                                documento_referencia=f"RET-{activo.codigo}"
                            )
                            
                            # Crear Detalle
                            DetalleMovimiento.objects.create(
                                movimiento=mov,
                                material=activo.material,
                                cantidad=1,
                                costo_unitario=activo.valor_compra,
                                activo=activo # El servicio se encargará de liberar activo y cerrar asignación
                            )
                            
                            # Confirmar para afectar stock
                            KardexService.confirmar_movimiento(mov.id)
                            messages.success(request, f'Activo devuelto y Vale {mov.nota_ingreso} generado en {almacen_destino.nombre}.')
                    else:
                        # FALLBACK MANUAL (Si falla lo anterior)
                        asignacion = AsignacionActivo.objects.filter(activo=activo, fecha_devolucion__isnull=True).last()
                        if asignacion:
                            asignacion.fecha_devolucion = timezone.now()
                            asignacion.observacion_devolucion = observacion
                            asignacion.save()
                        
                        activo.estado = 'DISPONIBLE'
                        activo.trabajador_asignado = None
                        activo.ubicacion = almacen_destino
                        activo.save()
                        messages.warning(request, f'Activo devuelto manualmente (Sin Vale NI porque falta material/almacén).')

                return redirect('activo_list')
            except Exception as e:
                messages.error(request, f'Error al devolver: {e}')
    else:
        form = DevolucionForm()

    context = {
        'activo': activo,
        'form': form,
        'titulo': f'Devolución de Activo: {activo.nombre}'
    }
    return render(request, 'activos/devolver_form.html', context)

# ==========================================
# GESTIÓN DE KITS
# ==========================================

class KitListView(ListView):
    model = Kit
    template_name = 'activos/kit_list.html'
    context_object_name = 'kits'

class KitCreateView(CreateView):
    model = Kit
    form_class = KitForm
    template_name = 'activos/kit_form.html'
    success_url = reverse_lazy('kit_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Crear Nuevo Kit'
        return context

def asignar_kit(request, pk):
    kit = get_object_or_404(Kit, pk=pk)
    componentes = kit.componentes.all()
    
    # Validar que el kit tenga componentes
    if not componentes.exists():
        messages.error(request, 'Este kit está vacío. Agregue activos al kit editándolos individualmente.')
        return redirect('kit_list')

    # Validar disponibilidad completa
    no_disponibles = componentes.exclude(estado='DISPONIBLE')
    if no_disponibles.exists():
        nombres = ", ".join([a.nombre for a in no_disponibles])
        messages.error(request, f'No se puede asignar el kit. Los siguientes ítems no están disponibles: {nombres}')
        return redirect('kit_list')

    if request.method == 'POST':
        form = AsignarKitForm(request.POST)
        if form.is_valid():
            trabajador = form.cleaned_data['trabajador']
            observacion = form.cleaned_data['observacion']
            
            try:
                with transaction.atomic():
                    # 1. Bloquear filas (SELECT FOR UPDATE) para evitar condiciones de carrera
                    # Obtenemos los componentes nuevamente pero asegurando exclusividad
                    componentes_lock = Activo.objects.select_for_update().filter(kit=kit)
                    
                    # 2. Re-validar disponibilidad estricta dentro de la transacción
                    items_ocupados = [a.nombre for a in componentes_lock if a.estado != 'DISPONIBLE']
                    if items_ocupados:
                        raise ValidationError(f"Los siguientes ítems cambiaron de estado y ya no están disponibles: {', '.join(items_ocupados)}")

                    # 3. Procesar asignación
                    for activo in componentes_lock:
                        activo.estado = 'ASIGNADO'
                        activo.trabajador_asignado = trabajador
                        activo.save()
                        
                        AsignacionActivo.objects.create(
                            activo=activo,
                            trabajador=trabajador,
                            observacion_entrega=f"ASIGNACIÓN DE KIT {kit.codigo}: {observacion}"
                        )
                messages.success(request, f'Kit {kit.nombre} asignado exitosamente a {trabajador}.')
                return redirect('kit_list')
            except ValidationError as e:
                messages.error(request, f'Validación fallida: {e.message}')
            except Exception as e:
                messages.error(request, f'Error al procesar el kit: {e}')
    else:
        form = AsignarKitForm()
    
    context = {
        'kit': kit,
        'componentes': componentes,
        'form': form
    }
    return render(request, 'activos/asignar_kit.html', context)

def administrar_kit(request, pk):
    """
    Vista para agregar o quitar activos de un Kit.
    """
    kit = get_object_or_404(Kit, pk=pk)
    
    if request.method == 'POST':
        accion = request.POST.get('accion')
        activo_id = request.POST.get('activo_id')
        
        if activo_id:
            activo = get_object_or_404(Activo, id=activo_id)
            
            if accion == 'agregar':
                if activo.kit:
                    messages.error(request, f'El activo ya pertenece al kit {activo.kit.codigo}.')
                else:
                    activo.kit = kit
                    activo.save()
                    messages.success(request, f'{activo.codigo} agregado al kit.')
            
            elif accion == 'quitar':
                activo.kit = None
                activo.save()
                messages.warning(request, f'{activo.codigo} retirado del kit.')
                
        return redirect('kit_administrar', pk=pk)

    # Contexto para el template
    context = {
        'kit': kit,
        'componentes': kit.componentes.all().order_by('codigo'),
        'disponibles': Activo.objects.filter(kit__isnull=True, estado='DISPONIBLE').order_by('codigo')
    }
    return render(request, 'activos/kit_componentes.html', context)
