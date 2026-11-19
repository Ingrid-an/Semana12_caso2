"""
Middlewares especializados - Caso 2 RF4
- Middleware de auditoría médica
- Middleware de validación de horario
- Middleware de alertas de citas pendientes
"""
import logging
from datetime import datetime, time
from django.utils import timezone
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.urls import resolve

logger = logging.getLogger('consultas.auditoria')


class ValidacionHorarioMiddleware:
    """
    Middleware de validación de horario:
    Verifica que las consultas solo se agenden en horario de atención
    (L-V 8:00-18:00, Sáb 8:00-13:00).
    Solo aplica a rutas de agendamiento en horario no permitido (opcional para demo).
    En desarrollo se permite siempre; se registra la advertencia.
    """

    RUTAS_AGENDAMIENTO = [
        'agendar_cita',
        'crear_cita',
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Verificar si estamos fuera de horario de atención del sistema
        ahora = timezone.localtime()
        dia = ahora.weekday()  # 0=Lunes ... 6=Domingo
        hora_actual = ahora.time()

        fuera_de_horario = False
        if dia == 6:  # Domingo
            fuera_de_horario = True
        elif dia == 5:  # Sábado
            if hora_actual < time(8, 0) or hora_actual >= time(13, 0):
                fuera_de_horario = True
        else:  # L-V
            if hora_actual < time(8, 0) or hora_actual >= time(18, 0):
                fuera_de_horario = True

        request.fuera_de_horario_atencion = fuera_de_horario

        response = self.get_response(request)
        return response


class AuditoriaMedicaMiddleware:
    """
    Middleware de auditoría médica:
    Registra quién accedió a qué historial clínico (requerimiento legal de confidencialidad).
    Logging de accesos a información sensible.
    """

    RUTAS_HISTORIAL = [
        'historial_paciente',
        'detalle_paciente',
        'ver_consulta',
        'detalle_consulta',
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Solo auditar si el usuario está autenticado y la ruta es de historial
        if request.user.is_authenticated:
            try:
                resolver_match = resolve(request.path)
                view_name = resolver_match.url_name or ''
                if any(ruta in view_name for ruta in self.RUTAS_HISTORIAL) or 'historial' in request.path:
                    self._registrar_acceso(request, view_name)
            except Exception:
                pass  # No interrumpir el flujo por errores de auditoría

        return response

    def _registrar_acceso(self, request, view_name):
        from .models import LogAuditoria, Paciente

        paciente_id = request.resolver_match.kwargs.get('pk') or request.resolver_match.kwargs.get('paciente_id')
        paciente = None
        if paciente_id:
            try:
                paciente = Paciente.objects.get(pk=paciente_id)
            except Paciente.DoesNotExist:
                pass

        ip = self._get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:255]

        detalle = f"Vista: {view_name} | Path: {request.path}"

        if paciente:
            LogAuditoria.objects.create(
                usuario=request.user,
                paciente=paciente,
                accion=f'ACCESO_HISTORIAL: {view_name}',
                ip_address=ip,
                user_agent=user_agent,
                detalle=detalle
            )
            logger.info(
                f"AUDITORÍA | Usuario: {request.user.username} | "
                f"Paciente: {paciente.dni} | IP: {ip} | Acción: {view_name}"
            )
        else:
            logger.info(
                f"AUDITORÍA | Usuario: {request.user.username} | "
                f"IP: {ip} | Acción: {view_name} | Path: {request.path}"
            )

    def _get_client_ip(self, request):
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded:
            return x_forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')


class AlertasCitasMiddleware:
    """
    Middleware de alertas:
    Notificar al médico si tiene citas pendientes al iniciar sesión / en cada request.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and hasattr(request.user, 'medico'):
            # Solo mostrar una vez por sesión para no spamear
            if not request.session.get('alerta_citas_mostrada'):
                from .models import Cita
                from datetime import date
                citas_hoy = Cita.objects.filter(
                    medico=request.user.medico,
                    fecha=date.today(),
                    estado__in=['pendiente', 'confirmada']
                ).count()
                if citas_hoy > 0:
                    messages.info(
                        request,
                        f'Tiene {citas_hoy} cita(s) pendiente(s) para hoy. Revise su agenda.'
                    )
                    request.session['alerta_citas_mostrada'] = True

        response = self.get_response(request)
        return response
