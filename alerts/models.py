from django.db import models
from django.contrib.auth.models import User
from videos.models import Video

class Alert(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    video = models.ForeignKey(Video, on_delete=models.CASCADE, null=True, blank=True)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    severity = models.CharField(max_length=20)

    def __str__(self):
        return f"Alert for {self.user.username}: {self.severity}"
