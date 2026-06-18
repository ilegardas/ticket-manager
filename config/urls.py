from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('tickets.urls')), # O la ruta de tus endpoints
    
    # Esto obliga a que la raíz redirija automáticamente a la sección de la API
    path('', RedirectView.as_view(url='/api/', permanent=False)),
]
