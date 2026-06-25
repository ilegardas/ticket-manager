from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Inicializamos los routers duales estándar
router_no_slash = DefaultRouter(trailing_slash=False)
router_slash = DefaultRouter(trailing_slash=True)

for r in [router_no_slash, router_slash]:
    r.register(r'tickets', views.TicketViewSet, basename='ticket')
    r.register(r'sistemas', views.SistemaViewSet, basename='sistema')
    r.register(r'modulos', views.ModuloViewSet, basename='modulo')
    r.register(r'documentos', views.DocumentoViewSet, basename='documento')
    r.register(r'usuarios', views.UsuarioViewSet, basename='usuario')
    r.register(r'prioridades', views.PrioridadViewSet, basename='prioridad')
    r.register(r'estados', views.EstadoViewSet, basename='estado')
    r.register(r'categorias', views.CategoriaViewSet, basename='categoria')
    r.register(r'conocimiento', views.ConocimientoViewSet, basename='conocimiento')

urlpatterns = [
    # 🔐 1. AUTENTICACIÓN
    path('auth/login', views.login_view),
    path('auth/login/', views.login_view),
    path('auth/logout', views.logout_view),
    path('auth/logout/', views.logout_view),
    path('auth/me', views.me_view),
    path('auth/me/', views.me_view),
    
    # 🛡️ 2. MATCHERS DETERMINISTAS PARA EL TICKET INDIVIDUAL (Garantiza romper el 404 de /api/tickets/22)
    path('tickets/<int:pk>', views.TicketViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'})),
    path('tickets/<int:pk>/', views.TicketViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'})),
    path('tickets<int:pk>', views.TicketViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'})),
    path('tickets<int:pk>/', views.TicketViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'})),

    # 🔄 3. ENDPOINTS RPC REQUERIDOS POR EL CLIENTE DE REACT
    path('addchatter', views.compat_add_chatter, name='compat_add_chatter'),
    path('addchatter/', views.compat_add_chatter, name='compat_add_chatter_cb'),
    path('updateticket', views.compat_update_ticket, name='compat_update_ticket'),
    path('updateticket/', views.compat_update_ticket, name='compat_update_ticket_cb'),

    # 📊 4. ENDPOINTS DEL DASHBOARD / REPORTES CORE
    path('reportes/resumen', views.reporte_resumen),
    path('reportes/por-sistema', views.reporte_por_sistema),
    path('reportes/por-estado', views.reporte_por_estado),
    path('reportes/por-prioridad', views.reporte_por_prioridad),
    path('reportes/sla', views.reporte_sla),
    path('reportes/tendencias', views.reporte_tendencias),
    path('reportes/por-region', views.reporte_por_region),
    path('reportes/tickets', views.reporte_tickets),
    path('reportes/actividad-reciente', views.actividad_reciente),

    # ⚠️ 5. RUTAS ESPEJO / LEGACY MATCHERS DEL DASHBOARD
    path('reporteresumen', views.reporte_resumen),
    path('reporteresumen/', views.reporte_resumen),
    path('reporteporsistema', views.reporte_por_sistema),
    path('reporteporsistema/', views.reporte_por_sistema),
    path('reporteporestado', views.reporte_por_estado),
    path('reporteporestado/', views.reporte_por_estado),
    path('reporteporprioridad', views.reporte_por_prioridad),
    path('reporteporprioridad/', views.reporte_por_prioridad),
    path('reportetendencias', views.reporte_tendencias),
    path('reportettendencias/', views.reporte_tendencias),
    path('reportetickets', views.reporte_tickets),
    path('reportetickets/', views.reporte_tickets),
    path('actividadreciente', views.actividad_reciente),
    path('actividadreciente/', views.actividad_reciente),

    # 🛠️ 6. ACCIONES Y OPERACIONES AUXILIARES LEGACY (Resuelve deletemodulo)
    path('createmodulo', views.compat_create_modulo),
    path('createmodulo/', views.compat_create_modulo),
    path('deletemodulo', views.compat_delete_modulo),
    path('deletemodulo/', views.compat_delete_modulo),
    path('createticket', views.compat_create_ticket),
    path('createticket/', views.compat_create_ticket),
    path('createconocimiento', views.compat_create_conocimiento),
    path('createconocimiento/', views.compat_create_conocimiento),
    path('deleteconocimiento', views.compat_delete_conocimiento),
    path('deleteconocimiento/', views.compat_delete_conocimiento),
    path('createusuario', views.compat_create_usuario),
    path('createusuario/', views.compat_create_usuario),
    path('deleteusuario', views.compat_delete_usuario),
    path('deleteusuario/', views.compat_delete_usuario),

    # 🔌 7. ENTRADA HÍBRIDA DE LOS ROUTERS PARA COLECCIONES (Estados, Prioridades, etc.)
    path('', include(router_no_slash.urls)),
    path('', include(router_slash.urls)),
]
