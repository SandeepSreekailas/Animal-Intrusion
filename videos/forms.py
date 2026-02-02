from django import forms
from .models import Video
from farmland.models import Farmland
import os

class VideoForm(forms.ModelForm):
    class Meta:
        model = Video
        fields = ['farmland', 'video_file']

    def __init__(self, user, *args, **kwargs):
        super(VideoForm, self).__init__(*args, **kwargs)
        self.fields['farmland'].queryset = Farmland.objects.filter(user=user)

    def clean_video_file(self):
        video = self.cleaned_data.get('video_file')
        
        if video:
            # Check file size (500MB)
            if video.size > 500 * 1024 * 1024:
                raise forms.ValidationError("File size too large. Max 500MB.")
            
            # Check extension
            ext = os.path.splitext(video.name)[1].lower()
            valid_extensions = ['.mp4', '.avi', '.mov', '.mkv']
            if ext not in valid_extensions:
                raise forms.ValidationError("Unsupported file format. Allowed: MP4, AVI, MOV, MKV.")
            
        return video
