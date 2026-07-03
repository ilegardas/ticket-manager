from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView  # Importación obligatoria

urlpatterns = [
    admin.site.urls,
    path('api/', include('tickets.urls')),
    
    # 🚀 REDIRECCIÓN CORREGIDA: Apunta la raíz física directamente al login de la API
    path('', RedirectView.as_view(url='/api/auth/login/', permanent=False), name='raiz_to_login'),
]
