from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

def home_view(request):
    """
    Landing page. Redirects to dashboard if user is authenticated.
    """
    if request.user.is_authenticated:
        return redirect('analytics-dashboard')
    return render(request, 'core/home.html')

@login_required
def settings_view(request):
    """
    Placeholder settings page.
    """
    return render(request, 'core/settings.html')
