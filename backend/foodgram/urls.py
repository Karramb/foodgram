from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from api.urls import urls as api_urls
from api.views import short_url

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(api_urls)),
    path('s/<int:pk>/', short_url, name='short_url')
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns += static(settings.STATIC_URL,
                          document_root=settings.STATIC_ROOT)
    urlpatterns += (path('__debug__/', include(debug_toolbar.urls)),)
