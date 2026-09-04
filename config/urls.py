from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from financeiro.views import dashboard

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', dashboard, name='home'),
    path('clientes/', include('core.urls')),
    path('producao/', include('producao.urls')),
    path('financeiro/', include('financeiro.urls')),
    path('juridico/', include('juridico.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)