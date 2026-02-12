from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import HttpResponse, JsonResponse
from django.template.loader import get_template
from django.db.models import Prefetch, Q, F
from django.utils import timezone
from decimal import Decimal
from xhtml2pdf import pisa
import qrcode
from io import BytesIO
import base64
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill

# Importamos modelos y formularios locales
from .models import Movimiento, DetalleMovimiento, Stock, Almacen, Material, Proyecto, Requerimiento, Existencia, DetalleRequerimiento
from .forms import MovimientoForm, DetalleMovimientoFormSet
from .services import KardexService
from apps.core.models import Configuracion

# ==========================================
# 1. REPORTES Y PDF
# ==========================================

def generar_vale_pdf(request, movimiento_id):
    movimiento = get_object_or_404(Movimiento, id=movimiento_id)
    config = Configuracion.objects.first()
    
    # Generar Código QR con datos clave
    qr_data = f"DOC: {movimiento.nota_ingreso or 'S/N'}\nFECHA: {movimiento.fecha.strftime('%d/%m/%Y')}\nREF: {movimiento.id}"
    qr = qrcode.make(qr_data)
    buffer = BytesIO()
    qr.save(buffer, format="PNG")
    qr_img = base64.b64encode(buffer.getvalue()).decode()

    template_path = 'logistica/vale_pdf.html'
    context = {
        'movimiento': movimiento,
        'detalles': movimiento.detalles.all(),
        'config': config,
        'qr_code': qr_img,
        'titulo': f"VALE DE {movimiento.get_tipo_display().upper()}"
    }

    response = HttpResponse(content_type='application/pdf')
    nombre_archivo = movimiento.nota_ingreso if movimiento.nota_ingreso else movimiento.codigo_visual()
    filename = f"Vale_{nombre_archivo}.pdf"
    response['Content-Disposition'] = f'inline; filename="{filename}"'

    template = get_template(template_path)
    html = template.render(context)

    pisa_status = pisa.CreatePDF(html, dest=response)

    if pisa_status.err:
       return HttpResponse('Error al generar PDF <pre>' + html + '</pre>')
    return response

# ==========================================
# 2. VISTAS DE INVENTARIO Y LISTADOS
# ==========================================

def inventario_list(request):
    """
    Reporte de Stock Físico con Búsqueda Inteligente.
    """
    query = request.GET.get('q')
    filtro = request.GET.get('filtro') # Nuevo parámetro para filtrar alertas

    stocks_filter = Stock.objects.select_related('material')

    if query:
        stocks_filter = stocks_filter.filter(
            Q(material__codigo__icontains=query) |
            Q(material__descripcion__icontains=query)
        )
    
    # Si viene del dashboard (clic en tarjeta roja), filtramos solo los críticos
    if filtro == 'critico':
        stocks_filter = stocks_filter.filter(cantidad__lte=F('cantidad_minima'), cantidad_minima__gt=0)
    elif filtro == 'advertencia':
        stocks_filter = stocks_filter.filter(
            cantidad__gt=F('cantidad_minima'),
            cantidad__lte=F('cantidad_minima') * Decimal('1.2'),
            cantidad_minima__gt=0
        )

    almacenes = Almacen.objects.prefetch_related(
        Prefetch('stocks', queryset=stocks_filter)
    ).distinct()

    context = {
        'almacenes': almacenes,
        'busqueda': query
    }
    return render(request, 'logistica/inventario.html', context)

def movimiento_list(request):
    """
    Pantalla Principal de Movimientos.
    """
    # Filtramos los últimos 50 para no saturar
    movimientos = Movimiento.objects.select_related(
        'almacen_origen', 
        'almacen_destino', 
        'torre_destino',
        'proyecto'
    ).order_by('-fecha')[:50]
    
    context = {
        'movimientos': movimientos
    }
    return render(request, 'logistica/movimiento_list.html', context)

def kardex_producto(request, almacen_id, material_id):
    """
    Muestra la historia clínica de un material específico en un almacén.
    """
    almacen = get_object_or_404(Almacen, id=almacen_id)
    material = get_object_or_404(Material, id=material_id)

    # 1. Obtener Stock Actual (Punto de partida para cálculo inverso)
    stock_item = Stock.objects.filter(almacen=almacen, material=material).first()
    saldo_actual = stock_item.cantidad if stock_item else Decimal(0)

    # 2. Obtener movimientos (Del más reciente al más antiguo)
    movimientos = DetalleMovimiento.objects.filter(
        material=material,
        movimiento__estado='CONFIRMADO'
    ).filter(
        Q(movimiento__almacen_origen=almacen) | 
        Q(movimiento__almacen_destino=almacen)
    ).select_related('movimiento', 'movimiento__creado_por').order_by('-movimiento__fecha')

    movimientos_visuales = []
    
    # 3. Procesamiento en memoria (Cálculo de Saldos y Banderas)
    for detalle in movimientos:
        mov = detalle.movimiento
        tipo_original = mov.tipo
        
        # A. Determinar si es Ingreso o Salida PARA ESTE ALMACÉN
        es_ingreso = False
        es_salida = False
        tipo_visual = tipo_original
        
        # FIX ROBUSTO: Convertimos a string para asegurar la comparación (UUID vs Str)
        id_actual = str(almacen.id)
        id_destino = str(mov.almacen_destino_id) if mov.almacen_destino_id else ''
        id_origen = str(mov.almacen_origen_id) if mov.almacen_origen_id else ''

        soy_destino = (id_destino == id_actual)
        soy_origen = (id_origen == id_actual)

        # Lógica de Transferencias y Ajustes
        if soy_destino:
            # Soy el destino -> Es un INGRESO
            es_ingreso = True
            if 'SALIDA' in tipo_original:
                tipo_visual = 'TRANSFERENCIA_ENTRADA' # Corrección de etiqueta
        elif soy_origen:
            # Soy el origen -> Es una SALIDA
            es_salida = True
        else:
            # Fallback: Si no soy ni origen ni destino (ej: admin global o error de datos)
            if 'INGRESO' in tipo_original or 'DEVOLUCION' in tipo_original or 'ENTRADA' in tipo_original:
                es_ingreso = True
            elif 'SALIDA' in tipo_original or 'CONSUMO' in tipo_original:
                es_salida = True

        # B. Asignar atributos al objeto detalle (para usar en el template)
        detalle.es_ingreso = es_ingreso
        detalle.es_salida = es_salida
        detalle.tipo_visual = tipo_visual
        
        # FIX FINAL: Valores numéricos explícitos (Decimal o 0)
        # Si es ingreso, la salida ES CERO. Si es salida, la entrada ES CERO.
        detalle.cantidad_entrada = detalle.cantidad if es_ingreso else Decimal(0)
        detalle.cantidad_salida = detalle.cantidad if es_salida else Decimal(0)
        
        detalle.saldo_calculado = saldo_actual

        # C. Recalcular saldo para la siguiente iteración (hacia el pasado)
        # Si fue ingreso, antes tenía MENOS. Si fue salida, antes tenía MÁS.
        if es_ingreso:
            saldo_actual -= detalle.cantidad
        elif es_salida:
            saldo_actual += detalle.cantidad
            
        movimientos_visuales.append(detalle)

    context = {
        'almacen': almacen,
        'material': material,
        'movimientos': movimientos_visuales
    }
    return render(request, 'logistica/kardex_producto.html', context)

def requerimiento_list(request):
    """
    Lista de seguimiento de Requerimientos (Pedidos de Obra).
    """
    requerimientos = Requerimiento.objects.select_related('proyecto', 'creado_por').order_by('-fecha_solicitud')
    
    context = {
        'requerimientos': requerimientos
    }
    return render(request, 'logistica/requerimiento_list.html', context)

def requerimiento_detail(request, req_id):
    """
    Ver el progreso de un requerimiento: Qué se pidió vs Qué se ha entregado.
    """
    req = get_object_or_404(Requerimiento, id=req_id)
    # Salidas confirmadas que han atendido este requerimiento
    salidas = req.salidas.filter(estado='CONFIRMADO').order_by('-fecha')
    
    context = {
        'req': req,
        'salidas': salidas
    }
    return render(request, 'logistica/requerimiento_detail.html', context)

# ==========================================
# 3. CREACIÓN Y GESTIÓN DE MOVIMIENTOS
# ==========================================

def operacion_almacen(request, tipo_accion, almacen_id):
    """
    Vista principal para registrar Ingresos y Salidas.
    CORRECCIONES: Usuario, Proyecto, Filtros y GENERADOR DOBLE (NI/VS).
    """
    if str(almacen_id) == '00000000-0000-0000-0000-000000000000':
        almacen = None
    else:
        almacen = get_object_or_404(Almacen, id=almacen_id)
    
    tipo_default = 'SALIDA_OBRA' if tipo_accion == 'salida' else 'INGRESO_COMPRA'
    if request.GET.get('tipo'):
        tipo_default = request.GET.get('tipo')

    initial_data = {
        'almacen_origen': almacen,
        'tipo': tipo_default
    }

    if request.method == 'POST':
        form = MovimientoForm(request.POST, tipo_accion=tipo_accion)
        formset = DetalleMovimientoFormSet(request.POST, form_kwargs={'tipo_accion': tipo_accion})
        if form.is_valid():
            nuevo_mov = form.save(commit=False)
            
            # 1. ASIGNAR USUARIO
            nuevo_mov.creado_por = request.user 
            
            # 2. ASIGNAR PROYECTO
            if almacen and almacen.proyecto:
                nuevo_mov.proyecto = almacen.proyecto
            else:
                # Fallback por si el almacén no tiene proyecto
                # Intentamos obtener el proyecto del almacén seleccionado en el formulario
                almacen_seleccionado = nuevo_mov.almacen_origen or nuevo_mov.almacen_destino
                nuevo_mov.proyecto = almacen_seleccionado.proyecto if almacen_seleccionado else Proyecto.objects.first()

            # 3. GENERADOR DE CÓDIGO AUTOMÁTICO (NI o VS)
            # Solo generamos si no tiene uno manual
            if not nuevo_mov.nota_ingreso:
                es_salida = 'SALIDA' in nuevo_mov.tipo or 'CONSUMO' in nuevo_mov.tipo
                es_ingreso = 'INGRESO' in nuevo_mov.tipo or 'DEVOLUCION' in nuevo_mov.tipo or 'ENTRADA' in nuevo_mov.tipo
                
                prefix = None
                if es_salida:
                    prefix = 'VS-'
                elif es_ingreso:
                    prefix = 'NI-'
                
                if prefix:
                    # Buscamos el último código de ese tipo (VS o NI)
                    ultimo = Movimiento.objects.filter(nota_ingreso__startswith=prefix).order_by('-nota_ingreso').first()
                    
                    contador = 1
                    if ultimo:
                        try:
                            # Ejemplo: NI-0007 -> toma "0007" -> suma 1 -> 8
                            contador = int(ultimo.nota_ingreso.split('-')[1]) + 1
                        except:
                            contador = 1
                    
                    # Asignamos: NI-0008 o VS-0003
                    nuevo_mov.nota_ingreso = f"{prefix}{contador:04d}"

            # --- GUARDAR ---
            nuevo_mov.save()
            form.save_m2m() 
            
            formset = DetalleMovimientoFormSet(request.POST, instance=nuevo_mov, form_kwargs={'tipo_accion': tipo_accion})
            if formset.is_valid():
                formset.save()
                messages.success(request, f'Operación {nuevo_mov.nota_ingreso} registrada exitosamente.')
                return redirect('movimiento_list')
            else:
                nuevo_mov.delete()
                messages.error(request, 'Error en los detalles de los materiales.')
    else:
        form = MovimientoForm(initial=initial_data, tipo_accion=tipo_accion)
        formset = DetalleMovimientoFormSet(form_kwargs={'tipo_accion': tipo_accion})

    # =========================================================================
    # 🛡️ FILTRO DINÁMICO DEL DESPLEGABLE
    # =========================================================================
    choices_originales = form.fields['tipo'].choices
    choices_filtradas = []

    for key, label in choices_originales:
        if not key:
            choices_filtradas.append((key, label))
            continue
        clave = str(key).upper()
        if tipo_accion == 'ingreso':
            if 'INGRESO' in clave or 'DEVOLUCION' in clave or 'ENTRADA' in clave:
                choices_filtradas.append((key, label))
        elif tipo_accion == 'salida':
            if 'SALIDA' in clave or 'CONSUMO' in clave:
                choices_filtradas.append((key, label))

    form.fields['tipo'].choices = choices_filtradas
    # =========================================================================

    context = {
        'form': form,
        'formset': formset,
        'almacen': almacen,
        'titulo': f"{'Salida' if tipo_accion == 'salida' else 'Ingreso'} de Materiales{' - ' + almacen.nombre if almacen else ''}",
        'boton_texto': f"Confirmar {'Salida' if tipo_accion == 'salida' else 'Ingreso'}"
    }
    return render(request, 'logistica/operacion_form.html', context)

def editar_movimiento(request, movimiento_id):
    """
    Permite editar un movimiento existente (Solo Borradores).
    """
    movimiento = get_object_or_404(Movimiento, id=movimiento_id)
    
    if movimiento.estado != 'BORRADOR':
        messages.error(request, "No se puede editar un movimiento confirmado.")
        return redirect('movimiento_list')

    # Determinamos el tipo de acción basado en el movimiento existente
    es_ingreso = 'INGRESO' in movimiento.tipo or 'DEVOLUCION' in movimiento.tipo or 'ENTRADA' in movimiento.tipo
    tipo_accion = 'ingreso' if es_ingreso else 'salida'

    if request.method == 'POST':
        form = MovimientoForm(request.POST, instance=movimiento, tipo_accion=tipo_accion)
        formset = DetalleMovimientoFormSet(request.POST, instance=movimiento, form_kwargs={'tipo_accion': tipo_accion})
        
        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    form.save()
                    formset.save()
                    messages.success(request, 'Movimiento actualizado correctamente.')
                    return redirect('movimiento_list')
            except Exception as e:
                messages.error(request, f"Error al actualizar: {e}")
    else:
        form = MovimientoForm(instance=movimiento, tipo_accion=tipo_accion)
        formset = DetalleMovimientoFormSet(instance=movimiento, form_kwargs={'tipo_accion': tipo_accion})

    almacen_contexto = movimiento.almacen_origen or movimiento.almacen_destino

    context = {
        'form': form,
        'formset': formset,
        'titulo': f"Editar {movimiento.get_tipo_display()}",
        'boton_texto': "Guardar Cambios",
        'almacen': almacen_contexto
    }
    return render(request, 'logistica/operacion_form.html', context)

# ==========================================
# 4. ACCIONES DE MOVIMIENTO (CONFIRMAR / ELIMINAR)
# ==========================================

def confirmar_movimiento_web(request, movimiento_id):
    movimiento = get_object_or_404(Movimiento, id=movimiento_id)
    
    if movimiento.estado == 'BORRADOR':
        try:
            # --- RED DE SEGURIDAD (Generador Tardío de Código) ---
            if not movimiento.nota_ingreso or movimiento.nota_ingreso == 'Por Generar':
                es_salida = 'SALIDA' in movimiento.tipo or 'CONSUMO' in movimiento.tipo
                es_ingreso = 'INGRESO' in movimiento.tipo or 'DEVOLUCION' in movimiento.tipo or 'ENTRADA' in movimiento.tipo
                prefix = 'VS-' if es_salida else ('NI-' if es_ingreso else None)
                
                if prefix:
                    ultimo = Movimiento.objects.filter(nota_ingreso__startswith=prefix).order_by('-nota_ingreso').first()
                    contador = 1
                    if ultimo:
                        try:
                            contador = int(ultimo.nota_ingreso.split('-')[1]) + 1
                        except:
                            contador = 1
                    movimiento.nota_ingreso = f"{prefix}{contador:04d}"
                movimiento.save()
            
            # --- USAMOS EL SERVICIO CENTRALIZADO ---
            # Esto actualiza Stock y Existencia correctamente
            KardexService.confirmar_movimiento(movimiento.id)
            messages.success(request, f'Movimiento {movimiento.nota_ingreso} confirmado correctamente.')

        except ValidationError as e:
            messages.error(request, f'Validación: {e.message}')
        except Exception as e:
            messages.error(request, f'Error al procesar: {str(e)}')
            
    else:
        messages.warning(request, 'Este movimiento ya estaba confirmado.')
    
    return redirect('movimiento_list')

def anular_movimiento(request, movimiento_id):
    """
    Anula un movimiento. Si es Borrador lo cancela, si es Confirmado revierte stock.
    """
    movimiento = get_object_or_404(Movimiento, id=movimiento_id)
    
    try:
        KardexService.anular_movimiento(movimiento.id)
        messages.success(request, f'Movimiento {movimiento.nota_ingreso} ANULADO correctamente. Stock revertido.')
    except ValidationError as e:
        messages.error(request, f"No se pudo anular: {e.message}")
        
    return redirect('movimiento_list')

# ==========================================
# 5. APIs Y HERRAMIENTAS (SCRIPTS)
# ==========================================

def api_consultar_stock(request, almacen_id, material_id):
    """
    API JSON: Devuelve el stock actual de un material.
    """
    try:
        item = Stock.objects.filter(almacen_id=almacen_id, material_id=material_id).first()
        stock_actual = item.cantidad if item else 0
        return JsonResponse({'stock': stock_actual})
    except Exception as e:
        return JsonResponse({'stock': 0, 'error': str(e)})

# ==========================================
# 6. ZONA DE PELIGRO (ADMINISTRACIÓN)
# ==========================================

def reset_database(request):
    """
    Limpia toda la data transaccional (Movimientos, Stock, Requerimientos).
    Mantiene catálogos (Materiales, Proyectos, Usuarios).
    Requiere ser Superusuario y confirmar contraseña.
    """
    if not request.user.is_superuser:
        messages.error(request, "Acceso denegado. Solo administradores.")
        return redirect('dashboard')

    if request.method == 'POST':
        password = request.POST.get('password')
        if not request.user.check_password(password):
            messages.error(request, "Contraseña incorrecta. No se realizaron cambios.")
        else:
            try:
                with transaction.atomic():
                    # 1. Eliminar detalles y movimientos
                    DetalleMovimiento.objects.all().delete()
                    Movimiento.objects.all().delete()
                    # 2. Eliminar Stock y Costos
                    Stock.objects.all().delete()
                    Existencia.objects.all().delete()
                    # 3. Eliminar Requerimientos
                    DetalleRequerimiento.objects.all().delete()
                    Requerimiento.objects.all().delete()
                
                messages.success(request, "✅ Base de datos operativa reiniciada correctamente.")
                return redirect('dashboard')
            except Exception as e:
                messages.error(request, f"Error al limpiar datos: {e}")

    return render(request, 'logistica/reset_db.html')

def cerrar_requerimiento(request, req_id):
    """
    Cierra forzosamente un requerimiento (ej: ya no se necesita el saldo pendiente).
    """
    req = get_object_or_404(Requerimiento, id=req_id)
    
    if req.estado not in ['TOTAL', 'CANCELADO']:
        # Verificar si hay stock ingresado que no se entregó (Sobrante)
        sobrantes = []
        for det in req.detalles.all():
            remanente = det.cantidad_ingresada - det.cantidad_atendida
            if remanente > 0:
                sobrantes.append(f"{det.material.codigo} ({remanente})")

        req.estado = 'TOTAL' # Lo marcamos como completado
        req.observacion += "\n[SISTEMA] Cerrado manualmente por el usuario (Saldo anulado)."
        req.save()
        
        if sobrantes:
            lista = ", ".join(sobrantes)
            messages.warning(request, f"⚠️ ATENCIÓN: El requerimiento {req.codigo} se cerró con materiales ingresados NO entregados: {lista}. Estos pasan a ser STOCK LIBRE.")
        else:
            messages.success(request, f"Requerimiento {req.codigo} finalizado manualmente.")
        
    return redirect('requerimiento_detail', req_id=req.id)

# ==========================================
# 7. EXPORTACIÓN A EXCEL
# ==========================================

def exportar_inventario_excel(request):
    """
    Genera un Excel con el stock actual filtrado por la búsqueda.
    """
    query = request.GET.get('q')
    stocks_filter = Stock.objects.select_related('material', 'material__categoria', 'almacen')

    if query:
        stocks_filter = stocks_filter.filter(
            Q(material__codigo__icontains=query) |
            Q(material__descripcion__icontains=query)
        )
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Inventario Físico"

    # Encabezados
    headers = ["Almacén", "Código", "Material", "Categoría", "Unidad", "Stock Actual", "Mínimo", "Ubicación"]
    ws.append(headers)
    
    # Estilo Encabezado
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color="2C3E50", end_color="2C3E50", fill_type="solid")
        cell.alignment = Alignment(horizontal="center")

    # Datos
    for stock in stocks_filter:
        ws.append([
            stock.almacen.nombre,
            stock.material.codigo,
            stock.material.descripcion,
            stock.material.categoria.nombre if stock.material.categoria else '-',
            stock.material.unidad_medida,
            stock.cantidad,
            stock.cantidad_minima,
            stock.ubicacion_pasillo
        ])

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="Inventario_{timezone.now().strftime("%Y%m%d")}.xlsx"'
    wb.save(response)
    return response

def exportar_kardex_excel(request, almacen_id, material_id):
    """
    Genera el Kardex de un producto específico en Excel.
    """
    almacen = get_object_or_404(Almacen, id=almacen_id)
    material = get_object_or_404(Material, id=material_id)

    # Reutilizamos la lógica de cálculo de saldos
    stock_item = Stock.objects.filter(almacen=almacen, material=material).first()
    saldo_actual = stock_item.cantidad if stock_item else Decimal(0)

    movimientos = DetalleMovimiento.objects.filter(
        material=material,
        movimiento__estado='CONFIRMADO'
    ).filter(
        Q(movimiento__almacen_origen=almacen) | 
        Q(movimiento__almacen_destino=almacen)
    ).select_related('movimiento', 'movimiento__creado_por').order_by('-movimiento__fecha')

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Kardex {material.codigo}"

    # Información General
    ws.append(["Material:", f"{material.codigo} - {material.descripcion}"])
    ws.append(["Almacén:", almacen.nombre])
    ws.append([]) # Espacio

    # Encabezados Tabla
    headers = ["Fecha", "Tipo Operación", "Documento", "Entrada", "Salida", "Saldo", "Usuario"]
    ws.append(headers)
    
    # Estilo Encabezado
    for cell in ws[4]: # Fila 4 porque agregamos 3 filas antes
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color="2C3E50", end_color="2C3E50", fill_type="solid")

    # Procesar datos (Misma lógica que la vista web)
    rows = []
    for detalle in movimientos:
        mov = detalle.movimiento
        
        # Determinar si es entrada o salida para este almacén
        id_actual = str(almacen.id)
        id_destino = str(mov.almacen_destino_id) if mov.almacen_destino_id else ''
        id_origen = str(mov.almacen_origen_id) if mov.almacen_origen_id else ''

        soy_destino = (id_destino == id_actual)
        soy_origen = (id_origen == id_actual)

        es_ingreso = False
        es_salida = False

        if soy_destino:
            es_ingreso = True
        elif soy_origen:
            es_salida = True
        else:
            # Fallback
            if 'INGRESO' in mov.tipo or 'DEVOLUCION' in mov.tipo or 'ENTRADA' in mov.tipo: es_ingreso = True
            elif 'SALIDA' in mov.tipo or 'CONSUMO' in mov.tipo: es_salida = True

        entrada = detalle.cantidad if es_ingreso else 0
        salida = detalle.cantidad if es_salida else 0
        
        # Guardamos en lista temporal para invertir el orden si quisiéramos, 
        # pero aquí lo agregamos directo y calculamos saldo hacia atrás
        rows.append([
            mov.fecha.strftime("%d/%m/%Y %H:%M"),
            mov.get_tipo_display(),
            f"{mov.nota_ingreso or ''} {mov.documento_referencia or ''}",
            entrada,
            salida,
            saldo_actual,
            mov.creado_por.username
        ])

        # Recalcular saldo anterior
        if es_ingreso: saldo_actual -= detalle.cantidad
        elif es_salida: saldo_actual += detalle.cantidad

    # Escribir filas
    for row in rows:
        ws.append(row)

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="Kardex_{material.codigo}.xlsx"'
    wb.save(response)
    return response