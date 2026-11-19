"""
Django Admin personalizado - Caso 2 RF5
- Vista de agenda diaria por médico
- Lista de pacientes con búsquedas por DNI o nombre
- Estadísticas, acción masiva, campos calculados
"""
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count
from django.utils import timezone
from datetime import date, timedelta
from .models import (
    Especialidad, Paciente, Medico, Cita, Consulta, LogAuditoria
)


@admin.register(Especialidad)
class EspecialidadAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'descripcion']
    search_fields = ['nombre']


class ConsultaInline(admin.StackedInline):
    model = Consulta
    extra = 0
    readonly_fields = ['fecha_registro', 'registrado_por']
    can_delete = False


@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    list_display = [
        'dni', 'apellidos', 'nombres', 'tipo', 'edad_display',
        'email', 'activo', 'fecha_registro'
    ]
    list_filter = ['tipo', 'activo', 'fecha_registro']
    search_fields = ['dni', 'nombres', 'apellidos', 'codigo_uncp', 'email']
    readonly_fields = ['fecha_registro', 'edad_display']
    list_per_page = 25
    ordering = ['apellidos', 'nombres']

    fieldsets = (
        ('Datos Personales', {
            'fields': ('dni', 'nombres', 'apellidos', 'fecha_nacimiento', 'edad_display', 'tipo')
        }),
        ('Datos UNCP', {
            'fields': ('codigo_uncp', 'email', 'telefono')
        }),
        ('Información Clínica', {
            'fields': ('alergias',)
        }),
        ('Sistema', {
            'fields': ('user', 'activo', 'fecha_registro'),
            'classes': ('collapse',)
        }),
    )

    @admin.display(description='Edad')
    def edad_display(self, obj):
        return f"{obj.edad} años"


@admin.register(Medico)
class MedicoAdmin(admin.ModelAdmin):
    list_display = [
        'cmp', 'nombre_completo', 'especialidad', 'consultorio',
        'hora_inicio', 'hora_fin', 'atiende_sabado', 'activo'
    ]
    list_filter = ['especialidad', 'activo', 'atiende_sabado']
    search_fields = ['cmp', 'user__first_name', 'user__last_name', 'user__username']
    list_per_page = 20

    @admin.display(description='Nombre')
    def nombre_completo(self, obj):
        return obj.nombre_completo


@admin.action(description='Marcar citas seleccionadas como completadas')
def marcar_completadas(modeladmin, request, queryset):
    actualizadas = queryset.filter(estado__in=['pendiente', 'confirmada']).update(estado='completada')
    modeladmin.message_user(request, f'{actualizadas} cita(s) marcadas como completadas.')


@admin.register(Cita)
class CitaAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'fecha', 'hora', 'paciente', 'medico', 'estado_coloreado',
        'motivo_corto', 'dias_desde_creacion'
    ]
    list_filter = [
        'estado', 'fecha', 'medico__especialidad', 'medico',
        ('fecha', admin.DateFieldListFilter),
    ]
    search_fields = [
        'paciente__dni', 'paciente__nombres', 'paciente__apellidos',
        'medico__user__first_name', 'medico__user__last_name', 'motivo'
    ]
    date_hierarchy = 'fecha'
    list_per_page = 30
    actions = [marcar_completadas]
    readonly_fields = ['fecha_creacion', 'fecha_modificacion', 'creado_por']
    autocomplete_fields = ['paciente', 'medico']

    fieldsets = (
        ('Datos de la Cita', {
            'fields': ('paciente', 'medico', 'fecha', 'hora', 'estado')
        }),
        ('Detalle', {
            'fields': ('motivo', 'notas_cancelacion')
        }),
        ('Auditoría', {
            'fields': ('creado_por', 'fecha_creacion', 'fecha_modificacion'),
            'classes': ('collapse',)
        }),
    )

    @admin.display(description='Estado')
    def estado_coloreado(self, obj):
        colores = {
            'pendiente': '#ffc107',
            'confirmada': '#17a2b8',
            'completada': '#28a745',
            'cancelada': '#dc3545',
            'no_asistio': '#6c757d',
        }
        color = colores.get(obj.estado, '#000')
        return format_html(
            '<span style="background-color:{}; color:white; padding:3px 8px; border-radius:4px;">{}</span>',
            color, obj.get_estado_display()
        )

    @admin.display(description='Motivo')
    def motivo_corto(self, obj):
        return obj.motivo[:50] + '...' if len(obj.motivo) > 50 else obj.motivo

    @admin.display(description='Días desde creación')
    def dias_desde_creacion(self, obj):
        delta = timezone.now() - obj.fecha_creacion
        return f"{delta.days} días"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('paciente', 'medico', 'medico__user', 'medico__especialidad')

    def save_model(self, request, obj, form, change):
        if not change:
            obj.creado_por = request.user
        super().save_model(request, obj, form, change)


@admin.register(Consulta)
class ConsultaAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'paciente_display', 'medico_display', 'fecha_registro',
        'diagnostico_corto', 'proxima_cita'
    ]
    list_filter = ['fecha_registro', 'cita__medico__especialidad']
    search_fields = [
        'cita__paciente__dni', 'cita__paciente__nombres',
        'diagnostico', 'tratamiento'
    ]
    readonly_fields = [
        'cita', 'diagnostico', 'tratamiento', 'medicamentos',
        'proxima_cita', 'archivos_adjuntos', 'fecha_registro', 'registrado_por'
    ]
    # Solo se permite editar notas_adicionales (integridad)
    fields = [
        'cita', 'diagnostico', 'tratamiento', 'medicamentos',
        'proxima_cita', 'archivos_adjuntos', 'notas_adicionales',
        'registrado_por', 'fecha_registro'
    ]

    @admin.display(description='Paciente')
    def paciente_display(self, obj):
        return obj.cita.paciente

    @admin.display(description='Médico')
    def medico_display(self, obj):
        return obj.cita.medico

    @admin.display(description='Diagnóstico')
    def diagnostico_corto(self, obj):
        return obj.diagnostico[:60] + '...' if len(obj.diagnostico) > 60 else obj.diagnostico


@admin.register(LogAuditoria)
class LogAuditoriaAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'usuario', 'paciente', 'accion', 'ip_address']
    list_filter = ['timestamp', 'accion']
    search_fields = ['usuario__username', 'paciente__dni', 'paciente__apellidos', 'accion']
    readonly_fields = [
        'usuario', 'paciente', 'accion', 'ip_address',
        'user_agent', 'timestamp', 'detalle'
    ]
    date_hierarchy = 'timestamp'
    list_per_page = 50

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
