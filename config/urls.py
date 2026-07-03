from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    # 🚀 REGLA PRIORITARIA: Intercepta la raíz vacía antes de procesar los sub-routers
    path('', RedirectView.as_view(url='/api/auth/login/', permanent=False), name='raiz_to_login'),
    
    # Administración predeterminada
    path('admin/', admin.site.urls),
    
    # Enrutamiento modular hacia la aplicación
    path('api/', include('tickets.urls')),
]
