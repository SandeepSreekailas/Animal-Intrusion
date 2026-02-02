import cv2
import numpy as np
import os
from django.conf import settings
from django.core.files.base import ContentFile
from .models import Detection, DetectionSnapshot
from alerts.models import Alert
from datetime import timedelta

def process_video(video_instance):
    """
    Processes a video for motion detection.
    Updates Video status, creates Detections, Snapshots, and Alerts.
    """
    video_path = video_instance.video_file.path
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        video_instance.status = 'Error'
        video_instance.save()
        return

    video_instance.status = 'Processing'
    video_instance.save()

    try:
        # Motion detection parameters
        fgbg = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=50, detectShadows=False)
        frame_rate = cap.get(cv2.CAP_PROP_FPS)
        min_contour_area = 500  # Sensitivity
        
        frame_count = 0
        last_detection_time = -10  # Seconds
        detection_cooldown = 2.0   # Seconds between detections

        detections_made = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1
            current_time = frame_count / frame_rate

            # specific resizing for consistency
            frame = cv2.resize(frame, (640, 480))
            
            # Apply background subtraction
            fgmask = fgbg.apply(frame)
            
            # Remove noise
            kernel = np.ones((5,5), np.uint8)
            fgmask = cv2.morphologyEx(fgmask, cv2.MORPH_OPEN, kernel)
            
            # Find contours
            contours, _ = cv2.findContours(fgmask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            motion_detected = False
            for contour in contours:
                if cv2.contourArea(contour) > min_contour_area:
                    motion_detected = True
                    break
            
            # If motion detected and cooldown passed
            if motion_detected and (current_time - last_detection_time > detection_cooldown):
                last_detection_time = current_time
                detections_made += 1

                # Create Detection record
                video_time_delta = timedelta(seconds=current_time)
                
                detection = Detection.objects.create(
                    video=video_instance,
                    animal_type="Unknown Animal (Motion)", # generic for motion
                    confidence=0.85,
                    severity='High',
                    video_timestamp=video_time_delta # Event time in video
                    # created_at is auto_now_add=True
                )

                # Save Snapshot
                # Encode frame to jpg
                ret, buffer = cv2.imencode('.jpg', frame)
                if ret:
                    file_name = f"snapshot_{video_instance.pk}_{frame_count}.jpg"
                    content = ContentFile(buffer.tobytes())
                    snapshot = DetectionSnapshot(detection=detection)
                    snapshot.image.save(file_name, content, save=True)
                    
                    snapshot.video_timestamp = video_time_delta
                    snapshot.save()

                # Create Alert (limit to 1 per video or 1 per major event to avoid spam? 
                # Let's do 1 per detection for now as requested)
                Alert.objects.create(
                    user=video_instance.user,
                    video=video_instance,
                    message=f"Motion detected at {timedelta(seconds=current_time)}",
                    severity='High',
                    is_read=False
                )

        video_instance.status = 'Processed'
        video_instance.save()
        
    except Exception as e:
        print(f"Error processing video: {e}")
        video_instance.status = 'Error'
        video_instance.save()
    finally:
        cap.release()
