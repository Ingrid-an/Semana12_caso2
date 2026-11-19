from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('pacientes/', views.lista_pacientes, name='lista_pacientes'),
    path('pacientes/nuevo/', views.crear_paciente, name='crear_paciente'),
    path('citas/agendar/', views.agendar_cita, name='agendar_cita'),
    path('citas/', views.mis_citas, name='mis_citas'),
    path('citas/<int:pk>/cancelar/', views.cancelar_cita, name='cancelar_cita'),
    path('historial/<int:pk>/', views.historial_paciente, name='historial_paciente'),
    path('consulta/<int:cita_id>/registrar/', views.registrar_consulta, name='registrar_consulta'),
    path('agenda/', views.agenda_medico, name='agenda_medico'),
    path('reportes/', views.reportes, name='reportes'),
]
