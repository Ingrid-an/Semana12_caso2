"""
Formularios complejos con validaciones cruzadas - Caso 2
"""
from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from datetime import date, time, datetime, timedelta
from .models import Paciente, Medico, Cita, Consulta, Especialidad


class LoginForm(AuthenticationForm):
    """Login diferenciado por tipo de usuario (visual)."""
    username = forms.CharField(
        label='Usuario',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Usuario o DNI',
            'autofocus': True
        })
    )
    password = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Contraseña'
        })
    )


class PacienteForm(forms.ModelForm):
    class Meta:
        model = Paciente
        fields = [
            'dni', 'nombres', 'apellidos', 'fecha_nacimiento',
            'tipo', 'codigo_uncp', 'email', 'telefono', 'alergias'
        ]
        widgets = {
            'dni': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '8', 'pattern': r'\d{8}'}),
            'nombres': forms.TextInput(attrs={'class': 'form-control'}),
            'apellidos': forms.TextInput(attrs={'class': 'form-control'}),
            'fecha_nacimiento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'codigo_uncp': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'alergias': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def clean_dni(self):
        dni = self.cleaned_data.get('dni')
        if dni and not dni.isdigit():
            raise ValidationError('El DNI solo debe contener números.')
        if dni and len(dni) != 8:
            raise ValidationError('El DNI debe tener exactamente 8 dígitos.')
        return dni

    def clean_fecha_nacimiento(self):
        fecha = self.cleaned_data.get('fecha_nacimiento')
        if fecha and fecha > date.today():
            raise ValidationError('La fecha de nacimiento no puede ser futura.')
        return fecha

    def clean_email(self):
        email = self.cleaned_data.get('email')
        tipo = self.cleaned_data.get('tipo')
        if tipo == 'estudiante' and email and not email.lower().endswith('@uncp.edu.pe'):
            raise ValidationError(
                'Los estudiantes deben usar correo institucional @uncp.edu.pe'
            )
        return email


class CitaForm(forms.ModelForm):
    """
    Formulario de cita médica con validaciones complejas (RF2):
    - Selección de médico filtrado por especialidad
    - Validación de slot ocupado
    - Motivo mínimo 20 caracteres
    - Paciente no puede tener 2 citas el mismo día
    - Médico no puede tener citas superpuestas
    """
    especialidad = forms.ModelChoiceField(
        queryset=Especialidad.objects.all(),
        required=False,
        label='Filtrar por Especialidad',
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_especialidad'})
    )

    class Meta:
        model = Cita
        fields = ['paciente', 'medico', 'fecha', 'hora', 'motivo']
        widgets = {
            'paciente': forms.Select(attrs={'class': 'form-select'}),
            'medico': forms.Select(attrs={'class': 'form-select', 'id': 'id_medico'}),
            'fecha': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'hora': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'motivo': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describa el motivo de la consulta (mínimo 20 caracteres)...'
            }),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['medico'].queryset = Medico.objects.filter(activo=True).select_related('user', 'especialidad')
        self.fields['paciente'].queryset = Paciente.objects.filter(activo=True)

        # Si es paciente logueado, fijar el paciente
        if user and hasattr(user, 'paciente'):
            self.fields['paciente'].initial = user.paciente
            self.fields['paciente'].widget = forms.HiddenInput()
            self.fields['paciente'].queryset = Paciente.objects.filter(pk=user.paciente.pk)

    def clean_motivo(self):
        motivo = self.cleaned_data.get('motivo', '')
        if len(motivo.strip()) < 20:
            raise ValidationError('El motivo de consulta debe tener al menos 20 caracteres.')
        return motivo

    def clean_fecha(self):
        fecha = self.cleaned_data.get('fecha')
        if not fecha:
            return fecha
        if fecha < date.today():
            raise ValidationError('No se pueden agendar citas en fechas pasadas.')
        if fecha.weekday() == 6:
            raise ValidationError('No se atienden citas los domingos.')
        # Límite razonable: no más de 60 días adelante
        if fecha > date.today() + timedelta(days=60):
            raise ValidationError('Solo se pueden agendar citas hasta 60 días en el futuro.')
        return fecha

    def clean_hora(self):
        hora = self.cleaned_data.get('hora')
        fecha = self.cleaned_data.get('fecha')
        if hora and fecha:
            # Horario general L-V 8:00-18:00, Sáb 8:00-13:00
            if fecha.weekday() == 5:  # Sábado
                if hora < time(8, 0) or hora >= time(13, 0):
                    raise ValidationError('Los sábados el horario de atención es de 08:00 a 13:00.')
            else:
                if hora < time(8, 0) or hora >= time(18, 0):
                    raise ValidationError('El horario de atención es de 08:00 a 18:00 (Lunes a Viernes).')
        return hora

    def clean(self):
        cleaned_data = super().clean()
        paciente = cleaned_data.get('paciente')
        medico = cleaned_data.get('medico')
        fecha = cleaned_data.get('fecha')
        hora = cleaned_data.get('hora')

        if not all([paciente, medico, fecha, hora]):
            return cleaned_data

        # Validación cruzada: paciente no puede tener 2 citas el mismo día
        citas_mismo_dia = Cita.objects.filter(
            paciente=paciente,
            fecha=fecha
        ).exclude(estado='cancelada')
        if self.instance.pk:
            citas_mismo_dia = citas_mismo_dia.exclude(pk=self.instance.pk)
        if citas_mismo_dia.exists():
            raise ValidationError({
                'fecha': 'El paciente ya tiene una cita programada para este día. Solo se permite una cita por día.'
            })

        # Validación: médico no puede tener citas superpuestas
        citas_ocupadas = Cita.objects.filter(
            medico=medico,
            fecha=fecha,
            hora=hora
        ).exclude(estado='cancelada')
        if self.instance.pk:
            citas_ocupadas = citas_ocupadas.exclude(pk=self.instance.pk)
        if citas_ocupadas.exists():
            raise ValidationError({
                'hora': f'El Dr(a). {medico.nombre_completo} ya tiene una cita a las {hora.strftime("%H:%M")} en esta fecha.'
            })

        # Validar horario del médico específico
        if hora < medico.hora_inicio or hora >= medico.hora_fin:
            raise ValidationError({
                'hora': (
                    f'El Dr(a). {medico.nombre_completo} atiende de '
                    f'{medico.hora_inicio.strftime("%H:%M")} a {medico.hora_fin.strftime("%H:%M")}.'
                )
            })

        if fecha.weekday() == 5 and not medico.atiende_sabado:
            raise ValidationError({
                'fecha': f'El Dr(a). {medico.nombre_completo} no atiende los sábados.'
            })

        return cleaned_data


class ConsultaForm(forms.ModelForm):
    """Formulario de registro de consulta médica (post-atención)."""
    class Meta:
        model = Consulta
        fields = [
            'diagnostico', 'tratamiento', 'medicamentos',
            'proxima_cita', 'archivos_adjuntos'
        ]
        widgets = {
            'diagnostico': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'tratamiento': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'medicamentos': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'Lista de medicamentos recetados...'
            }),
            'proxima_cita': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'archivos_adjuntos': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 2,
                'placeholder': 'Simulación: nombres de archivos adjuntos (recetas, exámenes)...'
            }),
        }

    def clean_proxima_cita(self):
        proxima = self.cleaned_data.get('proxima_cita')
        if proxima and proxima <= date.today():
            raise ValidationError('La próxima cita de control debe ser una fecha futura.')
        return proxima


class CancelarCitaForm(forms.Form):
    notas_cancelacion = forms.CharField(
        label='Motivo de cancelación',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        required=True,
        min_length=10
    )
