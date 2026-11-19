"""
Script para cargar datos de prueba del Caso 2.
Mínimo: 8 médicos, 15 pacientes, 30 citas.
Además crea grupos, permisos y usuarios de prueba.
"""
import os
import django
from datetime import date, time, timedelta
import random

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'centro_medico.settings')
django.setup()

from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from consultas.models import Especialidad, Paciente, Medico, Cita, Consulta

print("=== Creando grupos y permisos ===")
grupos_nombres = ['Médicos', 'Recepcionistas', 'Pacientes', 'Admins']
for nombre in grupos_nombres:
    Group.objects.get_or_create(name=nombre)

# Asignar permisos personalizados
ct = ContentType.objects.get_for_model(Cita)
perms = {
    'agendar_cita': 'Puede agendar citas',
    'cancelar_cita': 'Puede cancelar citas',
    'generar_reportes': 'Puede generar reportes',
}
for codename, name in perms.items():
    Permission.objects.get_or_create(
        codename=codename,
        content_type=ct,
        defaults={'name': name}
    )

ct_p = ContentType.objects.get_for_model(Paciente)
Permission.objects.get_or_create(
    codename='ver_historial_clinico',
    content_type=ct_p,
    defaults={'name': 'Puede ver historial clínico'}
)

# Asignar permisos a grupos
g_medicos = Group.objects.get(name='Médicos')
g_recep = Group.objects.get(name='Recepcionistas')
g_pac = Group.objects.get(name='Pacientes')
g_admin = Group.objects.get(name='Admins')

for p in Permission.objects.filter(codename__in=['ver_historial_clinico', 'cancelar_cita']):
    g_medicos.permissions.add(p)
for p in Permission.objects.filter(codename__in=['agendar_cita', 'cancelar_cita']):
    g_recep.permissions.add(p)
    g_pac.permissions.add(p)
for p in Permission.objects.filter(codename__in=['agendar_cita', 'cancelar_cita', 'generar_reportes', 'ver_historial_clinico']):
    g_admin.permissions.add(p)

print("=== Creando especialidades ===")
especialidades_data = [
    ('Medicina General', 'Atención primaria'),
    ('Pediatría', 'Atención a menores'),
    ('Ginecología', 'Salud femenina'),
    ('Traumatología', 'Lesiones musculoesqueléticas'),
    ('Dermatología', 'Piel y anexos'),
    ('Oftalmología', 'Salud visual'),
    ('Psicología', 'Salud mental'),
    ('Nutrición', 'Alimentación y dietas'),
]
especialidades = []
for nombre, desc in especialidades_data:
    esp, _ = Especialidad.objects.get_or_create(nombre=nombre, defaults={'descripcion': desc})
    especialidades.append(esp)

print("=== Creando usuarios y médicos (8+) ===")
medicos_data = [
    ('medico1', 'Carlos', 'Ramírez', '12345', 0, 'Consultorio 101', True),
    ('medico2', 'María', 'González', '12346', 1, 'Consultorio 102', False),
    ('medico3', 'José', 'Fernández', '12347', 2, 'Consultorio 201', True),
    ('medico4', 'Ana', 'Torres', '12348', 3, 'Consultorio 202', False),
    ('medico5', 'Luis', 'Vargas', '12349', 4, 'Consultorio 301', True),
    ('medico6', 'Patricia', 'Soto', '12350', 5, 'Consultorio 302', False),
    ('medico7', 'Roberto', 'Mendoza', '12351', 6, 'Consultorio 401', True),
    ('medico8', 'Elena', 'Castro', '12352', 7, 'Consultorio 402', False),
    ('medico9', 'Diego', 'Paredes', '23456', 0, 'Consultorio 103', True),
]
medicos = []
for username, first, last, cmp, esp_idx, consultorio, sabado in medicos_data:
    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            'first_name': first,
            'last_name': last,
            'email': f'{username}@uncp.edu.pe',
            'is_staff': True,
        }
    )
    if created:
        user.set_password('medico123')
        user.save()
    user.groups.add(g_medicos)
    medico, _ = Medico.objects.get_or_create(
        user=user,
        defaults={
            'cmp': cmp,
            'especialidad': especialidades[esp_idx],
            'consultorio': consultorio,
            'hora_inicio': time(8, 0),
            'hora_fin': time(18, 0),
            'atiende_sabado': sabado,
        }
    )
    medicos.append(medico)

print("=== Creando pacientes (15+) ===")
pacientes_data = [
    ('70123456', 'Ingrid', 'Andrade', 'estudiante', '2020123456', 'ingrid.andrade@uncp.edu.pe'),
    ('70234567', 'Josue', 'Yaranga', 'estudiante', '2020123457', 'josue.yaranga@uncp.edu.pe'),
    ('70345678', 'Lucía', 'Quispe', 'estudiante', '2021123458', 'lucia.quispe@uncp.edu.pe'),
    ('70456789', 'Pedro', 'Huamán', 'docente', 'DOC001', 'pedro.huaman@uncp.edu.pe'),
    ('70567890', 'Rosa', 'Mamani', 'estudiante', '2022123459', 'rosa.mamani@uncp.edu.pe'),
    ('70678901', 'Miguel', 'Chávez', 'docente', 'DOC002', 'miguel.chavez@uncp.edu.pe'),
    ('70789012', 'Carmen', 'Flores', 'estudiante', '2020123460', 'carmen.flores@uncp.edu.pe'),
    ('70890123', 'Jorge', 'Ríos', 'estudiante', '2021123461', 'jorge.rios@uncp.edu.pe'),
    ('70901234', 'Sofía', 'Paz', 'docente', 'DOC003', 'sofia.paz@uncp.edu.pe'),
    ('71012345', 'Andrés', 'Vega', 'estudiante', '2022123462', 'andres.vega@uncp.edu.pe'),
    ('71123456', 'Valeria', 'Cruz', 'estudiante', '2020123463', 'valeria.cruz@uncp.edu.pe'),
    ('71234567', 'Fernando', 'López', 'docente', 'DOC004', 'fernando.lopez@uncp.edu.pe'),
    ('71345678', 'Diana', 'Ruiz', 'estudiante', '2021123464', 'diana.ruiz@uncp.edu.pe'),
    ('71456789', 'Héctor', 'Silva', 'estudiante', '2022123465', 'hector.silva@uncp.edu.pe'),
    ('71567890', 'Natalia', 'Ortiz', 'docente', 'DOC005', 'natalia.ortiz@uncp.edu.pe'),
    ('71678901', 'Oscar', 'Núñez', 'estudiante', '2020123466', 'oscar.nunez@uncp.edu.pe'),
]
pacientes = []
for i, (dni, nombres, apellidos, tipo, codigo, email) in enumerate(pacientes_data):
    # Crear usuario para algunos pacientes
    user = None
    if i < 3:
        uname = f'paciente{i+1}'
        user, created = User.objects.get_or_create(
            username=uname,
            defaults={
                'first_name': nombres,
                'last_name': apellidos,
                'email': email,
            }
        )
        if created:
            user.set_password('pac123')
            user.save()
        user.groups.add(g_pac)
    nacimiento = date(1995 + (i % 10), (i % 12) + 1, (i % 28) + 1)
    p, _ = Paciente.objects.get_or_create(
        dni=dni,
        defaults={
            'user': user,
            'nombres': nombres,
            'apellidos': apellidos,
            'fecha_nacimiento': nacimiento,
            'tipo': tipo,
            'codigo_uncp': codigo,
            'email': email,
            'alergias': random.choice(['Ninguna conocida', 'Penicilina', 'Polen', 'Mariscos', 'Aspirina']),
        }
    )
    pacientes.append(p)

print("=== Creando usuarios de recepción y admin ===")
# Recepcionista
rec_user, created = User.objects.get_or_create(
    username='recepcion',
    defaults={'first_name': 'Ana', 'last_name': 'Recepción', 'email': 'recepcion@uncp.edu.pe', 'is_staff': True}
)
if created:
    rec_user.set_password('recep123')
    rec_user.save()
rec_user.groups.add(g_recep)

# Admin
admin_user, created = User.objects.get_or_create(
    username='admin',
    defaults={'first_name': 'Director', 'last_name': 'Centro Médico', 'email': 'admin@uncp.edu.pe', 'is_staff': True, 'is_superuser': True}
)
if created:
    admin_user.set_password('admin123')
    admin_user.save()
admin_user.groups.add(g_admin)

print("=== Creando citas (30+) ===")
motivos = [
    'Dolor de cabeza persistente desde hace varios días con náuseas ocasionales',
    'Control de presión arterial y revisión de medicación actual del paciente',
    'Dolor de garganta y fiebre leve durante los últimos tres días consecutivos',
    'Consulta por alergias estacionales y necesidad de receta de antihistamínicos',
    'Revisión de resultados de análisis de sangre y evaluación general de salud',
    'Dolor lumbar después de actividad física intensa el fin de semana pasado',
    'Control prenatal de rutina y seguimiento del embarazo de la paciente',
    'Evaluación de manchas en la piel y posible derivación a dermatología',
    'Consulta por ansiedad y estrés académico durante el periodo de exámenes',
    'Revisión oftalmológica por visión borrosa al leer por periodos prolongados',
    'Dolor de estómago recurrente y posible intolerancia a ciertos alimentos',
    'Control de diabetes y ajuste de dosis de insulina según últimos controles',
    'Consulta por insomnio frecuente y cansancio durante el día laboral',
    'Evaluación de lesión en tobillo derecho después de práctica deportiva',
    'Seguimiento de tratamiento para infección urinaria diagnosticada previamente',
]

estados = ['pendiente', 'confirmada', 'completada', 'cancelada', 'pendiente']
hoy = date.today()
citas_creadas = 0
horas = [time(h, m) for h in range(8, 18) for m in (0, 30)]

for i in range(40):
    paciente = random.choice(pacientes)
    medico = random.choice(medicos)
    dias = random.randint(-10, 20)
    fecha = hoy + timedelta(days=dias)
    if fecha.weekday() == 6:
        fecha += timedelta(days=1)
    hora = random.choice(horas)
    # Evitar duplicados exactos
    if Cita.objects.filter(medico=medico, fecha=fecha, hora=hora).exists():
        continue
    if Cita.objects.filter(paciente=paciente, fecha=fecha).exclude(estado='cancelada').exists():
        continue
    estado = random.choice(estados)
    if fecha < hoy and estado in ['pendiente', 'confirmada']:
        estado = random.choice(['completada', 'cancelada', 'no_asistio'])
    cita = Cita.objects.create(
        paciente=paciente,
        medico=medico,
        fecha=fecha,
        hora=hora,
        motivo=random.choice(motivos),
        estado=estado,
        creado_por=admin_user,
    )
    citas_creadas += 1
    # Crear consulta para algunas completadas
    if estado == 'completada' and random.random() > 0.3:
        Consulta.objects.get_or_create(
            cita=cita,
            defaults={
                'diagnostico': 'Diagnóstico de ejemplo basado en el motivo de consulta presentado por el paciente.',
                'tratamiento': 'Tratamiento sintomático y recomendaciones generales de reposo e hidratación.',
                'medicamentos': 'Paracetamol 500mg cada 8 horas por 3 días. Ibuprofeno si persiste el dolor.',
                'registrado_por': medico.user,
            }
        )

print(f"Citas creadas: {citas_creadas}")
print(f"Médicos: {Medico.objects.count()}")
print(f"Pacientes: {Paciente.objects.count()}")
print(f"Consultas: {Consulta.objects.count()}")
print("=== Datos de prueba cargados correctamente ===")
print("\nUsuarios de prueba:")
print("  admin / admin123          (Administrador)")
print("  medico1 / medico123       (Médico)")
print("  recepcion / recep123      (Recepcionista)")
print("  paciente1 / pac123        (Paciente)")
