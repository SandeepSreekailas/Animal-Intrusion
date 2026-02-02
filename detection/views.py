from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from videos.models import Video
from .processor import VideoProcessor
from .models import DetectionSnapshot
import threading

@login_required
def start_processing(request, video_id):
    video = get_object_or_404(Video, pk=video_id, user=request.user)
    
    # Mark as processing immediately
    video.status = 'Processing'
    video.save()
    
    def run_process(vid_obj):
        processor = VideoProcessor(vid_obj)
        processor.process()

    # Fire and forget thread
    thread = threading.Thread(target=run_process, args=(video,))
    thread.daemon = True # ensure it dies if server dies
    thread.start()
    
    return redirect('video-detail', pk=video_id)

@login_required
def get_processing_status(request, video_id):
    """
    API to poll for video status and detections.
    Returns live detection messages for real-time recognition.
    """
    video = get_object_or_404(Video, pk=video_id, user=request.user)
    detections = video.detection_set.all().order_by('-created_at')
    
    # Get recent alerts for live recognition messages
    recent_alerts = video.alert_set.filter(
        severity__in=['High', 'Critical', 'Medium']
    ).order_by('-created_at')[:10]  # Last 10 alerts
    
    det_list = []
    for d in detections:
        thumb_url = d.snapshots.first().image.url if d.snapshots.first() else None
        det_list.append({
            'time': timezone.localtime(d.created_at).strftime("%H:%M:%S"), # System time
            'type': d.animal_type,
            'severity': d.severity,
            'thumb': thumb_url,
            'id': d.id
        })
    
    # Get live recognition messages from recent alerts
    live_messages = []
    for alert in recent_alerts:
        if 'detected' in alert.message.lower():
            live_messages.append({
                'message': alert.message,
                'severity': alert.severity,
                'time': timezone.localtime(alert.created_at).strftime("%H:%M:%S")
            })
        
    return JsonResponse({
        'status': video.status,
        'detections': det_list,
        'live_messages': live_messages[:5]  # Return last 5 live messages
    })

@login_required
def snapshot_gallery(request, video_id):
    video = get_object_or_404(Video, pk=video_id, user=request.user)
    severity = request.GET.get('severity')
    
    snapshots = DetectionSnapshot.objects.filter(detection__video=video).order_by('video_timestamp')
    
    if severity:
        snapshots = snapshots.filter(detection__severity=severity)
        
    return render(request, 'detection/snapshot_gallery.html', {
        'video_id': video.id,
        'video_file_name': video.video_file.name,
        'snapshots': snapshots
    })

@login_required
def detection_list(request):
    """
    List all detection events with snapshots.
    """
    from .models import Detection
    detections = Detection.objects.filter(video__user=request.user).select_related('video', 'video__farmland').order_by('-created_at')
    return render(request, 'detection/detection_list.html', {'detections': detections})
