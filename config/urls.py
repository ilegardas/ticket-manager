from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # 🎯 ÚNICA RUTA API: Todo lo que empiece con api/ se procesará dentro de tickets/urls.py
    path('api/', include('tickets.urls')), 
]
