from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from core import views as core_views
from analytics import views as analytics_views
from detection import views as detection_views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Core Landing & Settings
    path('', core_views.home_view, name='home'),
    path('settings/', core_views.settings_view, name='settings'),

    # Dashboard & Analytics
    path('dashboard/', analytics_views.dashboard_view, name='analytics-dashboard'),
    path('reports/', analytics_views.reports_view, name='reports'),
    
    # App Routes
    path('videos/', include('videos.urls')),
    path('detections/', detection_views.detection_list, name='detection-list'),
    path('alerts/', include('alerts.urls')),
    
    # Utility Routes (Processing, Export APIs)
    path('detection/', include('detection.urls')), # For processing endpoints
    path('analytics/', include('analytics.urls')), # For export APIs
    path('accounts/', include('accounts.urls')),
    path('farmland/', include('farmland.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
