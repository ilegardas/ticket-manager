from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.http import JsonResponse

def health_check(request):
    return JsonResponse({'status': 'ok'})

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('tickets.urls')),
    #path('api/healthz', health_check),
    
    # Redirigir la raíz de la página directamente a /api/
    path('', RedirectView.as_view(url='api/', permanent=False)),
]
