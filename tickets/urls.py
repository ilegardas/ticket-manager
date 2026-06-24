from django.urls import path, include, re_path
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
    # Enrutamiento Estándar
    path('', include(router.urls)),
    path('auth/login', views.login_view),
    path('auth/logout', views.logout_view),
    path('auth/me', views.me_view),
    
    # Endpoints de Reportes
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
    # ALIAS DE COMPATIBILIDAD PARA EL FRONTEND (SINGULARES Y MÉTODOS)
    # ─────────────────────────────────────────────────────────────────
    path('ticket', views.TicketViewSet.as_view({'get': 'list', 'post': 'create'})),
    path('ticket/', views.TicketViewSet.as_view({'get': 'list', 'post': 'create'})),
    
    # 🔴 CORREGIDO: '?P<pk>' con P mayúscula para evitar el SyntaxError de Railway
    re_path(r'^ticket/(?P<pk>\d+)/?$', views.TicketViewSet.as_view({
        'get': 'retrieve', 
        'put': 'update', 
        'patch': 'partial_update', 
        'delete': 'destroy'
    })),
    
    # Historial (Chatter) y Tiempos de Pausa
    path('chatter', views.compat_chatter_list), 
    path('chatter/', views.compat_chatter_list),
    path('timelogs', views.compat_timelogs_list),
    path('timelogs/', views.compat_timelogs_list),
    
    path('sistema', views.SistemaViewSet.as_view({'get': 'list', 'post': 'create'})),
    path('sistema/', views.SistemaViewSet.as_view({'get': 'list', 'post': 'create'})),
    
    # CRUD de Usuarios mediante Vistas de Compatibilidad
    path('createusuario', views.compat_create_usuario),
    path('createusuario/', views.compat_create_usuario),
    
    path('updateusuario', views.compat_update_usuario),
    path('updateusuario/', views.compat_update_usuario),
    path('updateusuario/<int:pk>', views.compat_update_usuario),
    path('updateusuario/<int:pk>/', views.compat_update_usuario),
    
    path('deleteusuario', views.compat_delete_usuario),
    path('deleteusuario/', views.compat_delete_usuario),
    path('deleteusuario/<int:pk>', views.compat_delete_usuario),
    path('deleteusuario/<int:pk>/', views.compat_delete_usuario),
    
    # Formularios de Creación Auxiliares
    path('createticket', views.compat_create_ticket),
    path('createticket/', views.compat_create_ticket),
    path('createmodulo', views.compat_create_modulo),
    path('createmodulo/', views.compat_create_modulo),
    path('createconocimiento', views.compat_create_conocimiento),
    path('createconocimiento/', views.compat_create_conocimiento),

    # Duplicados heredados para asegurar la compatibilidad de reportes históricos
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
