from django import forms
from .models import Trabajador

class TrabajadorForm(forms.ModelForm):
    class Meta:
        model = Trabajador
        fields = ['dni', 'nombres', 'apellidos', 'cargo', 'talla_zapato', 'talla_ropa', 'activo']
        widgets = {
            'dni': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'DNI'}),
            'nombres': forms.TextInput(attrs={'class': 'form-control'}),
            'apellidos': forms.TextInput(attrs={'class': 'form-control'}),
            'cargo': forms.TextInput(attrs={'class': 'form-control'}),
            'talla_zapato': forms.TextInput(attrs={'class': 'form-control'}),
            'talla_ropa': forms.TextInput(attrs={'class': 'form-control'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }