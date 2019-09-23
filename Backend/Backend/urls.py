from django.contrib import admin
from django.urls import path, include
from ebayItems.tasks import ebay_badewanne_update


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include(('ebayItems.urls', 'ebayItems'), namespace='ebayItems')),
    path('accounts/', include('django.contrib.auth.urls')),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework'))
]

ebay_badewanne_update(repeat=900, repeat_until=None)