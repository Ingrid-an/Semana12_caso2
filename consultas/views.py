"""
Vistas del sistema de Gestión de Consultas Médicas
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import Group, Permission
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.http import HttpResponseForbidden
from datetime import date, timedelta
from .models import Paciente, Medico, Cita, Consulta, LogAuditoria, Especialidad
from .forms import LoginForm, PacienteForm, CitaForm, ConsultaForm, CancelarCitaForm


def home(request):
    context = {}
    if request.user.is_authenticated:
        if hasattr(request.user, 'medico'):
            citas_hoy = Cita.objects.filter(
                medico=request.user.medico,
                fecha=date.today()
            ).exclude(estado='cancelada').order_by('hora')
            context['citas_hoy'] = citas_hoy
            context['rol'] = 'medico'
        elif hasattr(request.user, 'paciente'):
            mis_citas = Cita.objects.filter(
                paciente=request.user.paciente
            ).exclude(estado='cancelada').order_by('-fecha', '-hora')[:10]
            context['mis_citas'] = mis_citas
            context['rol'] = 'paciente'
        elif request.user.groups.filter(name='Recepcionistas').exists():
            context['rol'] = 'recepcionista'
            context['citas_hoy'] = Cita.objects.filter(fecha=date.today()).exclude(estado='cancelada').count()
            context['pacientes_total'] = Paciente.objects.filter(activo=True).count()
        elif request.user.is_superuser or request.user.groups.filter(name='Admins').exists():
            context['rol'] = 'admin'
            context['stats'] = {
                'pacientes': Paciente.objects.count(),
                'medicos': Medico.objects.count(),
                'citas_hoy': Cita.objects.filter(fecha=date.today()).count(),
                'consultas': Consulta.objects.count(),
            }
    return render(request, 'consultas/home.html', context)


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        login(request, user)
        messages.success(request, f'Bienvenido/a, {user.get_full_name() or user.username}')
        return redirect('home')
    return render(request, 'consultas/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, 'Sesión cerrada correctamente.')
    return redirect('login')


@login_required
def lista_pacientes(request):
    # Recepcionistas y admins
    if not (request.user.is_superuser or
            request.user.groups.filter(name__in=['Recepcionistas', 'Admins', 'Médicos']).exists()):
        raise PermissionDenied('No tiene permiso para ver la lista de pacientes.')
    q = request.GET.get('q', '')
    pacientes = Paciente.objects.filter(activo=True)
    if q:
        pacientes = pacientes.filter(
            Q(dni__icontains=q) | Q(nombres__icontains=q) | Q(apellidos__icontains=q)
        )
    return render(request, 'consultas/lista_pacientes.html', {
        'pacientes': pacientes[:50],
        'q': q
    })


@login_required
def crear_paciente(request):
    if not (request.user.is_superuser or
            request.user.groups.filter(name__in=['Recepcionistas', 'Admins']).exists()):
        raise PermissionDenied
    form = PacienteForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Paciente registrado correctamente.')
        return redirect('lista_pacientes')
    return render(request, 'consultas/form_paciente.html', {'form': form, 'titulo': 'Registrar Paciente'})


@login_required
def agendar_cita(request):
    # Permiso: agendar_cita o recepcionista/paciente/admin
    puede = (
        request.user.has_perm('consultas.agendar_cita') or
        request.user.is_superuser or
        request.user.groups.filter(name__in=['Recepcionistas', 'Pacientes', 'Admins']).exists() or
        hasattr(request.user, 'paciente')
    )
    if not puede:
        raise PermissionDenied('No tiene permiso para agendar citas.')

    form = CitaForm(request.POST or None, user=request.user)
    if request.method == 'POST' and form.is_valid():
        cita = form.save(commit=False)
        cita.creado_por = request.user
        cita.save()
        messages.success(request, f'Cita agendada para el {cita.fecha} a las {cita.hora.strftime("%H:%M")}.')
        return redirect('home')
    return render(request, 'consultas/form_cita.html', {
        'form': form,
        'titulo': 'Agendar Cita Médica'
    })


@login_required
def mis_citas(request):
    if hasattr(request.user, 'paciente'):
        citas = Cita.objects.filter(paciente=request.user.paciente).order_by('-fecha', '-hora')
    elif hasattr(request.user, 'medico'):
        citas = Cita.objects.filter(medico=request.user.medico).order_by('-fecha', '-hora')
    else:
        citas = Cita.objects.all().order_by('-fecha', '-hora')[:50]
    return render(request, 'consultas/mis_citas.html', {'citas': citas})


@login_required
def cancelar_cita(request, pk):
    cita = get_object_or_404(Cita, pk=pk)
    # Permisos: cancelar_cita, o propio paciente, o médico de la cita, o recepción/admin
    puede = (
        request.user.has_perm('consultas.cancelar_cita') or
        request.user.is_superuser or
        (hasattr(request.user, 'paciente') and cita.paciente == request.user.paciente) or
        (hasattr(request.user, 'medico') and cita.medico == request.user.medico) or
        request.user.groups.filter(name__in=['Recepcionistas', 'Admins']).exists()
    )
    if not puede:
        raise PermissionDenied('No tiene permiso para cancelar esta cita.')

    if cita.estado in ['completada', 'cancelada']:
        messages.warning(request, 'Esta cita ya no se puede cancelar.')
        return redirect('mis_citas')

    form = CancelarCitaForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        cita.estado = 'cancelada'
        cita.notas_cancelacion = form.cleaned_data['notas_cancelacion']
        cita.save()
        messages.success(request, 'Cita cancelada correctamente.')
        return redirect('mis_citas')
    return render(request, 'consultas/cancelar_cita.html', {'form': form, 'cita': cita})


@login_required
def historial_paciente(request, pk):
    paciente = get_object_or_404(Paciente, pk=pk)
    # Permiso ver_historial_clinico: médicos o el propio paciente
    puede = (
        request.user.has_perm('consultas.ver_historial_clinico') or
        request.user.is_superuser or
        (hasattr(request.user, 'paciente') and request.user.paciente == paciente) or
        hasattr(request.user, 'medico') or
        request.user.groups.filter(name__in=['Médicos', 'Admins']).exists()
    )
    if not puede:
        # Registrar intento no autorizado
        LogAuditoria.objects.create(
            usuario=request.user,
            paciente=paciente,
            accion='INTENTO_ACCESO_DENEGADO',
            ip_address=request.META.get('REMOTE_ADDR'),
            detalle=f'Usuario sin permiso intentó ver historial de {paciente.dni}'
        )
        raise PermissionDenied('No tiene permiso para ver este historial clínico.')

    citas = Cita.objects.filter(paciente=paciente).select_related('medico', 'medico__especialidad').order_by('-fecha')
    consultas = Consulta.objects.filter(cita__paciente=paciente).select_related('cita__medico')

    # El middleware también registra, pero reforzamos aquí
    LogAuditoria.objects.create(
        usuario=request.user,
        paciente=paciente,
        accion='ACCESO_HISTORIAL',
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:255],
        detalle=f'Acceso al historial completo de {paciente}'
    )

    return render(request, 'consultas/historial.html', {
        'paciente': paciente,
        'citas': citas,
        'consultas': consultas,
    })


@login_required
def registrar_consulta(request, cita_id):
    cita = get_object_or_404(Cita, pk=cita_id)
    if not hasattr(request.user, 'medico') or cita.medico != request.user.medico:
        if not request.user.is_superuser:
            raise PermissionDenied('Solo el médico asignado puede registrar la consulta.')

    if hasattr(cita, 'consulta'):
        messages.info(request, 'Esta cita ya tiene consulta registrada. Puede agregar notas.')
        return redirect('historial_paciente', pk=cita.paciente.pk)

    form = ConsultaForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        consulta = form.save(commit=False)
        consulta.cita = cita
        consulta.registrado_por = request.user
        consulta.save()
        messages.success(request, 'Consulta médica registrada correctamente.')
        return redirect('mis_citas')
    return render(request, 'consultas/form_consulta.html', {
        'form': form,
        'cita': cita,
        'titulo': 'Registrar Consulta Médica'
    })


@login_required
def agenda_medico(request):
    if not hasattr(request.user, 'medico') and not request.user.is_superuser:
        raise PermissionDenied
    medico = request.user.medico if hasattr(request.user, 'medico') else None
    fecha = request.GET.get('fecha', str(date.today()))
    try:
        fecha_obj = date.fromisoformat(fecha)
    except ValueError:
        fecha_obj = date.today()

    if medico:
        citas = Cita.objects.filter(medico=medico, fecha=fecha_obj).order_by('hora')
    else:
        citas = Cita.objects.filter(fecha=fecha_obj).order_by('hora')
    return render(request, 'consultas/agenda.html', {
        'citas': citas,
        'fecha': fecha_obj,
        'medico': medico,
    })


@login_required
def reportes(request):
    if not (request.user.has_perm('consultas.generar_reportes') or
            request.user.is_superuser or
            request.user.groups.filter(name='Admins').exists()):
        raise PermissionDenied('Solo administradores pueden generar reportes.')

    citas_por_especialidad = (
        Cita.objects.values('medico__especialidad__nombre')
        .annotate(total=Count('id'))
        .order_by('-total')
    )
    medicos_mas_consultas = (
        Consulta.objects.values('cita__medico__user__first_name', 'cita__medico__user__last_name')
        .annotate(total=Count('id'))
        .order_by('-total')[:10]
    )
    pacientes_frecuentes = (
        Cita.objects.values('paciente__nombres', 'paciente__apellidos', 'paciente__dni')
        .annotate(total=Count('id'))
        .order_by('-total')[:10]
    )
    return render(request, 'consultas/reportes.html', {
        'citas_por_especialidad': citas_por_especialidad,
        'medicos_mas_consultas': medicos_mas_consultas,
        'pacientes_frecuentes': pacientes_frecuentes,
    })
