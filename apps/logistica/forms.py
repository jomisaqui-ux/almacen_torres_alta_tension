from django import forms
from django.forms import inlineformset_factory
from django.db.models import F
from .models import Movimiento, DetalleMovimiento, Requerimiento, DetalleRequerimiento
from apps.activos.models import Activo
from apps.rrhh.models import Trabajador
from apps.catalogo.models import Proveedor

# ==========================================
# 1. FORMULARIO DE LA CABECERA (Movimiento)
# ==========================================
class MovimientoForm(forms.ModelForm):
    class Meta:
        model = Movimiento
        # Aquí van los campos GENERALES (Quién, Dónde, Cuándo)
        fields = [
            'tipo', 
            'almacen_origen', 
            'proveedor',            # <--- Campo Nuevo
            'requerimiento',
            'almacen_destino', 
            'torre_destino', 
            'trabajador',
            'nota_ingreso',         # <--- Campo Nuevo
            'documento_referencia', # <--- Campo Nuevo
            'observacion'
        ]
        
        labels = {
            'nota_ingreso': 'N° Nota de Ingreso (Interno)',
            'documento_referencia': 'N° Guía / Factura (Proveedor)',
        }

        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date'}),
            'observacion': forms.Textarea(attrs={'rows': 2}),
            # El campo nota_ingreso es solo lectura porque se autogenera
            'nota_ingreso': forms.TextInput(attrs={'readonly': 'readonly', 'placeholder': 'Autogenerado al guardar'}),
        }

    def __init__(self, *args, tipo_accion=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Lógica de filtrado inteligente según si es INGRESO o SALIDA
        qs = Requerimiento.objects.exclude(estado='CANCELADO')

        if tipo_accion == 'ingreso':
            # Para INGRESOS: Mostrar solo si falta que llegue material al almacén
            # (Algún detalle tiene cantidad_ingresada < cantidad_solicitada)
            qs = qs.exclude(estado='TOTAL').filter(detalles__cantidad_ingresada__lt=F('detalles__cantidad_solicitada')).distinct()
        else:
            # Para SALIDAS (Default): Mostrar solo si falta entregar a obra
            # (Estado Pendiente o Parcial)
            qs = qs.filter(estado__in=['PENDIENTE', 'PARCIAL'])

        self.fields['requerimiento'].queryset = qs.order_by('-fecha_solicitud')
        self.fields['requerimiento'].required = False # Permitimos movimientos libres (sin requerimiento)
        self.fields['requerimiento'].empty_label = "--- Sin Requerimiento (Stock Libre) ---"

        # Aplicar estilos Bootstrap a todos los campos
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class': 'form-check-input'})
            else:
                field.widget.attrs.update({'class': 'form-select' if isinstance(field.widget, forms.Select) else 'form-control'})
        
        # OPTIMIZACIÓN: No cargar todos los trabajadores en el select inicial
        # Si hay datos POST (validación), permitimos el ID enviado.
        # Si es edición (instance), permitimos el ID actual.
        # Si es nuevo, queryset vacío.
        if self.data and 'trabajador' in self.data:
            trabajador_id = self.data.get('trabajador')
            if trabajador_id:
                self.fields['trabajador'].queryset = Trabajador.objects.filter(id=trabajador_id)
        elif self.instance.pk and self.instance.trabajador:
            self.fields['trabajador'].queryset = Trabajador.objects.filter(id=self.instance.trabajador.id)
        else:
            self.fields['trabajador'].queryset = Trabajador.objects.none()

        # BLOQUEO Y OCULTAMIENTO DE ALMACÉN POR CONTEXTO
        if 'initial' in kwargs:
            initial = kwargs['initial']
            # Si ya viene definido el Origen (Contexto Salida), lo ocultamos
            if initial.get('almacen_origen'):
                self.fields['almacen_origen'].widget = forms.HiddenInput()
            # Si ya viene definido el Destino (Contexto Ingreso), lo ocultamos
            if initial.get('almacen_destino'):
                self.fields['almacen_destino'].widget = forms.HiddenInput()
        
        # Nota: El campo 'proveedor' se mostrará/ocultará vía JavaScript según el tipo

    def clean(self):
        """Validación cruzada para asegurar que existan los almacenes correctos según el tipo."""
        cleaned_data = super().clean()
        tipo = cleaned_data.get('tipo')
        origen = cleaned_data.get('almacen_origen')
        destino = cleaned_data.get('almacen_destino')

        # Definimos qué tipos requieren qué almacén
        tipos_ingreso = ['INGRESO_COMPRA', 'DEVOLUCION_OBRA', 'TRANSFERENCIA_ENTRADA']
        tipos_salida = ['SALIDA_OBRA', 'SALIDA_OFICINA', 'TRANSFERENCIA_SALIDA']
        # DEVOLUCION_LIMA y REINGRESO_LIMA tienen reglas especiales abajo
        # SALIDA_EPP se maneja como salida pero no requiere torre, requiere trabajador

        # Validación de Proveedor
        if tipo == 'INGRESO_COMPRA' and not cleaned_data.get('proveedor'):
            self.add_error('proveedor', 'Para un Ingreso por Compra, es OBLIGATORIO seleccionar el Proveedor.')

        if tipo in tipos_ingreso and not destino:
            self.add_error('almacen_destino', 'Para registrar este Ingreso/Devolución, es OBLIGATORIO seleccionar el Almacén Destino.')

        if tipo == 'TRANSFERENCIA_SALIDA' and not destino:
            self.add_error('almacen_destino', 'Para una Transferencia de Salida, debes seleccionar el Almacén Destino (Ej: Lima).')

        if (tipo in tipos_salida or tipo == 'SALIDA_EPP') and not origen:
            self.add_error('almacen_origen', 'Para registrar esta Salida, es OBLIGATORIO seleccionar el Almacén Origen.')
            
        # Validaciones específicas para LIMA
        if tipo == 'REINGRESO_LIMA' and not destino:
             self.add_error('almacen_destino', 'Para el Reingreso desde Lima, debes seleccionar el Almacén Destino donde entrará el material.')
        if tipo == 'DEVOLUCION_LIMA' and not origen:
             self.add_error('almacen_origen', 'Para devolver a Lima, debes seleccionar de qué Almacén sale.')
            
        if tipo in ['SALIDA_EPP', 'SALIDA_OBRA', 'SALIDA_OFICINA', 'DEVOLUCION_OBRA']:
            trabajador = cleaned_data.get('trabajador')
            if not trabajador:
                self.add_error('trabajador', 'Es OBLIGATORIO seleccionar al Trabajador (Solicitante/Beneficiario/Devolvente).')
            elif not trabajador.activo:
                self.add_error('trabajador', f'El trabajador {trabajador} figura como INACTIVO (Cesado). No se le puede entregar materiales.')

        return cleaned_data

# ==========================================
# 2. FORMULARIO DEL DETALLE (Materiales)
# ==========================================
# apps/logistica/forms.py

class DetalleMovimientoForm(forms.ModelForm):
    # Campo unificado para manejar la lógica de asignación
    seleccion_requerimiento = forms.ChoiceField(required=False)

    class Meta:
        model = DetalleMovimiento
        fields = ['material', 'cantidad', 'costo_unitario', 'marca', 'series_temporales', 'activo'] 
        widgets = {
            # Usamos HiddenInput para evitar renderizar el select pesado en cada fila
            'material': forms.HiddenInput(),
            
            'cantidad': forms.NumberInput(attrs={'step': '0.01', 'placeholder': 'Cant.'}),
            'costo_unitario': forms.NumberInput(attrs={'step': '0.01', 'placeholder': 'Precio S/.'}),
            'marca': forms.TextInput(attrs={'placeholder': 'Marca / Modelo', 'class': 'form-control-sm campo-activo-fijo'}),
            'series_temporales': forms.TextInput(attrs={'placeholder': 'Series (sep. por comas)', 'class': 'form-control-sm campo-activo-fijo'}),
            'activo': forms.Select(attrs={'class': 'form-select form-select-sm campo-activo-salida'}),
        }
    
    def __init__(self, *args, tipo_accion=None, almacen_id=None, tipo_movimiento=None, **kwargs):
        self.tipo_accion = tipo_accion # Guardamos el tipo para usarlo en clean()
        self.almacen_id = almacen_id   # Guardamos el almacén para filtrar
        self.tipo_movimiento = tipo_movimiento # Nuevo: Para saber si es REINGRESO_LIMA
        super().__init__(*args, **kwargs)
        # Hacemos que el costo sea opcional (para Salidas o cuando no se tiene el dato)
        self.fields['costo_unitario'].required = False
        
        # Filtramos los activos disponibles para el selector
        # Solo mostramos activos DISPONIBLES y que NO pertenezcan a un Kit (los kits se asignan en bloque)
        qs_activos = Activo.objects.filter(estado='DISPONIBLE', kit__isnull=True)
        
        # NUEVO: Si hay un almacén definido, filtramos solo los activos que están ahí
        if self.almacen_id:
            qs_activos = qs_activos.filter(ubicacion_id=self.almacen_id)
            
        # LÓGICA DE REINGRESO: Si vuelve de Lima, mostramos los que están "DEVUELTO_EXTERNO"
        if self.tipo_movimiento == 'REINGRESO_LIMA':
            # Sobreescribimos el queryset para mostrar SOLO los que están fuera
            qs_activos = Activo.objects.filter(estado='DEVUELTO_EXTERNO')
        
        # NUEVO: Si es devolución de obra, mostramos los que están ASIGNADOS (en campo)
        elif self.tipo_movimiento == 'DEVOLUCION_OBRA':
            qs_activos = Activo.objects.filter(estado='ASIGNADO')
            
        if self.instance.pk and self.instance.activo:
            # Si estamos editando, incluimos el activo actual aunque ya no esté disponible (porque lo tiene esta línea)
            qs_activos = qs_activos | Activo.objects.filter(id=self.instance.activo.id)
        self.fields['activo'].queryset = qs_activos

        # Filtramos para que no salgan requerimientos viejos/cerrados en el desplegable de la fila
        qs = Requerimiento.objects.exclude(estado__in=['TOTAL', 'CANCELADO'])
        
        if tipo_accion == 'ingreso':
            # Para INGRESOS: Mostrar solo si falta que llegue material al almacén
            # (Algún detalle tiene cantidad_ingresada < cantidad_solicitada)
            qs = qs.filter(detalles__cantidad_ingresada__lt=F('detalles__cantidad_solicitada')).distinct()
            
        qs = qs.order_by('-fecha_solicitud')
        
        # Construimos las opciones del desplegable unificado
        choices = [
            ('STOCK_LIBRE', '--- Sin Requerimiento (Stock Libre) ---'),
        ]
        
        # Agregamos los requerimientos reales
        for req in qs:
            choices.append((str(req.id), str(req)))
            
        # Definimos el campo dinámicamente para asegurar que quede al final del formulario (DOM)
        self.fields['seleccion_requerimiento'] = forms.ChoiceField(
            choices=choices, 
            required=False, 
            widget=forms.Select(attrs={'class': 'form-select form-select-sm'})
        )
        
        # Establecer valor inicial basado en la instancia (Edición)
        if self.instance.pk:
            if self.instance.es_stock_libre:
                self.fields['seleccion_requerimiento'].initial = 'STOCK_LIBRE'
            elif self.instance.requerimiento:
                self.fields['seleccion_requerimiento'].initial = str(self.instance.requerimiento.id)
            else:
                self.fields['seleccion_requerimiento'].initial = 'STOCK_LIBRE'
        else:
            self.fields['seleccion_requerimiento'].initial = 'STOCK_LIBRE' # Por defecto

        for field in self.fields.values():
            # Mantenemos las clases de Bootstrap y agregamos las nuestras si ya existen
            existing_class = field.widget.attrs.get('class', '')
            if 'form-select' not in existing_class and isinstance(field.widget, forms.Select):
                field.widget.attrs['class'] = existing_class + ' form-select'
            elif 'form-control' not in existing_class:
                field.widget.attrs['class'] = existing_class + ' form-control'

        # Aseguramos el orden lógico de los campos para la navegación (Tab Index)
        # AJUSTE: Movemos 'activo' antes de los campos de texto para evitar saltos erróneos cuando estos se ocultan en Salidas
        self.order_fields(['material', 'cantidad', 'costo_unitario', 'activo', 'marca', 'series_temporales', 'seleccion_requerimiento'])

    def clean(self):
        cleaned_data = super().clean()
        material = cleaned_data.get('material')
        cantidad = cleaned_data.get('cantidad')
        series = cleaned_data.get('series_temporales')
        
        # Validar solo en Ingresos y si es Activo Fijo
        if self.tipo_accion == 'ingreso' and material and material.tipo == 'ACTIVO_FIJO':
            # CASO ESPECIAL: Devolución de Obra (Es un ingreso, pero seleccionamos un activo existente)
            if self.tipo_movimiento == 'DEVOLUCION_OBRA':
                activo = cleaned_data.get('activo')
                if not activo:
                    self.add_error('activo', "Para una Devolución de Obra, debes seleccionar el equipo que retorna.")
            else:
                # CASO NORMAL: Compra o Ingreso Nuevo (Series manuales)
                if cantidad:
                    # Convertimos series a lista, eliminando espacios vacíos
                    lista_series = [s.strip() for s in (series or "").split(',') if s.strip()]
                    cantidad_entera = int(cantidad)
                    
                    if len(lista_series) != cantidad_entera:
                        self.add_error('series_temporales', f"Debes ingresar {cantidad_entera} series separadas por comas. (Ingresaste {len(lista_series)})")
        
        # Validar solo en Salidas y si es Activo Fijo
        if self.tipo_accion == 'salida' and material and material.tipo == 'ACTIVO_FIJO':
            activo = cleaned_data.get('activo')
            if not activo:
                self.add_error('activo', "Para la salida de un Activo Fijo, debes seleccionar el equipo específico (Serie/Código).")
            # Nota: La cantidad se valida en el frontend para que sea 1
            
            # NUEVO: Validación de Ubicación (Anti-Teletransportación)
            # Verificamos que el activo seleccionado realmente esté en el almacén de origen
            origen_id = self.almacen_id or self.data.get('almacen_origen')
            if activo and origen_id:
                if str(activo.ubicacion_id) != str(origen_id):
                    self.add_error('activo', f"El activo {activo.codigo} se encuentra en '{activo.ubicacion}', no en el almacén seleccionado.")
        
        return cleaned_data

    def save(self, commit=True):
        """Sobreescribimos save para traducir el campo 'seleccion_requerimiento' a los campos del modelo."""
        instance = super().save(commit=False)
        val = self.cleaned_data.get('seleccion_requerimiento')
        
        if val == 'STOCK_LIBRE':
            instance.requerimiento = None
            instance.es_stock_libre = True
        elif val:
            # Es un UUID de Requerimiento
            instance.requerimiento = Requerimiento.objects.get(id=val)
            instance.es_stock_libre = False
        else:
            # Fallback
            instance.requerimiento = None
            instance.es_stock_libre = True
            
        if commit:
            instance.save()
        return instance

# ==========================================
# 3. LA FÁBRICA (FormSet)
# ==========================================
DetalleMovimientoFormSet = inlineformset_factory(
    Movimiento,           # Modelo Padre
    DetalleMovimiento,    # Modelo Hijo
    form=DetalleMovimientoForm, # <--- IMPORTANTE: Usar el formulario del HIJO
    extra=0,
    can_delete=True
)

# ==========================================
# 4. FORMULARIOS DE REQUERIMIENTOS (NUEVO)
# ==========================================

class RequerimientoForm(forms.ModelForm):
    class Meta:
        model = Requerimiento
        fields = ['solicitante', 'fecha_solicitud', 'fecha_necesaria', 'prioridad', 'observacion']
        widgets = {
            'fecha_solicitud': forms.DateInput(attrs={'type': 'date'}),
            'fecha_necesaria': forms.DateInput(attrs={'type': 'date'}),
            'observacion': forms.Textarea(attrs={'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})

class DetalleRequerimientoForm(forms.ModelForm):
    class Meta:
        model = DetalleRequerimiento
        fields = ['material', 'cantidad_solicitada']
        widgets = {
            'material': forms.HiddenInput(),
            'cantidad_solicitada': forms.NumberInput(attrs={'step': '0.01', 'placeholder': 'Cant.'}),
        }

DetalleRequerimientoFormSet = inlineformset_factory(
    Requerimiento,
    DetalleRequerimiento,
    form=DetalleRequerimientoForm,
    extra=0,
    can_delete=True
)

# ==========================================
# 5. UTILITARIOS (CARGA MASIVA)
# ==========================================
class ImportarDatosForm(forms.Form):
    archivo_excel = forms.FileField(
        label="Seleccionar archivo Excel (.xlsx)",
        help_text="Asegúrese de usar la plantilla oficial descargada del sistema.",
        widget=forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': '.xlsx'})
    )

    def clean_archivo_excel(self):
        archivo = self.cleaned_data.get('archivo_excel')
        if archivo:
            if not archivo.name.endswith('.xlsx'):
                raise forms.ValidationError("Formato inválido. Solo se permiten archivos Excel (.xlsx).")
        return archivo