from django.db import models
from datetime import timedelta
from videos.models import Video

class Detection(models.Model):
    SEVERITY_CHOICES = [
        ('Low', 'Low'),
        ('Medium', 'Medium'),
        ('High', 'High'),
        ('Critical', 'Critical'),
    ]

    video = models.ForeignKey(Video, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)  # System processing time
    video_timestamp = models.DurationField(default=timedelta(0))              # Event time in video (HH:MM:SS)
    animal_type = models.CharField(max_length=50)
    confidence = models.FloatField()
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES)

    def __str__(self):
        return f"{self.animal_type} - {self.severity}"

    @property
    def formatted_video_timestamp(self):
        """Returns video timestamp as HH:MM:SS"""
        if self.video_timestamp is not None:
            total_seconds = int(self.video_timestamp.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            return f"{hours:02}:{minutes:02}:{seconds:02}"
        return "00:00:00"

class DetectionSnapshot(models.Model):
    detection = models.ForeignKey(Detection, on_delete=models.CASCADE, related_name='snapshots')
    image = models.ImageField(upload_to='snapshots/')
    created_at = models.DateTimeField(auto_now_add=True)
    video_timestamp = models.DurationField(null=True) # Specific time in video
