from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Inicializamos el router para los ViewSets estándar de la app
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
    
    # 🔄 2. ENDPOINTS RPC REQUERIDOS POR TU CLIENTE DE REACT
    path('addchatter', views.compat_add_chatter, name='compat_add_chatter'),
    path('addchatter/', views.compat_add_chatter, name='compat_add_chatter_cb'),
    path('updateticket', views.compat_update_ticket, name='compat_update_ticket'),
    path('updateticket/', views.compat_update_ticket, name='compat_update_ticket_cb'),

    # 📊 3. ENDPOINTS DEL DASHBOARD / REPORTES CORE (Estructura Nueva)
    path('reportes/resumen', views.reporte_resumen),
    path('reportes/por-sistema', views.reporte_por_sistema),
    path('reportes/por-estado', views.reporte_por_estado),
    path('reportes/por-prioridad', views.reporte_por_prioridad),
    path('reportes/sla', views.reporte_sla),
    path('reportes/tendencias', views.reporte_tendencias),
    path('reportes/por-region', views.reporte_por_region),
    path('reportes/tickets', views.reporte_tickets),
    path('reportes/actividad-reciente', views.actividad_reciente),

    # ⚠️ 4. RUTAS ESPEJO / LEGACY (Las que tu Frontend busca en la raíz y daban 404)
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
    path('reporteporregion', views.reporte_por_region),
    path('reporteporregion/', views.reporte_por_region),
    path('reportesla', views.reporte_sla),
    path('reportesla/', views.reportesla if hasattr(views, 'reportesla') else views.reporte_sla),

    # 🛠️ 5. CREACIÓN DE AUXILIARES LEGACY (Formularios como Agregar Módulos)
    path('createmodulo', views.compat_create_modulo),
    path('createmodulo/', views.compat_create_modulo),
    path('createticket', views.compat_create_ticket),
    path('createticket/', views.compat_create_ticket),
    path('createconocimiento', views.compat_create_conocimiento),
    path('createconocimiento/', views.compat_create_conocimiento),
    path('createusuario', views.compat_create_usuario),
    path('createusuario/', views.compat_create_usuario),

    # 🔌 6. RUTAS AUTOMÁTICAS DE LOS VIEWSETS (Siempre al final)
    path('', include(router.urls)),
]
