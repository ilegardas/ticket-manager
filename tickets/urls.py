from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

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
    # Enrutamiento estándar
    path('', include(router.urls)),
    path('auth/login', views.login_view),
    path('auth/logout', views.logout_view),
    path('auth/me', views.me_view),
    
    # Reportes Oficiales
    path('reportes/resumen', views.reporte_resumen),
    path('reportes/por-sistema', views.reporte_por_sistema),
    path('reportes/por-estado', views.reporte_por_estado),
    path('reportes/por-prioridad', views.reporte_por_prioridad),
    path('reportes/sla', views.reporte_sla),
    path('reportes/tendencias', views.reporte_tendencias),
    path('reportes/por-region', views.reporte_por_region),
    path('reportes/tickets', views.reporte_tickets),
    path('reportes/actividad-reciente', views.actividad_reciente),

    # ─────────────────────────────────────────────────────────────────
    # ALIAS DE COMPATIBILIDAD PARA EL FRONTEND (RESUELVE LOS 404 Y 500)
    # ─────────────────────────────────────────────────────────────────
    path('ticket', views.TicketViewSet.as_view({'get': 'list', 'post': 'create'})),
    path('ticket/', views.TicketViewSet.as_view({'get': 'list', 'post': 'create'})),
    path('ticket/<int:pk>', views.TicketViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'})),
    path('ticket/<int:pk>/', views.TicketViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'})),
    
    path('chatter', views.compat_chatter_list), 
    path('chatter/', views.compat_chatter_list),
    path('timelogs', views.compat_timelogs_list),
    path('timelogs/', views.compat_timelogs_list),
    
    path('sistema', views.SistemaViewSet.as_view({'get': 'list', 'post': 'create'})),
    path('sistema/', views.SistemaViewSet.as_view({'get': 'list', 'post': 'create'})),
    
    path('createusuario', views.compat_create_usuario),
    path('createusuario/', views.compat_create_usuario),
    path('updateusuario', views.compat_update_usuario),
    path('updateusuario/', views.compat_update_usuario),
    path('updateusuario/<int:pk>', views.compat_update_usuario),
    path('updateusuario/<int:pk>/', views.compat_update_usuario),
    
    path('createticket', views.compat_create_ticket),
    path('createticket/', views.compat_create_ticket),
    path('createmodulo', views.compat_create_modulo),
    path('createmodulo/', views.compat_create_modulo),
    path('createconocimiento', views.compat_create_conocimiento),
    path('createconocimiento/', views.compat_create_conocimiento),

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
    path('actividadreciente', views.actividad_reciente),
    path('actividadreciente/', views.actividad_reciente),
    path('reporteporregion', views.reporte_por_region),
    path('reporteporregion/', views.reporte_por_region),
    path('reportesla', views.reporte_sla),
    path('reportesla/', views.reporte_sla),
    path('reportettickets', views.reporte_tickets),
    path('reportettickets/', views.reporte_tickets),
    path('reportetickets', views.reporte_tickets),
    path('reportetickets/', views.reporte_tickets),
]
