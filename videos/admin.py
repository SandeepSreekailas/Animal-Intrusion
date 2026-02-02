from django.contrib import admin
from .models import Video

@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ('farmland', 'user', 'timestamp', 'status')
    list_filter = ('status', 'timestamp')
