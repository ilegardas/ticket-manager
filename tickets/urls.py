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
    path('auth/login/', views.login_view, name='login'),
    path('auth/login', views.login_view),
    path('auth/logout/', views.logout_view, name='logout'),
    path('auth/logout', views.logout_view),
    path('auth/me/', views.me_view, name='me'),
    path('auth/me', views.me_view),
    
    # 🛡️ 2. MATCHERS DETERMINISTAS PARA EL TICKET INDIVIDUAL (API)
    path('tickets/<int:pk>/', views.TicketViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'})),
    path('tickets/<int:pk>', views.TicketViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'})),

    # 📥 3. ENDPOINTS RPC COMPATIBLES PARA ACCIONES DE ESCRITURA DE INCIDENCIAS
    path('addchatter/', views.compat_add_chatter, name='compat_add_chatter_cb'),
    path('addchatter', views.compat_add_chatter, name='compat_add_chatter'),
    path('updateticket/', views.compat_update_ticket, name='compat_update_ticket_cb'),
    path('updateticket', views.compat_update_ticket, name='compat_update_ticket'),

    # 📊 4. ENDPOINTS DEL DASHBOARD / REPORTES CORE
    path('reportes/resumen/', views.reporte_resumen),
    path('reportes/por-sistema/', views.reporte_por_sistema),
    path('reportes/por-estado/', views.reporte_por_estado),
    path('reportes/por-prioridad/', views.reporte_por_prioridad),
    path('reportes/sla/', views.reporte_sla),
    path('reportes/tendencias/', views.reporte_tendencias),
    path('reportes/tickets/', views.reporte_tickets),
    path('reportes/actividad-reciente/', views.actividad_reciente),

    # 🖥️ 5. CONTROL DE PANELES INTERNOS INTERACTIVOS (SUITE LOCAL / HTMX)
    path('panel/dashboard/', views.panel_dashboard, name='panel_dashboard'),
    
    # Módulo de Gestión de Incidencias (Tickets)
    path('panel/tickets/', views.panel_tickets_list, name='panel_tickets_list'),
    path('panel/tickets/nuevo/', views.panel_ticket_create, name='panel_ticket_create'),
    path('panel/tickets/<int:pk>/', views.panel_ticket_detail, name='panel_ticket_detail'),
    path('panel/tickets/<int:pk>/chatter/', views.panel_ticket_chatter, name='panel_ticket_chatter'),
    path('panel/tickets/<int:ticket_id>/comentario/', views.panel_ticket_add_comentario, name='panel_ticket_add_comentario'),
    path('panel/tickets/<int:ticket_id>/recordatorio/', views.panel_ticket_enviar_recordatorio, name='panel_ticket_enviar_recordatorio'),
    path('panel/tickets/exportar/excel/', views.panel_tickets_exportar_excel, name='panel_tickets_exportar_excel'),
    
    # Módulo Integrado de Base de Conocimiento (CON)
    path('panel/conocimiento/', views.panel_conocimiento_lista, name='panel_conocimiento_lista'),
    path('panel/conocimiento/crear/', views.panel_conocimiento_crear, name='panel_conocimiento_crear'),
    path('panel/conocimiento/<int:pk>/', views.panel_conocimiento_detalle, name='panel_conocimiento_detalle'),
    path('panel/conocimiento/<int:entrada_id>/editar/', views.panel_conocimiento_editar, name='panel_conocimiento_editar'),
    path('panel/conocimiento/<int:pk>/eliminar/', views.panel_conocimiento_eliminar, name='panel_conocimiento_eliminar'),
    path('panel/conocimiento/importar-csv/', views.panel_conocimiento_importar_csv, name='panel_conocimiento_importar_csv'),
    path('panel/tickets/<int:ticket_id>/convertir/', views.panel_conocimiento_crear_desde_ticket, name='panel_conocimiento_crear_desde_ticket'),
    
    # Módulo de Administración de Usuarios
    path('panel/usuarios/', views.panel_usuarios_list, name='panel_usuarios_list'),
    path('panel/usuarios/crear-manual/', views.panel_usuario_crear, name='panel_usuario_crear'),
    path('panel/usuarios/<int:user_id>/editar/', views.panel_usuario_editar, name='panel_usuario_editar'),
    path('panel/usuarios/<int:user_id>/rol/', views.panel_usuario_cambiar_rol, name='panel_usuario_cambiar_rol'),
    path('panel/usuarios/<int:user_id>/toggle/', views.panel_usuario_toggle_activo, name='panel_usuario_toggle_activo'),
    path('panel/usuarios/<int:user_id>/eliminar/', views.panel_usuario_eliminar, name='panel_usuario_eliminar'),
    path('panel/usuarios/importar-csv/', views.panel_usuario_importar_csv, name='panel_usuario_importar_csv'),
    path('panel/usuarios/exportar/excel/', views.panel_usuarios_exportar_excel, name='panel_usuarios_exportar_excel'),
    
    # Módulo de Configuración de Infraestructura de TI
    path('panel/configuracion/sistemas/', views.panel_config_sistemas, name='panel_config_sistemas'),
    path('panel/configuracion/sistemas/<int:pk>/eliminar/', views.panel_config_sistema_eliminar, name='panel_config_sistema_eliminar'),
    path('panel/configuracion/modulos/', views.panel_config_modulos, name='panel_config_modulos'),
    path('panel/configuracion/modulos/<int:pk>/eliminar/', views.panel_config_cmdb_eliminar, name='panel_config_modulo_eliminar'),
    path('panel/configuracion/categorias/', views.panel_config_categorias, name='panel_config_categorias'),
    path('panel/configuracion/categorias/<int:pk>/eliminar/', views.panel_config_categoria_eliminar, name='panel_config_categoria_eliminar'),
    path('panel/configuracion/sistemas/crear-modal/', views.panel_config_sistema_crear_modal, name='panel_config_sistema_crear_modal'),
    path('panel/configuracion/sistemas/csv-modal/', views.panel_config_sistema_csv_modal, name='panel_config_sistema_csv_modal'),
    path('panel/configuracion/sistemas/importar-csv/', views.panel_config_sistema_importar_csv, name='panel_config_sistema_importar_csv'),
    path('panel/configuracion/sistemas/<int:pk>/editar-modal/', views.panel_config_sistema_editar_modal, name='panel_config_sistema_editar_modal'),
    path('panel/configuracion/sistemas/<int:pk>/actualizar/', views.panel_config_sistema_actualizar, name='panel_config_sistema_actualizar'),
    path('panel/configuracion/modulos/<int:pk>/toggle/', views.panel_config_modulo_toggle_activo, name='panel_config_modulo_toggle_activo'),
    
    # Módulo de Reportería Avanzada y Descargas
    path('panel/reportes/', views.panel_reportes_avanzados, name='panel_reportes_avanzados'),
    path('panel/reportes/exportar/', views.exportar_reporte_csv, name='exportar_reporte_csv'),
    
    # Endpoints de Soporte Asíncrono (AJAX / Dinámico)
    path('ajax/cargar-modulos/', views.ajax_cargar_modulos, name='ajax_cargar_modulos'),

    # CMDB url's
    path('panel/tickets/<int:ticket_id>/responsables-cmdb/', views.ajax_obtener_responsables_cmdb, name='ajax_responsables_cmdb'),
    path('panel/configuracion/cmdb/', views.panel_config_cmdb, name='panel_config_cmdb'),
    path('panel/configuracion/cmdb/<int:pk>/eliminar/', views.panel_config_cmdb_eliminar, name='panel_config_cmdb_eliminar'),

    # ... DIRECTORIO ...
    path('panel/directorio/', views.panel_directorio, name='panel_directorio'),
    path('panel/directorio/exportar/', views.exportar_directorio_excel, name='exportar_directorio_excel'),

    # ... Depaertamentos
    path('panel/departamentos/', views.panel_departamentos, name='panel_departamentos'),
    path('panel/departamentos/crear/', views.departamento_crear, name='departamento_crear'),
    path('panel/departamentos/<int=dept_id>/editar/', views.departamento_editar, name='departamento_editar'),
    
    # 🚀 SOLUCIÓN: El router se monta con un prefijo o se incluye limpiamente sin duplicados
    path('api-root/', include(router.urls)),
]
