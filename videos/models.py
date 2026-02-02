from django.db import models
from django.contrib.auth.models import User
from farmland.models import Farmland

from django.core.validators import FileExtensionValidator

class Video(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Processing', 'Processing'),
        ('Processed', 'Processed'),
        ('Error', 'Error'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    farmland = models.ForeignKey(Farmland, on_delete=models.CASCADE)
    video_file = models.FileField(
        upload_to='videos/',
        validators=[FileExtensionValidator(allowed_extensions=['mp4', 'avi', 'mov', 'mkv'])]
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    
    # Metadata
    duration = models.DurationField(null=True, blank=True)
    fps = models.FloatField(null=True, blank=True)
    resolution = models.CharField(max_length=20, blank=True) # e.g., "1920x1080"
    thumbnail = models.ImageField(upload_to='videos/thumbnails/', null=True, blank=True)

    def __str__(self):
        return f"{self.farmland.name} - {self.timestamp}"
