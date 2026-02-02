from django.contrib import admin
from .models import Farmland

@admin.register(Farmland)
class FarmlandAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'size_acres', 'crop_type')
