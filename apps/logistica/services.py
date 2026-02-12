from django.db import transaction
from django.core.exceptions import ValidationError
from django.db.models import Sum, F
from decimal import Decimal
from .models import Movimiento, Stock, Existencia, DetalleRequerimiento

class KardexService:
    @staticmethod
    @transaction.atomic
    def confirmar_movimiento(movimiento_id):
        """
        Ejecuta la lógica contable y logística:
        1. Valida stock suficiente (si es salida).
        2. Actualiza Stock físico.
        3. Recalcula PMP (si es ingreso).
        4. Cambia estado a CONFIRMADO.
        """
        movimiento = Movimiento.objects.select_related('proyecto').get(id=movimiento_id)
        
        if movimiento.estado != 'BORRADOR':
            raise ValidationError("Solo se pueden confirmar movimientos en estado Borrador.")

        detalles = movimiento.detalles.all()
        if not detalles:
            raise ValidationError("El movimiento no tiene detalles (materiales).")

        # Iteramos por cada línea del vale
        for detalle in detalles:
            # 1. Obtener o Crear la 'Existencia' con BLOQUEO DE BASE DE DATOS (select_for_update)
            # Esto evita condiciones de carrera al calcular el PMP.
            existencia, _ = Existencia.objects.select_for_update().get_or_create(
                proyecto=movimiento.proyecto,
                material=detalle.material
            )

            # 2. Lógica según el tipo de movimiento
            # --- GRUPO INGRESOS (Suman Stock) ---
            if movimiento.tipo in ['INGRESO_COMPRA', 'DEVOLUCION_OBRA', 'TRANSFERENCIA_ENTRADA']:
                KardexService._procesar_ingreso(movimiento, detalle, existencia)
                
                # NUEVA LÓGICA: Conciliación de Ingreso (Manual o FIFO)
                KardexService._conciliar_ingreso_detalle(movimiento, detalle)
            
            # --- GRUPO SALIDAS (Restan Stock) ---
            elif movimiento.tipo in ['SALIDA_OBRA', 'SALIDA_OFICINA', 'TRANSFERENCIA_SALIDA', 'SALIDA_EPP']:
                # 1. Identificar Requerimiento (Línea > Cabecera)
                req_asociado = detalle.requerimiento or movimiento.requerimiento
                if req_asociado:
                    KardexService._atender_detalle_requerimiento(detalle, req_asociado)

                # 2. Procesar Salida Física
                KardexService._procesar_salida(movimiento, detalle, existencia)
            
            # --- AJUSTES (Depende de qué campo esté lleno) ---
            elif movimiento.tipo == 'AJUSTE_INVENTARIO':
                if movimiento.almacen_destino: # Si hay destino, es entrada
                    KardexService._procesar_ingreso(movimiento, detalle, existencia)
                elif movimiento.almacen_origen: # Si hay origen, es salida
                    KardexService._procesar_salida(movimiento, detalle, existencia)

        # 3. Finalizar
        movimiento.estado = 'CONFIRMADO'
        movimiento.save()

    @staticmethod
    def _procesar_ingreso(movimiento, detalle, existencia):
        """
        Al ingresar, AUMENTA stock y RECALCULA el precio promedio.
        Formula PMP = ( (StockActual * CostoActual) + (CantIngreso * CostoIngreso) ) / (StockTotalNuevo)
        """
        # A. Actualizar Stock Físico en Almacén Destino
        stock_fisico, _ = Stock.objects.select_for_update().get_or_create(
            almacen=movimiento.almacen_destino,
            material=detalle.material
        )
        stock_fisico.cantidad += detalle.cantidad
        stock_fisico.save()

        # B. Actualizar PMP y Stock Financiero del Proyecto (Si aplica)
        if movimiento.proyecto.usa_control_costos:
            costo_ingreso = detalle.costo_unitario
            if costo_ingreso <= 0:
                raise ValidationError(f"El material {detalle.material} requiere costo unitario mayor a 0.")

            valor_actual = existencia.stock_total_proyecto * existencia.costo_promedio
            valor_nuevo = detalle.cantidad * costo_ingreso
            nuevo_stock_total = existencia.stock_total_proyecto + detalle.cantidad

            if nuevo_stock_total > 0:
                nuevo_pmp = (valor_actual + valor_nuevo) / nuevo_stock_total
                existencia.costo_promedio = nuevo_pmp
                existencia.ultimo_costo_compra = costo_ingreso
        
        # Actualizamos la cantidad total del proyecto
        existencia.stock_total_proyecto += detalle.cantidad
        existencia.save()

    @staticmethod
    def _conciliar_ingreso_detalle(movimiento, detalle):
        """
        Asigna el ingreso a un requerimiento específico.
        Jerarquía:
        1. Selección Manual en Línea (detalle.requerimiento)
        2. Selección Manual en Cabecera (movimiento.requerimiento)
        3. Automático FIFO (Busca el más antiguo pendiente)
        """
        req_destino = detalle.requerimiento # 1. Prioridad Línea
        
        if not req_destino and movimiento.requerimiento:
            req_destino = movimiento.requerimiento # 2. Prioridad Cabecera
            
        # 3. Fallback FIFO (Si no hay selección manual Y no se forzó Stock Libre)
        if not req_destino and not detalle.es_stock_libre:
            # Buscamos el requerimiento más antiguo que necesite este material
            pendiente = DetalleRequerimiento.objects.filter(
                material=detalle.material,
                requerimiento__estado__in=['PENDIENTE', 'PARCIAL'],
                requerimiento__proyecto=movimiento.proyecto
            ).annotate(
                falta=F('cantidad_solicitada') - F('cantidad_ingresada')
            ).filter(falta__gt=0).order_by('requerimiento__fecha_solicitud').first()
            
            if pendiente:
                req_destino = pendiente.requerimiento

        # Si encontramos un destino (Manual o FIFO), actualizamos
        if req_destino:
            det_req = req_destino.detalles.filter(material=detalle.material).first()
            if det_req:
                # VALIDACIÓN ESTRICTA: No permitir ingresar más de lo solicitado
                pendiente_ingreso = det_req.cantidad_solicitada - det_req.cantidad_ingresada
                
                if detalle.cantidad > pendiente_ingreso:
                    raise ValidationError(f"Exceso de Abastecimiento en {req_destino.codigo}: Estás ingresando {detalle.cantidad} de {detalle.material}, pero solo faltan {pendiente_ingreso} (Solicitado: {det_req.cantidad_solicitada}).")

                det_req.cantidad_ingresada += detalle.cantidad
                det_req.save()

    @staticmethod
    def _procesar_salida(movimiento, detalle, existencia):
        """
        Al salir, DISMINUYE stock. El costo de salida es el PMP actual.
        """
        # A. Validar Stock Físico en Almacén Origen
        stock_fisico = Stock.objects.select_for_update().filter(
            almacen=movimiento.almacen_origen,
            material=detalle.material
        ).first()

        if not stock_fisico or stock_fisico.cantidad < detalle.cantidad:
            raise ValidationError(f"Stock insuficiente de {detalle.material} en {movimiento.almacen_origen}.")

        # --- VALIDACIÓN DE STOCK LIBRE (Protección de Reservas) ---
        # Si es una salida "Sin Requerimiento" (ni en cabecera ni en línea), no debe tocar el stock reservado.
        req_asociado = detalle.requerimiento or movimiento.requerimiento
        
        if not req_asociado and movimiento.proyecto:
            # 1. Calcular Stock Reservado (Comprometido)
            # Suma de (Ingresado - Atendido) de todos los requerimientos pendientes
            reservas = DetalleRequerimiento.objects.filter(
                requerimiento__proyecto=movimiento.proyecto,
                material=detalle.material,
                requerimiento__estado__in=['PENDIENTE', 'PARCIAL']
            ).annotate(
                reservado=F('cantidad_ingresada') - F('cantidad_atendida')
            ).filter(reservado__gt=0)

            stock_reservado = reservas.aggregate(total=Sum('reservado'))['total'] or Decimal(0)

            # 2. Calcular Stock Libre (Total Proyecto - Reservado)
            stock_libre = max(Decimal(0), existencia.stock_total_proyecto - stock_reservado)

            if detalle.cantidad > stock_libre:
                # Mensaje de error detallado
                lista_reqs = ", ".join([f"{r.requerimiento.codigo}" for r in reservas[:3]])
                if reservas.count() > 3: lista_reqs += ", ..."
                
                raise ValidationError(
                    f"Stock Reservado: Estás intentando sacar {detalle.cantidad} de {detalle.material} como Stock Libre, "
                    f"pero hay {stock_reservado} unidades reservadas para requerimientos ({lista_reqs}). "
                    f"Stock libre real: {stock_libre}."
                )

        # B. Disminuir Stock
        stock_fisico.cantidad -= detalle.cantidad
        stock_fisico.save()

        # C. Disminuir Stock del Proyecto (El PMP no cambia en salidas, solo se mantiene)
        existencia.stock_total_proyecto -= detalle.cantidad
        existencia.save()
        
        # D. GRABAR EL COSTO DE SALIDA (Snapshot)
        # Es vital guardar a qué costo salió esto para reportes históricos.
        detalle.costo_unitario = existencia.costo_promedio
        detalle.save()

    @staticmethod
    def _atender_detalle_requerimiento(detalle, req):
        """
        Procesa la atención de una línea específica contra un requerimiento.
        """
        det_req = req.detalles.filter(material=detalle.material).first()
        
        if not det_req:
            raise ValidationError(f"El material {detalle.material} no está incluido en el Requerimiento {req.codigo}.")
        
        pendiente = det_req.cantidad_pendiente
        if detalle.cantidad > pendiente:
            raise ValidationError(f"Exceso en {req.codigo}: Estás despachando {detalle.cantidad} de {detalle.material}, pero solo tiene pendiente {pendiente}.")
        
        # VALIDACIÓN DE FLUJO FÍSICO: No despachar más de lo que ha ingresado para este pedido
        saldo_ingresado = det_req.cantidad_ingresada - det_req.cantidad_atendida
        if detalle.cantidad > saldo_ingresado:
            raise ValidationError(f"Stock de Pedido Insuficiente en {req.codigo}: Estás sacando {detalle.cantidad} de {detalle.material}, pero solo han llegado {det_req.cantidad_ingresada} y quedan {saldo_ingresado} por entregar.")

        # Actualizamos lo atendido
        det_req.cantidad_atendida += detalle.cantidad
        det_req.save()
        
        # Actualizar estado del requerimiento
        KardexService._actualizar_estado_requerimiento(req)

    @staticmethod
    def _actualizar_estado_requerimiento(req):
        if any(d.cantidad_pendiente > 0 for d in req.detalles.all()):
            req.estado = 'PARCIAL'
        else:
            req.estado = 'TOTAL'
        req.save()

    @staticmethod
    @transaction.atomic
    def anular_movimiento(movimiento_id):
        """
        Anulación Lógica y Reversión de Stock.
        Si es Borrador -> Solo cambia estado.
        Si es Confirmado -> Revierte stock físico, saldos de proyecto y requerimientos.
        """
        movimiento = Movimiento.objects.select_related('proyecto').get(id=movimiento_id)
        
        if movimiento.estado == 'CANCELADO':
            raise ValidationError("El movimiento ya está anulado.")

        if movimiento.estado == 'BORRADOR':
            movimiento.estado = 'CANCELADO'
            movimiento.save()
            return

        # Si es CONFIRMADO, revertimos efectos
        detalles = movimiento.detalles.all()
        
        # 1. Revertir Stock, Existencia y Requerimientos (Línea por línea)
        for detalle in detalles:
            # Revertir Ingreso de Requerimiento (Lógica inversa de conciliación)
            if movimiento.tipo in ['INGRESO_COMPRA', 'DEVOLUCION_OBRA', 'TRANSFERENCIA_ENTRADA']:
                 KardexService._revertir_ingreso_detalle_requerimiento(movimiento, detalle)
                 KardexService._revertir_ingreso(movimiento, detalle, existencia)

            # Revertir Salida de Requerimiento
            elif movimiento.tipo in ['SALIDA_OBRA', 'SALIDA_OFICINA', 'TRANSFERENCIA_SALIDA', 'SALIDA_EPP']:
                 req_asociado = detalle.requerimiento or movimiento.requerimiento
                 if req_asociado:
                     KardexService._revertir_atencion_detalle_requerimiento(detalle, req_asociado)
                 
                 KardexService._revertir_salida(movimiento, detalle, existencia)

            # Obtener existencia para ajustes
            existencia = Existencia.objects.select_for_update().get(
                proyecto=movimiento.proyecto,
                material=detalle.material
            )

            # AJUSTES
            if movimiento.tipo == 'AJUSTE_INVENTARIO':
                if movimiento.almacen_destino: # Fue entrada -> Restar
                    KardexService._revertir_ingreso(movimiento, detalle, existencia)
                elif movimiento.almacen_origen: # Fue salida -> Sumar
                    KardexService._revertir_salida(movimiento, detalle, existencia)

        movimiento.estado = 'CANCELADO'
        movimiento.save()

    @staticmethod
    def _revertir_ingreso(movimiento, detalle, existencia):
        """
        Revierte un ingreso: Resta del stock físico y del proyecto.
        Valida que haya stock suficiente para devolver.
        """
        stock_fisico = Stock.objects.select_for_update().get(
            almacen=movimiento.almacen_destino,
            material=detalle.material
        )
        
        if stock_fisico.cantidad < detalle.cantidad:
            raise ValidationError(f"No se puede anular el ingreso de {detalle.material}: El stock actual ({stock_fisico.cantidad}) es menor a lo que se intenta revertir ({detalle.cantidad}).")

        stock_fisico.cantidad -= detalle.cantidad
        stock_fisico.save()

        # Revertir stock global (No tocamos PMP por complejidad histórica, solo cantidades)
        existencia.stock_total_proyecto -= detalle.cantidad
        existencia.save()

    @staticmethod
    def _revertir_salida(movimiento, detalle, existencia):
        """
        Revierte una salida: Devuelve (Suma) al stock físico y al proyecto.
        """
        stock_fisico, _ = Stock.objects.select_for_update().get_or_create(
            almacen=movimiento.almacen_origen,
            material=detalle.material
        )
        
        stock_fisico.cantidad += detalle.cantidad
        stock_fisico.save()

        existencia.stock_total_proyecto += detalle.cantidad
        existencia.save()

    @staticmethod
    def _revertir_atencion_detalle_requerimiento(detalle, req):
        det_req = req.detalles.filter(material=detalle.material).first()
        if det_req:
            det_req.cantidad_atendida -= detalle.cantidad
            if det_req.cantidad_atendida < 0: det_req.cantidad_atendida = Decimal(0)
            det_req.save()
        
        # Recalcular estado
        atendidos = any(d.cantidad_atendida > 0 for d in req.detalles.all())
        pendientes = any(d.cantidad_pendiente > 0 for d in req.detalles.all())
        
        if not atendidos:
            req.estado = 'PENDIENTE'
        elif pendientes:
            req.estado = 'PARCIAL'
        else:
            req.estado = 'TOTAL'
        req.save()

    @staticmethod
    def _revertir_ingreso_detalle_requerimiento(movimiento, detalle):
        """
        Revierte la asignación de ingreso a un requerimiento.
        Debe usar la misma lógica de jerarquía para encontrar a quién se le asignó.
        """
        req_destino = detalle.requerimiento or movimiento.requerimiento
        
        # Si fue FIFO, es difícil saber exactamente a cuál fue sin guardar un log histórico.
        # LIMITACIÓN ACTUAL: Si fue FIFO automático, la reversión simple podría no encontrarlo si no guardamos el ID.
        # SOLUCIÓN ROBUSTA: Por ahora, revertimos solo si hay asignación explícita (Manual o Cabecera).
        # Para FIFO perfecto en reversión, necesitaríamos guardar en 'detalle.requerimiento' el resultado del FIFO al confirmar.
        
        if req_destino:
            det_req = req_destino.detalles.filter(material=detalle.material).first()
            if det_req:
                det_req.cantidad_ingresada -= detalle.cantidad
                if det_req.cantidad_ingresada < 0: det_req.cantidad_ingresada = Decimal(0)
                det_req.save()