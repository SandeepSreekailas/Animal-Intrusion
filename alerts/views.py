from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.core.paginator import Paginator
from .models import Alert

@login_required
def alert_list(request):
    alert_qs = Alert.objects.filter(user=request.user).order_by('-created_at')
    paginator = Paginator(alert_qs, 20) # 20 per page
    page_number = request.GET.get('page')
    alerts = paginator.get_page(page_number)
    return render(request, 'alerts/alert_list.html', {'alerts': alerts})

@login_required
@require_POST
def mark_alert_read(request, pk):
    alert = get_object_or_404(Alert, pk=pk, user=request.user)
    alert.is_read = True
    alert.save()
    messages.success(request, "Alert marked as read.")
    return redirect('alert-list')
