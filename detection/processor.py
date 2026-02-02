import cv2
import numpy as np
import traceback
from datetime import timedelta
from collections import deque, Counter
from django.core.files.base import ContentFile
from django.conf import settings
from alerts.models import Alert
from alerts.utils import send_alert_email
from videos.models import Video
from detection.models import Detection, DetectionSnapshot

# Safe Import
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    print(f"CRITICAL: ULTRALYTICS IMPORT ERROR: {traceback.format_exc()}")
    YOLO = None
    YOLO_AVAILABLE = False

# === CONFIGURATION ===
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
CONF_THRESHOLD = 0.10  # Reduced to 0.10 to ensure we catch faint leopard signals
FRAME_SKIP = 2
DEDUP_WINDOW = 15.0
MIN_BOX_AREA_RATIO = 0.015
STABLE_FRAMES_REQUIRED = 3
CLASS_VOTE_WINDOW = 7
CLASS_VOTE_MIN_AGREE = 4

# PER-CLASS CONFIDENCE THRESHOLDS
CLASS_CONF_THRESHOLDS = {
    14: 0.60, # Bird: VERY HIGH threshold. Ignore faint bird signals.
    15: 0.10, # Cat (Tiger/Leopard): MINIMUM threshold. If it hints at being a cat, believe it.
    17: 0.15, # Horse (Lion): Low threshold to catch Lions
    20: 0.10, # Elephant: MINIMUM threshold
    21: 0.10, # Bear: MINIMUM threshold
    22: 0.15, # Zebra (Tiger): Low threshold to catch Tigers
}

# COCO Dataset Class IDs for Animals
TARGET_CLASSES = [14, 15, 16, 17, 18, 19, 20, 21, 22, 23]

# COMPREHENSIVE COCO CLASS MAPPING
CLASS_NAMES = {
    14: 'Bird',
    15: 'Cat',
    44: 'Dog',
    16: 'Dog',
    17: 'Horse',
    18: 'Sheep',
    19: 'Cow',
    20: 'Elephant',
    21: 'Bear',
    22: 'Zebra',
    23: 'Giraffe',
}

# ALIASING
ANIMAL_ALIASES = {
    14: 'Bird',
    15: 'Big Cat (Tiger/Leopard)',
    16: 'Wild Dog/Wolf',
    17: 'Lion (Suspected)', # Model often sees Lion as Horse
    18: 'Wild Boar (Suspected)', # Model often sees Wild Boar as Sheep
    19: 'Bull/Cow',
    20: 'Elephant',
    21: 'Wild Boar',
    22: 'Tiger (Suspected)', # Model often sees Tiger as Zebra
    23: 'Giraffe',
}

# SEVERITY MAPPING
SEVERITY_MAP = {
    14: 'Medium',
    15: 'Critical',
    16: 'High',
    17: 'Critical', # Horse -> Lion = Critical
    18: 'Critical', # Sheep -> Wild Boar = Critical
    19: 'Medium',
    20: 'Critical',
    21: 'Critical',
    22: 'Critical', # Zebra -> Tiger = Critical
    23: 'Medium',
}

def get_animal_name(cls_id):
    """Get the display name for an animal class, applying aliases if needed."""
    if cls_id in ANIMAL_ALIASES:
        return ANIMAL_ALIASES[cls_id]
    if cls_id in CLASS_NAMES:
        return CLASS_NAMES[cls_id]
    return f"Animal (Class {cls_id})"


class VideoProcessor:
    def __init__(self, video_instance):
        self.video = video_instance
        self.video_path = video_instance.video_file.path
        
        # IMPROVED TRACKING
        self.track_info = {}
        self.class_last_seen = {}
        self.recent_detections = []
        
        self.total_detections = 0
        self.total_frames_processed = 0
        self.unique_animals_seen = set()
        
        # Initialize YOLO11m (Medium) for Accuracy
        self.model = None
        if YOLO:
            print(f"[VideoProcessor] Loading YOLO11m model for video {self.video.id}...")
            try:
                self.model = YOLO("yolo11m.pt")
                print(f"[VideoProcessor] ✓ YOLO11m model loaded successfully")
            except Exception as e:
                print(f"[VideoProcessor] ✗ CRITICAL: Failed to load YOLO model: {e}")
                traceback.print_exc()
        else:
            print("[VideoProcessor] ✗ CRITICAL: Ultralytics YOLO not available")

    def process(self):
        """Main processing loop for video detection."""
        print(f"[VideoProcessor] Starting processing for video {self.video.id}")
        cap = cv2.VideoCapture(self.video_path)
        
        if not cap.isOpened():
            print(f"[VideoProcessor] ✗ Failed to open video file: {self.video_path}")
            self.video.status = 'Error'
            self.video.save()
            return

        self.video.status = 'Processing'
        self.video.save()

        try:
            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            print(f"[VideoProcessor] Video info: {total_frames} frames @ {fps:.2f} FPS")
            
            frame_idx = 0
            processed_frame_count = 0
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                frame_idx += 1
                
                # Process every Nth frame
                if frame_idx % FRAME_SKIP != 0:
                    continue
                
                processed_frame_count += 1
                current_timestamp = frame_idx / fps
                
                # Resize for consistent inference speed
                frame_resized = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
                
                # Run inference with tracking
                if self.model:
                    try:
                        # Use track() with persist=True to maintain IDs across frames
                        results = self.model.track(
                            frame_resized,
                            persist=True,
                            conf=CONF_THRESHOLD,
                            classes=TARGET_CLASSES,
                            verbose=False,
                            imgsz=640,
                            iou=0.5,
                            tracker="botsort.yaml",
                        )
                        
                        # Process results
                        if results and len(results) > 0:
                            for r in results:
                                if r.boxes is not None and r.boxes.id is not None:
                                    boxes = r.boxes.xyxy.cpu().numpy()
                                    ids = r.boxes.id.cpu().numpy().astype(int)
                                    classes = r.boxes.cls.cpu().numpy().astype(int)
                                    confidences = r.boxes.conf.cpu().numpy()
                                    
                                    for box, track_id, cls_id, conf in zip(boxes, ids, classes, confidences):
                                        # 1. PER-CLASS CONFIDENCE FILTER
                                        required_conf = CLASS_CONF_THRESHOLDS.get(cls_id, 0.25)
                                        if conf < required_conf:
                                            continue

                                        # 2. SIZE-BASED MISCLASSIFICATION FILTER (BIRD-STOPPER)
                                        # Calculate box area ratio
                                        x1, y1, x2, y2 = map(float, box)
                                        width = x2 - x1
                                        height = y2 - y1
                                        area_ratio = (width * height) / (FRAME_WIDTH * FRAME_HEIGHT)
                                        
                                        # Rule: If it's a "Bird" but HUGE (>3% of screen), it's probably a Leopard/Tree
                                        # Real surveillance birds are tiny dots.
                                        if cls_id == 14 and area_ratio > 0.03:
                                            # print(f"DEBUG: Ignored LARGE BIRD (Area: {area_ratio:.3f}) - Likely Misclassification")
                                            continue

                                        self.handle_detection(
                                            frame_resized, int(track_id), int(cls_id), 
                                            float(conf), box, current_timestamp
                                        )
                    
                    except Exception as e:
                        print(f"[VideoProcessor] Error during inference at frame {frame_idx}: {e}")
                        traceback.print_exc()
                        continue

            self.total_frames_processed = processed_frame_count
            print(f"[VideoProcessor] Processing complete:")
            print(f"  - Frames processed: {processed_frame_count}/{total_frames}")
            print(f"  - Total detections: {self.total_detections}")
            print(f"  - Unique animals: {len(self.unique_animals_seen)}")
            
            self.video.status = 'Processed'
            self.video.save()
            
            # Create completion alert
            Alert.objects.create(
                user=self.video.user,
                video=self.video,
                severity="Info",
                message=f"Video processing complete: {self.total_detections} detections, {len(self.unique_animals_seen)} unique animals"
            )

        except Exception as e:
            print(f"[VideoProcessor] ✗ CRITICAL ERROR: {e}")
            traceback.print_exc()
            self.video.status = 'Error'
            self.video.save()
        finally:
            cap.release()
            print(f"[VideoProcessor] Video capture released")

    def handle_detection(self, frame, track_id, cls_id, conf, box, timestamp):
        """
        Handle a detected animal with improved tracking to maintain consistent identity.
        
        Key improvements:
        1. Wait for stable classification (multiple frames) before creating detection
        2. Use class smoothing to prevent Cow->Horse->Boar misclassifications
        3. Strong deduplication to prevent same animal being detected multiple times
        """

        # ----- PER-TRACK CLASS SMOOTHING -----
        # Ensure track_info entry exists early so we can accumulate class statistics
        track_data = self.track_info.get(track_id)
        if track_data is None:
            track_data = {
                "animal_name": None,
                "class_id": None,
                "first_seen": timestamp,
                "last_seen": timestamp,
                "last_detection_time": None,
                "detection_id": None,
                "frame_count": 0,  # How many frames we've seen this track
                "class_conf": {},          # {cls_id: total_conf}
                "stable_class_id": None,   # smoothed / canonical class id
                "cls_history": deque(maxlen=CLASS_VOTE_WINDOW),  # rolling window of class ids
            }
            self.track_info[track_id] = track_data

        # Update tracking info
        track_data['last_seen'] = timestamp
        track_data['frame_count'] = track_data.get('frame_count', 0) + 1

        # Update per-class confidence history
        class_conf = track_data.setdefault("class_conf", {})
        class_conf[cls_id] = class_conf.get(cls_id, 0.0) + float(conf)

        # Decide / update a stable class id for this track
        stable_class_id = track_data.get("stable_class_id")
        frame_count = track_data.get('frame_count', 0)

        # Compute box area ratio (helps avoid partial-animal early misclassification)
        x1, y1, x2, y2 = map(float, box)
        box_w = max(0.0, x2 - x1)
        box_h = max(0.0, y2 - y1)
        box_area_ratio = (box_w * box_h) / float(FRAME_WIDTH * FRAME_HEIGHT)

        # Track when the animal is sufficiently visible
        if box_area_ratio >= MIN_BOX_AREA_RATIO:
            track_data["large_box_frames"] = track_data.get("large_box_frames", 0) + 1
        else:
            track_data["large_box_frames"] = track_data.get("large_box_frames", 0)

        # ----- CLASS LOCKING (majority voting) -----
        # In crowded scenes / partial views, per-frame cls_id can oscillate.
        # We lock the class once we have enough agreement across recent frames.
        track_data["cls_history"].append(int(cls_id))
        if stable_class_id is None:
            if (
                frame_count >= STABLE_FRAMES_REQUIRED
                and track_data.get("large_box_frames", 0) >= 2
                and len(track_data["cls_history"]) >= STABLE_FRAMES_REQUIRED
            ):
                counts = Counter(track_data["cls_history"])
                voted_cls, voted_count = counts.most_common(1)[0]
                if voted_count >= CLASS_VOTE_MIN_AGREE:
                    stable_class_id = voted_cls
                    track_data["stable_class_id"] = stable_class_id
                    track_data["class_id"] = stable_class_id

        # Still not stable: do not create detections yet (prevents wrong labels early)
        if stable_class_id is None:
            return

        # Use the STABLE class id for naming & dedup
        canonical_cls_id = track_data["stable_class_id"]
        if canonical_cls_id is None:
            return  # Still waiting for stable classification
        
        animal_name = get_animal_name(canonical_cls_id)
        severity = SEVERITY_MAP.get(canonical_cls_id, "Medium")
        
        # Update track data with stable class
        track_data['animal_name'] = animal_name
        track_data['class_id'] = canonical_cls_id
        
        # If the animal is still too small/partial, do not commit detections yet
        if box_area_ratio < MIN_BOX_AREA_RATIO:
            return

        # NOTE: we DO NOT class-dedup here anymore, because if multiple animals of the same
        # type appear together, class-dedup would wrongly suppress them. We dedup per track only.
        
        # Check if this specific track already created a detection recently
        last_det_time = track_data.get('last_detection_time')
        if last_det_time is not None:
            time_since_last = timestamp - last_det_time
            if time_since_last < DEDUP_WINDOW:
                # Same track seen recently, skip
                return
        
        # This is a NEW detection (either new track or track returned after DEDUP_WINDOW)
        
        # Only create detection if this is the first time for this track OR enough time passed
        should_create_detection = (
            track_data.get('detection_id') is None or  # First detection for this track
            (last_det_time is not None and (timestamp - last_det_time) >= DEDUP_WINDOW)
        )
        
        if not should_create_detection:
            return
        
        try:
            # If we already have a detection for this track and the model's stable class improved,
            # update the existing record instead of creating a new one.
            existing_detection_id = track_data.get("detection_id")
            if existing_detection_id is not None:
                try:
                    existing_det = Detection.objects.get(id=existing_detection_id)
                    # Upgrade logic: if we locked to Wild Boar, update name/severity/confidence
                    if existing_det.animal_type != animal_name:
                        existing_det.animal_type = animal_name
                        existing_det.severity = severity
                        existing_det.confidence = round(float(conf), 3)
                        existing_det.save(update_fields=["animal_type", "severity", "confidence"])
                    # Update last_detection_time and return (no new row)
                    track_data["last_detection_time"] = timestamp
                    return
                except Detection.DoesNotExist:
                    # fall through to create new detection
                    track_data["detection_id"] = None

            # Create Detection record (first commit for this track)
            detection = Detection.objects.create(
                video=self.video,
                animal_type=animal_name,
                confidence=round(float(conf), 3),
                severity=severity,
                video_timestamp=timedelta(seconds=timestamp)
            )
            self.total_detections += 1
            
            # Store detection ID and time in track info
            is_first_detection = track_data.get('detection_id') is None
            track_data['detection_id'] = detection.id
            track_data['last_detection_time'] = timestamp
            
            # Add to unique animals set
            self.unique_animals_seen.add(animal_name)
            
            # Create live recognition alert ONLY for the first detection of this track
            if is_first_detection:
                live_message = f"{animal_name} detected at {timestamp:.1f}s"
                print(f"✅ LIVE RECOGNITION: {live_message} (Track ID: {track_id}, Stable after {frame_count} frames)")
                
                Alert.objects.create(
                    user=self.video.user,
                    video=self.video,
                    message=live_message,
                    severity=severity,
                    is_read=False
                )
            
            # Create snapshot with bounding box
            frame_copy = frame.copy()
            x1, y1, x2, y2 = map(int, box)
            
            # Draw bounding box
            color = (0, 255, 0) if severity == 'Medium' else (0, 165, 255) if severity == 'High' else (0, 0, 255)
            thickness = 2
            cv2.rectangle(frame_copy, (x1, y1), (x2, y2), color, thickness)
            
            # Draw label with track ID
            label = f"{animal_name} ID:{track_id} ({conf:.2f})"
            label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            label_y = max(y1 - 10, label_size[1] + 10)
            cv2.rectangle(frame_copy, (x1, label_y - label_size[1] - 5), 
                         (x1 + label_size[0], label_y + 5), color, -1)
            cv2.putText(frame_copy, label, (x1, label_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            # Encode and save snapshot
            ret, buf = cv2.imencode('.jpg', frame_copy, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if ret:
                snapshot = DetectionSnapshot(
                    detection=detection,
                    video_timestamp=timedelta(seconds=timestamp)
                )
                filename = f"det_{detection.id}_track{track_id}_{int(timestamp)}.jpg"
                snapshot.image.save(filename, ContentFile(buf.tobytes()), save=True)
            
            # Create alert for high-severity animals
            if severity in ['High', 'Critical']:
                msg = f"{severity} Alert: {animal_name} detected at {timestamp:.1f}s (Confidence: {conf:.2f})"
                Alert.objects.create(
                    user=self.video.user,
                    video=self.video,
                    message=msg,
                    severity=severity
                )
                
                # Try to send email alert
                try:
                    send_alert_email(
                        self.video.user,
                        f"🚨 Intrusion Alert: {animal_name}",
                        msg
                    )
                except Exception as e:
                    print(f"[Detection] Failed to send email alert: {e}")
        
        except Exception as e:
            print(f"[Detection] ✗ Error saving detection: {e}")
            traceback.print_exc()
