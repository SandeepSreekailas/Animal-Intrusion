from django import forms
from .models import Farmland

class FarmlandForm(forms.ModelForm):
    class Meta:
        model = Farmland
        fields = ['name', 'location', 'size_acres', 'crop_type']
