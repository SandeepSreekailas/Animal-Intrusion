import cv2
import os
from django.core.files.base import ContentFile
from datetime import timedelta

def extract_metadata_and_thumbnail(video_instance):
    """
    Extracts metadata (duration, fps, resolution) and generates a thumbnail.
    """
    video_path = video_instance.video_file.path
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        return

    # Extract Metadata
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    if fps > 0:
        duration_seconds = frame_count / fps
        video_instance.duration = timedelta(seconds=duration_seconds)
    
    video_instance.fps = fps
    video_instance.resolution = f"{width}x{height}"

    # Generate Thumbnail (First Frame)
    ret, frame = cap.read()
    if ret:
        # Resize for thumbnail (optional, keeping original aspect ratio or max width)
        # Let's just save the first frame as is or slightly smaller if huge
        # cv2.imwrite... but we need to save to Django field
        ret, buffer = cv2.imencode('.jpg', frame)
        if ret:
            file_name = f"thumb_{video_instance.pk}.jpg"
            content = ContentFile(buffer.tobytes())
            video_instance.thumbnail.save(file_name, content, save=False)

    cap.release()
    video_instance.save()
