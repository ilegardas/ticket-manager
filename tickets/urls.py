from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Inicializamos el router para los ViewSets estándar  
router = DefaultRouter(trailing_slash=False)
router.register(r'tickets', views.TicketViewSet, basename='ticket')
router.register(r'sistemas', views.SistemaViewSet, basename='sistema')
router.register(r'modulos', views.ModuloViewSet, basename='modulo')
router.register(r'documentos', views.DocumentoViewSet, basename='documento')
router.register(r'usuarios', views.UsuarioViewSet, basename='usuario')
router.register(r'prioridades', views.PrioridadViewSet, basename='prioridad')
router.register(r'estados', views.EstadoViewSet, basename='estado')
router.register(r'categorias', views.CategoriaViewSet, basename='categoria')
router.register(r'conocimiento', views.ConocimientoViewSet, basename='conocimiento')

urlpatterns = [
    # 🔐 1. RUTAS DE AUTENTICACIÓN (Con y sin barra para blindar al frontend)
    path('auth/login', views.login_view),
    path('auth/login/', views.login_view),
    path('auth/logout', views.logout_view),
    path('auth/logout/', views.logout_view),
    path('auth/me', views.me_view),
    path('auth/me/', views.me_view),
    
    # 🔄 2. ENDPOINTS RPC REQUERIDOS POR EL CLIENTE DE REACT
    path('addchatter', views.compat_add_chatter, name='compat_add_chatter'),
    path('addchatter/', views.compat_add_chatter, name='compat_add_chatter_cb'),
    path('updateticket', views.compat_update_ticket, name='compat_update_ticket'),
    path('updateticket/', views.compat_update_ticket, name='compat_update_ticket_cb'),
    path('reportetickets', views.reporte_tickets, name='reporte_tickets_legacy'),
    path('reportetickets/', views.reporte_tickets, name='reporte_tickets_legacy_cb'),

    # 📊 3. ENDPOINTS DEL DASHBOARD / REPORTES CORE
    path('reportes/resumen', views.reporte_resumen),
    path('reportes/por-sistema', views.reporte_por_sistema),
    path('reportes/por-estado', views.reporte_por_estado),
    path('reportes/por-prioridad', views.reporte_por_prioridad),
    path('reportes/sla', views.reporte_sla),
    path('reportes/tendencias', views.reporte_tendencias),
    path('reportes/por-region', views.reporte_por_region),
    path('reportes/tickets', views.reporte_tickets),
    path('reportes/actividad-reciente', views.actividad_reciente),

    # 🔌 4. RUTAS AUTOMÁTICAS DE LOS VIEWSETS (Siempre al final)
    path('', include(router.urls)),
]
