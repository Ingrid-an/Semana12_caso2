"""
Modelos del sistema de Gestión de Consultas Médicas - Centro Médico UNCP
Caso 2 - Semana 12
"""
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator, MinLengthValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import date, time, timedelta


# ==================== VALIDADORES ====================
dni_validator = RegexValidator(
    regex=r'^\d{8}$',
    message='El DNI debe tener exactamente 8 dígitos numéricos.'
)

cmp_validator = RegexValidator(
    regex=r'^\d{4,6}$',
    message='El CMP debe tener entre 4 y 6 dígitos numéricos (ej: 12345).'
)


def validar_fecha_nacimiento(value):
    if value > date.today():
        raise ValidationError('La fecha de nacimiento no puede ser futura.')
    if value.year < 1920:
        raise ValidationError('Fecha de nacimiento no válida.')


# ==================== MODELOS PRINCIPALES ====================

class Especialidad(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Especialidad'
        verbose_name_plural = 'Especialidades'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Paciente(models.Model):
    TIPO_CHOICES = [
        ('estudiante', 'Estudiante'),
        ('docente', 'Docente'),
    ]

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='paciente',
        null=True, blank=True, help_text='Usuario asociado (opcional para pacientes registrados por recepción)'
    )
    dni = models.CharField(max_length=8, unique=True, validators=[dni_validator])
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    fecha_nacimiento = models.DateField(validators=[validar_fecha_nacimiento])
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    codigo_uncp = models.CharField(max_length=20, blank=True, help_text='Código de estudiante o docente UNCP')
    email = models.EmailField(help_text='Preferentemente correo institucional @uncp.edu.pe')
    telefono = models.CharField(max_length=15, blank=True)
    alergias = models.TextField(blank=True, default='Ninguna conocida')
    fecha_registro = models.DateTimeField(auto_now_add=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Paciente'
        verbose_name_plural = 'Pacientes'
        ordering = ['apellidos', 'nombres']
        permissions = [
            ('ver_historial_clinico', 'Puede ver historial clínico'),
        ]

    def __str__(self):
        return f"{self.apellidos}, {self.nombres} (DNI: {self.dni})"

    @property
    def edad(self):
        today = date.today()
        return today.year - self.fecha_nacimiento.year - (
            (today.month, today.day) < (self.fecha_nacimiento.month, self.fecha_nacimiento.day)
        )

    def clean(self):
        super().clean()
        if self.tipo == 'estudiante' and self.email and not self.email.endswith('@uncp.edu.pe'):
            # Advertencia suave; se puede forzar en el formulario
            pass


class Medico(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='medico'
    )
    cmp = models.CharField(max_length=10, unique=True, validators=[cmp_validator])
    especialidad = models.ForeignKey(Especialidad, on_delete=models.PROTECT, related_name='medicos')
    consultorio = models.CharField(max_length=50)
    # Horarios de atención (simplificado: rango general)
    hora_inicio = models.TimeField(default=time(8, 0))
    hora_fin = models.TimeField(default=time(18, 0))
    atiende_sabado = models.BooleanField(default=False)
    telefono = models.CharField(max_length=15, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Médico'
        verbose_name_plural = 'Médicos'
        ordering = ['user__last_name', 'user__first_name']

    def __str__(self):
        return f"Dr(a). {self.user.get_full_name()} - {self.especialidad} (CMP: {self.cmp})"

    @property
    def nombre_completo(self):
        return self.user.get_full_name() or self.user.username


class Cita(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('confirmada', 'Confirmada'),
        ('completada', 'Completada'),
        ('cancelada', 'Cancelada'),
        ('no_asistio', 'No asistió'),
    ]

    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name='citas')
    medico = models.ForeignKey(Medico, on_delete=models.CASCADE, related_name='citas')
    fecha = models.DateField()
    hora = models.TimeField()
    motivo = models.TextField(
        validators=[MinLengthValidator(20, message='El motivo debe tener al menos 20 caracteres.')]
    )
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    creado_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='citas_creadas'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    notas_cancelacion = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Cita'
        verbose_name_plural = 'Citas'
        ordering = ['-fecha', '-hora']
        unique_together = [['medico', 'fecha', 'hora']]  # Evita solapamiento exacto
        permissions = [
            ('agendar_cita', 'Puede agendar citas'),
            ('cancelar_cita', 'Puede cancelar citas'),
            ('generar_reportes', 'Puede generar reportes'),
        ]

    def __str__(self):
        return f"Cita {self.paciente} con {self.medico} - {self.fecha} {self.hora}"

    def clean(self):
        super().clean()
        errors = {}

        # Validación de horario de atención del médico
        if self.medico_id and self.hora:
            if self.hora < self.medico.hora_inicio or self.hora >= self.medico.hora_fin:
                errors['hora'] = (
                    f'El médico atiende de {self.medico.hora_inicio.strftime("%H:%M")} '
                    f'a {self.medico.hora_fin.strftime("%H:%M")}.'
                )

        # Sábado solo si el médico atiende
        if self.fecha and self.fecha.weekday() == 5:  # Sábado
            if self.medico_id and not self.medico.atiende_sabado:
                errors['fecha'] = 'Este médico no atiende los sábados.'
            if self.hora and self.hora >= time(13, 0):
                errors['hora'] = 'Los sábados solo se atiende hasta las 13:00.'

        # Domingo no
        if self.fecha and self.fecha.weekday() == 6:
            errors['fecha'] = 'No se atienden citas los domingos.'

        # Paciente no puede tener 2 citas el mismo día (excepto canceladas)
        if self.paciente_id and self.fecha:
            qs = Cita.objects.filter(
                paciente=self.paciente,
                fecha=self.fecha
            ).exclude(estado='cancelada')
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                errors['fecha'] = 'El paciente ya tiene una cita programada para este día.'

        # Médico no puede tener citas superpuestas (mismo slot)
        if self.medico_id and self.fecha and self.hora:
            qs = Cita.objects.filter(
                medico=self.medico,
                fecha=self.fecha,
                hora=self.hora
            ).exclude(estado='cancelada')
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                errors['hora'] = 'El médico ya tiene una cita en este horario.'

        if errors:
            raise ValidationError(errors)


class Consulta(models.Model):
    """Registro clínico post-atención. Inmutable una vez creada (solo notas adicionales)."""
    cita = models.OneToOneField(Cita, on_delete=models.PROTECT, related_name='consulta')
    diagnostico = models.TextField()
    tratamiento = models.TextField()
    medicamentos = models.TextField(blank=True, help_text='Medicamentos recetados')
    proxima_cita = models.DateField(null=True, blank=True)
    archivos_adjuntos = models.TextField(
        blank=True,
        help_text='Simulación de archivos: nombres de recetas, exámenes, etc.'
    )
    notas_adicionales = models.TextField(blank=True, help_text='Solo se pueden agregar notas, no modificar el resto')
    registrado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Consulta Médica'
        verbose_name_plural = 'Consultas Médicas'
        ordering = ['-fecha_registro']

    def __str__(self):
        return f"Consulta de {self.cita.paciente} - {self.fecha_registro.date()}"

    def save(self, *args, **kwargs):
        # Integridad: no permitir modificar campos principales si ya existe
        if self.pk:
            original = Consulta.objects.get(pk=self.pk)
            # Solo se permite agregar a notas_adicionales
            self.diagnostico = original.diagnostico
            self.tratamiento = original.tratamiento
            self.medicamentos = original.medicamentos
            self.proxima_cita = original.proxima_cita
            self.archivos_adjuntos = original.archivos_adjuntos
        super().save(*args, **kwargs)
        # Actualizar estado de la cita
        if self.cita.estado != 'completada':
            self.cita.estado = 'completada'
            self.cita.save(update_fields=['estado'])


class LogAuditoria(models.Model):
    """Registro de accesos a historiales clínicos (requerimiento legal)."""
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name='logs_acceso')
    accion = models.CharField(max_length=100)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    detalle = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Log de Auditoría'
        verbose_name_plural = 'Logs de Auditoría'
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.timestamp} - {self.usuario} accedió a {self.paciente}"
