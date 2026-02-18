from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from .models import PerfilUsuario
from apps.logistica.models import Almacen

User = get_user_model()

class UsuarioForm(forms.ModelForm):
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        required=False,
        help_text="Dejar en blanco para mantener la contraseña actual (al editar)."
    )
    almacenes = forms.ModelMultipleChoiceField(
        queryset=Almacen.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Almacenes Permitidos",
        help_text="Seleccione los almacenes a los que este usuario tendrá acceso."
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'dni', 'cargo', 'is_active', 'is_superuser']
        labels = {
            'username': 'Usuario (Login)',
            'first_name': 'Nombres',
            'last_name': 'Apellidos',
            'is_active': 'Activo',
            'is_superuser': 'Es Administrador (Superusuario)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Si es creación, la contraseña es obligatoria
        if not self.instance.pk:
            self.fields['password'].required = True
            self.fields['password'].help_text = "Requerido para nuevos usuarios."
        
        # Cargar almacenes iniciales si es edición
        if self.instance.pk:
            try:
                self.fields['almacenes'].initial = self.instance.perfil.almacenes.all()
            except PerfilUsuario.DoesNotExist:
                self.fields['almacenes'].initial = []

        for name, field in self.fields.items():
            if not isinstance(field.widget, (forms.CheckboxInput, forms.CheckboxSelectMultiple)):
                field.widget.attrs.update({'class': 'form-control'})
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class': 'form-check-input'})

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if password:
            try:
                validate_password(password, self.instance)
            except forms.ValidationError as error:
                self.add_error('password', error)
        return password

    def save(self, commit=True):
        user = super().save(commit=False)
        
        # Guardar contraseña de forma segura (Hashing) si se proporcionó
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)
        
        if commit:
            user.save()
            # Gestionar Perfil y Almacenes
            perfil, created = PerfilUsuario.objects.get_or_create(usuario=user)
            perfil.almacenes.set(self.cleaned_data['almacenes'])
            
        return user