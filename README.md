# Plataforma de Gestión de Consultas Médicas - Centro Médico UNCP

**Caso 2 - Práctica Grupal Semana 12**  
**Asignatura:** Desarrollo de Aplicaciones Web (IS093A)  
**Tema:** Gestión de Formularios, Django Admin, Middleware, Sesiones, Autenticación y Autorización

**Integrantes:**
- Andrade Egoavil Ingrid Ivette
- Yaranga Ruiz Josue

---

## Descripción

Sistema web fullstack desarrollado en Django para digitalizar el agendamiento de citas médicas, mantener historial clínico electrónico y controlar el acceso según roles (Administrador, Médico, Recepcionista, Paciente).

Cumple con todos los requisitos funcionales (RF1–RF5) y no funcionales del enunciado.

---

## Características implementadas

### RF1 - Gestión de Pacientes y Médicos
- Modelos `Paciente` y `Medico` con validaciones (DNI 8 dígitos, CMP, fecha de nacimiento, email institucional).
- Campos: alergias, código UNCP, especialidad, consultorio, horarios.

### RF2 - Sistema de Agendamiento (Formularios Complejos)
- `CitaForm` con validaciones cruzadas:
  - Motivo mínimo 20 caracteres
  - Una sola cita por paciente por día
  - Sin solapamiento de horarios del médico
  - Validación de horario de atención (L-V 8-18, Sáb 8-13)
- Formulario de registro de consulta post-atención (diagnóstico, tratamiento, medicamentos).

### RF3 - Autenticación y Autorización Robusta
- Login diferenciado.
- Grupos: Médicos, Recepcionistas, Pacientes, Admins.
- Permisos personalizados: `ver_historial_clinico`, `agendar_cita`, `cancelar_cita`, `generar_reportes`.
- Sesión con timeout de **20 minutos**.

### RF4 - Middleware Especializado
- `AuditoriaMedicaMiddleware`: registra quién accede a historiales clínicos (logs + modelo `LogAuditoria`).
- `ValidacionHorarioMiddleware`: detecta fuera de horario de atención.
- `AlertasCitasMiddleware`: notifica al médico citas pendientes al iniciar sesión.

### RF5 - Django Admin
- `list_display`, `list_filter`, `search_fields`, `date_hierarchy`.
- Acción masiva: “Marcar citas como completadas”.
- Campos calculados: edad del paciente, días desde creación.
- Agenda filtrable por médico y fecha.
- Logs de auditoría de solo lectura.

---

## Requisitos

- Python 3.10+
- Django 5.x / 6.x

## Instalación

```bash
# 1. Clonar el repositorio
git clone <URL-del-repositorio>
cd centro_medico   # o el nombre de la carpeta

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Migraciones
python manage.py migrate

# 5. Cargar datos de prueba (8+ médicos, 15+ pacientes, 30+ citas)
python crear_datos.py

# 6. Ejecutar servidor
python manage.py runserver
```

Abrir: http://127.0.0.1:8000/

---

## Usuarios de prueba

| Usuario     | Contraseña  | Rol            |
|-------------|-------------|----------------|
| admin       | admin123    | Administrador  |
| medico1     | medico123   | Médico         |
| recepcion   | recep123    | Recepcionista  |
| paciente1   | pac123      | Paciente       |

---

## Estructura del proyecto

```
centro_medico/
├── centro_medico/          # Configuración del proyecto
│   ├── settings.py         # Sesiones 20 min, middlewares, logging
│   └── urls.py
├── consultas/              # App principal
│   ├── models.py           # Paciente, Medico, Cita, Consulta, LogAuditoria
│   ├── forms.py            # Formularios con validaciones complejas
│   ├── views.py            # Vistas con control de permisos
│   ├── admin.py            # Django Admin personalizado
│   ├── middleware.py       # 3 middlewares especializados
│   ├── urls.py
│   └── templates/
├── templates/              # Templates base
├── crear_datos.py          # Script de datos de prueba
├── requirements.txt
├── .gitignore
└── README.md
```

---

## División de trabajo (sugerida / implementada)

| Integrante 1 (Modelos, Forms, Admin, Templates) | Integrante 2 (Settings, Middleware, Auth) |
|------------------------------------------------|-------------------------------------------|
| Modelos (Paciente, Médico, Cita, Consulta)     | Configuración base y settings             |
| Formularios complejos + validaciones cruzadas  | Middleware de auditoría médica            |
| Django Admin con agenda y acciones             | Middleware de validación de horario       |
| Plantillas de formularios                      | Sistema de autenticación multi-rol        |
|                                                | Grupos, permisos y autorización           |

---

## Capturas requeridas (para el PDF)

1. Formulario de cita con validaciones complejas (probar motivo corto, día ocupado, horario inválido).
2. Django Admin con agenda, filtros y acción masiva.
3. Middleware de auditoría (ver `/admin/consultas/logauditoria/` después de ver un historial).
4. Control de permisos (usuario sin permiso intenta acceder a historial o reportes → 403).
5. Cookies de sesión / timeout (en DevTools → Application → Cookies, `sessionid` con max-age ≈ 1200s).

---

## Git / Flujo de trabajo

- Ramas: `main`, `dev/integrante-1`, `dev/integrante-2`
- Commits frecuentes
- Pull Requests con code review

---

## Licencia

Proyecto académico - Universidad Nacional del Centro del Perú (UNCP) - 2026
