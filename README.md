#  AI-Based Animal Intrusion Detection System

A web-based AI system that detects animal intrusions in farmland using computer vision and object detection models.

Built with **Django + OpenCV + YOLO**, this system allows farmers to upload video footage, automatically detect animal movement, and receive structured intrusion reports.

---

##  Features

###  User Management

* Secure user registration & login
* Role-based access
* User-specific dashboards
* Isolated data per user

###  Farmland Management

* Add and manage farmlands
* Interactive map integration (Leaflet + OpenStreetMap)
* Store latitude & longitude

###  Video Management

* Upload video files (MP4, AVI, MOV, MKV)
* Metadata extraction (duration, FPS, resolution)
* Processing status tracking

###  AI Processing Engine

* Motion detection (OpenCV)
* Vegetation filtering
* Contour merging
* Object persistence tracking
* YOLO-based animal verification
* Severity classification (Low / Medium / Critical)

###  Dashboard & Analytics

* Total videos processed
* Detection statistics
* Severity distribution charts
* Farmland-wise intrusion comparison
* Time-based detection graphs

###  Reports

* CSV export
* PDF summary report
* Snapshot gallery with video timestamps

---

##  Tech Stack

* **Backend:** Django 4.x
* **Computer Vision:** OpenCV
* **Object Detection:** YOLO (Ultralytics)
* **Frontend:** Bootstrap 5
* **Maps:** Leaflet.js + OpenStreetMap
* **Database:** SQLite (dev) / MySQL or PostgreSQL (prod)

---

##  Project Structure

```
animal_intrusion/
│
├── accounts/
├── farmland/
├── videos/
├── detection/
├── alerts/
│
├── processor/
│   ├── motion_detector.py
│   ├── contour_merger.py
│   ├── yolo_verifier.py
│   └── video_processor.py
│
├── templates/
├── static/
├── media/
└── manage.py
```

---

##  Installation

### 1️⃣ Clone the repository

```bash
git clone https://github.com/yourusername/animal-intrusion-detection.git
cd animal-intrusion-detection
```

### 2️⃣ Create virtual environment

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
```

### 3️⃣ Install dependencies

```bash
pip install -r requirements.txt
```

### 4️⃣ Apply migrations

```bash
python manage.py migrate
```

### 5️⃣ Run server

```bash
python manage.py runserver
```

Visit:

```
http://127.0.0.1:8000/
```

---

##  How It Works

1. User uploads video
2. OpenCV processes frames
3. Motion detection identifies candidate regions
4. Vegetation noise is filtered
5. Contours are merged into object candidates
6. YOLO verifies animal presence
7. Detections stored with:

   * Video timestamp
   * System timestamp
   * Severity level
8. Dashboard updates analytics automatically

---

##  Data Isolation

Each user can only access:

* Their own farmlands
* Their own videos
* Their own detections
* Their own analytics

All queries are filtered by `request.user`.

---

##  Severity Logic

* **Critical** → Large predator detected
* **High** → Large animal intrusion
* **Medium** → Small/Medium animal intrusion

Severity is determined by system logic, not the detection model.

---

##  Map Integration

Farmland locations are selected using:

* Leaflet.js
* OpenStreetMap
* Click-to-select latitude & longitude

---

##  Future Improvements

* Custom wildlife-trained YOLO model
* Real-time camera integration
* Intrusion heatmaps
* Multi-language support
* Mobile app integration

---

##  License

This project is for educational and research purposes.

---


