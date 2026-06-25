from django.urls import path, include
from rest_framework.routers import DefaultRouter
from tickets import views

router = DefaultRouter(trailing_slash=False) # o True dependiendo de cómo esté configurado tu frontend
router.register(r'tickets', views.TicketViewSet)

urlpatterns = [
    # Endpoints manuales de compatibilidad primero
    path('api/addchatter', views.compat_add_chatter, name='compat_add_chatter'),
    path('api/updateticket', views.compat_update_ticket, name='compat_update_ticket'),
    
    # Rutas automáticas del router del ViewSet al final
    path('api/', include(router.urls)),
]
