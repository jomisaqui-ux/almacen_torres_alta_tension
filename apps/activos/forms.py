from django import forms
from .models import Activo, Kit
from apps.rrhh.models import Trabajador

class ActivoForm(forms.ModelForm):
    class Meta:
        model = Activo
        fields = ['codigo', 'serie', 'nombre', 'marca', 'modelo', 'estado', 'kit', 'fecha_compra', 'valor_compra', 'foto']
        widgets = {
            'codigo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: TAL-01'}),
            'serie': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'S/N Fabricante'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'marca': forms.TextInput(attrs={'class': 'form-control'}),
            'modelo': forms.TextInput(attrs={'class': 'form-control'}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'kit': forms.Select(attrs={'class': 'form-select'}),
            'fecha_compra': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'valor_compra': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'foto': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

    def clean_codigo(self):
        codigo = self.cleaned_data['codigo']
        # Convertir a mayúsculas automáticamente
        return codigo.upper()

class AsignacionForm(forms.Form):
    trabajador = forms.ModelChoiceField(
        queryset=Trabajador.objects.filter(activo=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Asignar a"
    )
    observacion = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        required=False,
        label="Observaciones de Entrega"
    )

class DevolucionForm(forms.Form):
    observacion = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        required=False,
        label="Estado al Devolver / Observaciones"
    )

class KitForm(forms.ModelForm):
    class Meta:
        model = Kit
        fields = ['codigo', 'nombre', 'descripcion']
        widgets = {
            'codigo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: KIT-01'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class AsignarKitForm(forms.Form):
    trabajador = forms.ModelChoiceField(
        queryset=Trabajador.objects.filter(activo=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Asignar Kit a"
    )
    observacion = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        required=False,
        label="Observaciones"
    )