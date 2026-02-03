from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

def home_view(request):
    """
    Landing page. Redirects to dashboard if user is authenticated.
    """
    if request.user.is_authenticated:
        return redirect('analytics-dashboard')
    return render(request, 'core/home.html')

from django.contrib import messages
from accounts.forms import ProfileUpdateForm

@login_required
def settings_view(request):
    """
    Settings page with Edit Profile option.
    """
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('settings')
    else:
        form = ProfileUpdateForm(instance=request.user)
    
    return render(request, 'core/settings.html', {'form': form})
