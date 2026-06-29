from django.urls import path, include, re_path
from rest_framework.routers import DefaultRouter
from . import views

# Inicializamos el router base estándar
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
    # 🔐 1. AUTENTICACIÓN
    path('auth/login', views.login_view),
    path('auth/login/', views.login_view),
    path('auth/logout', views.logout_view),
    path('auth/logout/', views.logout_view),
    path('auth/me', views.me_view),
    path('auth/me/', views.me_view),
    
    # 🛡️ 2. MATCHERS DETERMINISTAS PARA EL TICKET INDIVIDUAL
    path('tickets/<int:pk>', views.TicketViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'})),
    path('tickets/<int:pk>/', views.TicketViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'})),
    path('tickets<int:pk>', views.TicketViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'})),
    path('tickets<int:pk>/', views.TicketViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'})),

    # 🔄 3. ALIAS CRÍTICOS PARA LAS CONSULTAS DEL TICKET DETAIL (Evita h.map y objetos vacíos)
    path('chatter', views.compat_chatter_list),
    path('chatter/', views.compat_chatter_list),
    path('timelogs', views.compat_timelogs_list),
    path('timelogs/', views.compat_timelogs_list),

    # 📥 4. ENDPOINTS RPC PARA ACCIONES (🛡️ Duplicados con y sin diagonal para frenar el RuntimeError de APPEND_SLASH)
    path('addchatter', views.compat_add_chatter, name='compat_add_chatter'),
    path('addchatter/', views.compat_add_chatter, name='compat_add_chatter_cb'),
    path('updateticket', views.compat_update_ticket, name='compat_update_ticket'),
    path('updateticket/', views.compat_update_ticket, name='compat_update_ticket_cb'),
    
    # Soporte para recordatorios y reaperturas si los tiene configurados en views
    path('remindticket', views.compat_update_ticket), 
    path('remindticket/', views.compat_update_ticket),
    path('reopenticket', views.compat_update_ticket),
    path('reopenticket/', views.compat_update_ticket),

    # 📊 5. ENDPOINTS DEL DASHBOARD / REPORTES CORE
    path('reportes/resumen', views.reporte_resumen),
    path('reportes/por-sistema', views.reporte_por_sistema),
    path('reportes/por-estado', views.reporte_por_estado),
    path('reportes/por-prioridad', views.reporte_por_prioridad),
    path('reportes/sla', views.reporte_sla),
    path('reportes/tendencias', views.reporte_tendencias),
    path('reportes/por-region', views.reporte_por_region),
    path('reportes/tickets', views.reporte_tickets),
    path('reportes/actividad-reciente', views.actividad_reciente),

    # ⚠️ 6. RUTAS ESPEJO / LEGACY MATCHERS DEL DASHBOARD
    path('reporteresumen', views.reporte_resumen),
    path('reporteresumen/', views.reporte_resumen),
    path('reporteporsistema', views.reporte_por_sistema),
    path('reporteporsistema/', views.reporte_por_sistema),
    path('reporteporestado', views.reporte_por_estado),
    path('reporteporestado/', views.reporte_por_estado),
    path('reporteporprioridad', views.reporte_por_prioridad),
    path('reporteporprioridad/', views.reporte_por_prioridad),
    path('reportetendencias', views.reporte_tendencias),
    path('reportetendencias/', views.reporte_tendencias),
    path('reportetickets', views.reporte_tickets),
    path('reportetickets/', views.reporte_tickets),
    path('actividadreciente', views.actividad_reciente),
    path('actividadreciente/', views.actividad_reciente),

    # 🛠️ 7. ACCIONES Y OPERACIONES AUXILIARES LEGACY
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

    # 🖥️ CONTROL DE PANELES INTERNOS (MIGRACIÓN HYBRIDA)
    path('panel/tickets/', views.panel_tickets_list, name='panel_tickets_list'),
    path('panel/tickets/<int:pk>/', views.panel_ticket_detail, name='panel_ticket_detail'),
    path('panel/tickets/<int:pk>/chatter/', views.panel_ticket_chatter, name='panel_ticket_chatter'),
    path('panel/dashboard/', views.panel_dashboard, name='panel_dashboard'),
    path('panel/tickets/nuevo/', views.panel_ticket_create, name='panel_ticket_create'),
    path('panel/conocimiento/', views.panel_conocimiento_lista, name='panel_conocimiento_lista'),
    path('panel/tickets/<int:ticket_id>/convertir/', views.panel_conocimiento_crear_desde_ticket, name='panel_conocimiento_crear_desde_ticket'),

    
    # 🔌 8. ENTRADA DE ROUTER HÍBRIDA TOLERANTE A INTERFERENCIAS
    re_path(r'^(?P<url>.*)/$', include(router.urls)),
    path('', include(router.urls)),
]
