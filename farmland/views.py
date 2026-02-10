from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from .models import Farmland
from .forms import FarmlandForm

@login_required
def farmland_list(request):
    farmland_qs = Farmland.objects.filter(user=request.user).order_by('-id')
    paginator = Paginator(farmland_qs, 10) 
    page_number = request.GET.get('page')
    farmlands = paginator.get_page(page_number)
    return render(request, 'farmland/farmland_list.html', {'farmlands': farmlands})

@login_required
def farmland_create(request):
    if request.method == 'POST':
        form = FarmlandForm(request.POST)
        if form.is_valid():
            farmland = form.save(commit=False)
            farmland.user = request.user
            farmland.save()
            return redirect('farmland-list')
    else:
        form = FarmlandForm()
    return render(request, 'farmland/farmland_form.html', {'form': form, 'title': 'Add Farmland'})

@login_required
def farmland_update(request, pk): 
    farmland = get_object_or_404(Farmland, pk=pk, user=request.user)
    if request.method == 'POST':
        form = FarmlandForm(request.POST, instance=farmland)
        if form.is_valid():
            form.save()
            return redirect('farmland-list')
    else:
        form = FarmlandForm(instance=farmland)
    return render(request, 'farmland/farmland_form.html', {'form': form, 'title': 'Edit Farmland'})

@login_required
def farmland_delete(request, pk):
    farmland = get_object_or_404(Farmland, pk=pk, user=request.user)
    if request.method == 'POST':
        farmland.delete()
        return redirect('farmland-list')
    return render(request, 'farmland/farmland_confirm_delete.html', {'farmland': farmland})
