from django.contrib import admin
from .models import Detection, DetectionSnapshot

@admin.register(Detection)
class DetectionAdmin(admin.ModelAdmin):
    list_display = ('video', 'animal_type', 'confidence', 'severity', 'video_timestamp', 'created_at')
    list_filter = ('severity', 'animal_type')

@admin.register(DetectionSnapshot)
class DetectionSnapshotAdmin(admin.ModelAdmin):
    list_display = ('detection', 'video_timestamp', 'created_at')
