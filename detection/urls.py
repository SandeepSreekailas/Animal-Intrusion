from django.urls import path
from . import views

urlpatterns = [
    path('process/<int:video_id>/', views.start_processing, name='start-processing'),
    path('status/<int:video_id>/', views.get_processing_status, name='get-processing-status'),
    path('gallery/<int:video_id>/', views.snapshot_gallery, name='snapshot-gallery'),
]
