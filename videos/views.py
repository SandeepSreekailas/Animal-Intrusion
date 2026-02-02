from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from .models import Video
from .forms import VideoForm
from .utils import extract_metadata_and_thumbnail

@login_required
def video_list(request):
    video_qs = Video.objects.filter(user=request.user).order_by('-timestamp')
    paginator = Paginator(video_qs, 9) # 9 per page (Grid friendly)
    page_number = request.GET.get('page')
    videos = paginator.get_page(page_number)
    return render(request, 'videos/video_list.html', {'videos': videos})

@login_required
def video_create(request):
    if request.method == 'POST':
        form = VideoForm(request.user, request.POST, request.FILES)
        if form.is_valid():
            video = form.save(commit=False)
            video.user = request.user
            video.status = 'Pending'
            video.save()
            
            # Extract Metadata & Thumbnail (Sync for now)
            try:
                extract_metadata_and_thumbnail(video)
            except Exception as e:
                print(f"Error extracting metadata: {e}")
            
            return redirect('video-list')
    else:
        form = VideoForm(request.user)
    return render(request, 'videos/video_form.html', {'form': form})

@login_required
def video_detail(request, pk):
    video = get_object_or_404(Video, pk=pk, user=request.user)
    detections = video.detection_set.all()
    return render(request, 'videos/video_detail.html', {'video': video, 'detections': detections})

@login_required
def video_delete(request, pk):
    video = get_object_or_404(Video, pk=pk, user=request.user)
    if request.method == 'POST':
        video.delete()
        return redirect('video-list')
    return render(request, 'videos/video_confirm_delete.html', {'video': video})
