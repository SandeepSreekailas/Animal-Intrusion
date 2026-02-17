import csv
import json
import io
from datetime import timedelta
from django.shortcuts import render
from django.utils import timezone
from django.http import HttpResponse
from django.db.models import Count
from django.db.models.functions import TruncDate, TruncHour, TruncWeek, TruncMonth, ExtractWeekDay, ExtractHour
from django.contrib.auth.decorators import login_required
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import random

from videos.models import Video
from detection.models import Detection
from alerts.models import Alert
from farmland.models import Farmland
from django.conf import settings

# IMPORT THE NEW LIBRARY
from google import genai
from google.genai import types
from google import genai

@login_required
def dashboard_view(request):
    # --- 1. Summary Cards ---
    total_videos = Video.objects.filter(user=request.user).count()
    total_detections = Detection.objects.filter(video__user=request.user).count()
    total_alerts = Alert.objects.filter(user=request.user).count()
    
    severity_counts = Detection.objects.filter(video__user=request.user).values('severity').annotate(count=Count('severity'))
    # Convert to dict for easier template access: {'High': 10, 'Medium': 5}
    severity_dict = {item['severity']: item['count'] for item in severity_counts}
    
    high_sev = severity_dict.get('High', 0) + severity_dict.get('Critical', 0)
    medium_sev = severity_dict.get('Medium', 0)
    low_sev = severity_dict.get('Low', 0)

    # --- 2. Graph: Detections Over Time (Dynamic Range) ---
    time_range = request.GET.get('range', 'day') # Default to 'day' (Daily view)
    
    dates = []
    date_counts = []
    
    if time_range == 'month':
        # Last 12 Months (Monthly Resolution)
        start_time = timezone.now() - timedelta(days=365)
        detections_by_date = Detection.objects.filter(video__user=request.user, created_at__gte=start_time)\
            .annotate(date=TruncMonth('created_at'))\
            .values('date')\
            .annotate(count=Count('id'))\
            .order_by('date')
            
        data_dict = {item['date'].strftime('%Y-%m'): item['count'] for item in detections_by_date}
        
        # Generate last 12 months
        current_date = timezone.now().date()
        for i in range(12):
            # Approximate month subtraction logic
            year = current_date.year
            month = current_date.month - i
            while month <= 0:
                month += 12
                year -= 1
            d_str = f"{year}-{month:02d}"
            dates.insert(0, d_str) # Prepend to reverse order
            date_counts.insert(0, data_dict.get(d_str, 0))
            
    elif time_range == 'week':
        # Last 12 Weeks (Weekly Resolution)
        start_time = timezone.now() - timedelta(weeks=12)
        detections_by_date = Detection.objects.filter(video__user=request.user, created_at__gte=start_time)\
            .annotate(date=TruncWeek('created_at'))\
            .values('date')\
            .annotate(count=Count('id'))\
            .order_by('date')
            
        data_dict = {item['date'].strftime('%Y-W%U'): item['count'] for item in detections_by_date}
        
        for i in range(12):
            d = (timezone.now() - timedelta(weeks=11-i)).date()
            # Find the Monday of that week
            d = d - timedelta(days=d.weekday())
            d_str = d.strftime('%Y-W%U')
            dates.append(d_str)
            date_counts.append(data_dict.get(d_str, 0))
            
    else: # time_range == 'day'
        # Last 30 Days (Daily Resolution)
        start_time = timezone.now() - timedelta(days=30)
        detections_by_date = Detection.objects.filter(video__user=request.user, created_at__gte=start_time)\
            .annotate(date=TruncDate('created_at'))\
            .values('date')\
            .annotate(count=Count('id'))\
            .order_by('date')
            
        data_dict = {item['date'].strftime('%Y-%m-%d'): item['count'] for item in detections_by_date}
        
        for i in range(30):
            d = (timezone.now() - timedelta(days=29-i)).date()
            d_str = d.strftime('%Y-%m-%d')
            dates.append(d_str)
            date_counts.append(data_dict.get(d_str, 0))

    # --- 3. Graph: Severity Distribution (Pie) ---
    # We use severity_dict from above
    sev_labels = list(severity_dict.keys())
    sev_data = list(severity_dict.values())

    # --- 4. Graph: Farmland-wise Intrusion (Bar) ---
    farmland_stats = Detection.objects.filter(video__user=request.user).values('video__farmland__name')\
        .annotate(count=Count('id'))\
        .order_by('-count')
    
    farm_labels = [item['video__farmland__name'] for item in farmland_stats]
    farm_data = [item['count'] for item in farmland_stats]

    # --- 5. Graph: Animal Type Distribution (Bar) ---
    animal_stats = Detection.objects.filter(video__user=request.user).values('animal_type')\
        .annotate(count=Count('id'))\
        .order_by('-count')
    
    animal_labels = [item['animal_type'] for item in animal_stats]
    animal_data = [item['count'] for item in animal_stats]

    # --- 6. ADVANCED AI: Heatmap Data (Weekday x Hour) ---
    # 1=Sun, 7=Sat
    heatmap_qs = Detection.objects.filter(video__user=request.user).annotate(
        weekday=ExtractWeekDay('created_at'),
        hour=ExtractHour('created_at')
    ).values('weekday', 'hour').annotate(count=Count('id'))

    # Format for ECharts: [[x, y, value], ...] -> [[hour, weekday, count]]
    # We map 1-7 (Sun-Sat) to 0-6 (Sun-Sat) for array indexing if needed, 
    # but ECharts usually takes category indices. Let's use 0-6 for Mon-Sun or Sun-Sat.
    # Let's align with: 0=Mon, 1=Tue... 6=Sun for standard charts
    # Django: 1=Sun, 2=Mon, ..., 7=Sat.
    # Mapping to 0=Sun, ..., 6=Sat
    heatmap_data = []
    for item in heatmap_qs:
        # User-friendly day index: 0=Sun, 1=Mon...
        day_idx = item['weekday'] - 1 
        hour_idx = item['hour']
        count = item['count']
        heatmap_data.append([hour_idx, day_idx, count])

    # --- 7. ADVANCED AI: Farm Safety Score & Trends ---
    # Trend: Last 7 days vs Previous 7 days
    seven_days_ago = timezone.now() - timedelta(days=7)
    fourteen_days_ago = timezone.now() - timedelta(days=14)
    
    current_week_count = Detection.objects.filter(video__user=request.user, created_at__gte=seven_days_ago).count()
    prev_week_count = Detection.objects.filter(video__user=request.user, created_at__gte=fourteen_days_ago, created_at__lt=seven_days_ago).count()
    
    if prev_week_count > 0:
        trend_pct = int(((current_week_count - prev_week_count) / prev_week_count) * 100)
    else:
        trend_pct = 100 if current_week_count > 0 else 0

    # Risk Score Algorithm (0-100, where 100 is Safe)
    # Start at 100. Deduct for recent severe detections.
    risk_deduction = 0
    recent_dets = Detection.objects.filter(video__user=request.user, created_at__gte=seven_days_ago)
    for d in recent_dets:
        if d.severity == 'Critical': risk_deduction += 10
        elif d.severity == 'High': risk_deduction += 5
        elif d.severity == 'Medium': risk_deduction += 2
        else: risk_deduction += 1
    
    safety_score = max(0, 100 - risk_deduction)
    risk_level = "Safe"
    if safety_score < 50: risk_level = "Critical"
    elif safety_score < 80: risk_level = "Caution"

    # --- 8. ADVANCED AI: Predictive Insights ---
    # Find the most frequent (Day, Hour) tuple
    prediction_text = "Analysis in progress... gathering data."
    if heatmap_data:
        # Find max count item
        best_slot = max(heatmap_qs, key=lambda x: x['count'])
        # Map back to string
        days_map = {1: 'Sunday', 2: 'Monday', 3: 'Tuesday', 4: 'Wednesday', 5: 'Thursday', 6: 'Friday', 7: 'Saturday'}
        p_day = days_map.get(best_slot['weekday'], 'Unknown')
        p_hour = best_slot['hour']
        prediction_text = f"High intrusion risk detected on <strong>{p_day}s around {p_hour}:00</strong> based on historical patterns."
    elif total_detections == 0:
        prediction_text = "System secure. No threats detected to establish a pattern."

    context = {
        'total_videos': total_videos,
        'total_detections': total_detections,
        'total_alerts': total_alerts,
        'high_sev': high_sev,
        'medium_sev': medium_sev,
        'low_sev': low_sev,
        
        # JSON data for JS
        'dates_json': json.dumps(dates),
        'date_counts_json': json.dumps(date_counts),
        'sev_labels_json': json.dumps(sev_labels),
        'sev_data_json': json.dumps(sev_data),
        'farm_labels_json': json.dumps(farm_labels),
        'farm_data_json': json.dumps(farm_data),
        'animal_labels_json': json.dumps(animal_labels),
        'animal_data_json': json.dumps(animal_data),
        
        # AI Data
        'heatmap_data_json': json.dumps(heatmap_data),
        'safety_score': safety_score,
        'risk_level': risk_level,
        'trend_pct': trend_pct,
        'trend_sign': '+' if trend_pct > 0 else '',
        'prediction_text': prediction_text,
        
        'time_range': time_range,
        'greeting': "Good Morning" if timezone.localtime(timezone.now()).hour < 12 else "Good Afternoon" if timezone.localtime(timezone.now()).hour < 18 else "Good Evening"
    }
    return render(request, 'analytics/dashboard.html', context)

@login_required
def export_detections_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="detections_export.csv"'

    writer = csv.writer(response)
    writer.writerow(['Timestamp', 'Animal Type', 'Severity', 'Confidence', 'Farmland', 'Video ID'])

    detections = Detection.objects.filter(video__user=request.user).select_related('video', 'video__farmland').order_by('-created_at')
    for det in detections:
        writer.writerow([
            det.created_at,
            det.animal_type,
            det.severity,
            det.confidence,
            det.video.farmland.name,
            det.video.id
        ])
    return response

@login_required
def export_report_pdf(request):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="analytics_report.pdf"'

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    
    styles = getSampleStyleSheet()
    title_style = styles['Title']
    h2_style = styles['Heading2']
    normal_style = styles['Normal']

    # Title
    elements.append(Paragraph("Animal Intrusion Analytics Report", title_style))
    elements.append(Spacer(1, 12))

    # Summary
    total_detections = Detection.objects.filter(video__user=request.user).count()
    elements.append(Paragraph(f"Total Detections Logged: {total_detections}", normal_style))
    elements.append(Paragraph(f"Report Generated: {timezone.now().strftime('%Y-%m-%d %H:%M')}", normal_style))
    elements.append(Spacer(1, 24))

    # Recent Detections Table
    elements.append(Paragraph("Recent Critical Detections", h2_style))
    elements.append(Spacer(1, 12))

    data = [['Time', 'Animal', 'Farmland', 'Severity']]
    recent_dets = Detection.objects.filter(video__user=request.user, severity__in=['High', 'Critical']).order_by('-created_at')[:10]
    
    for d in recent_dets:
        data.append([
            d.created_at.strftime('%Y-%m-%d %H:%M'),
            d.animal_type,
            d.video.farmland.name,
            d.severity
        ])

    if len(data) > 1:
        t = Table(data, colWidths=[120, 100, 100, 80])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(t)
    else:
        elements.append(Paragraph("No recent critical detections found.", normal_style))

    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    
    response.write(pdf)
    return response

@login_required
def reports_view(request):
    """
    Renders a page for viewing/downloading reports.
    """
    return render(request, 'analytics/reports.html')

@csrf_exempt
@require_POST
@login_required
def ai_query(request):
    """
    FINAL WORKING VERSION: Uses Gemini 2.5/2.0 Models
    """
    try:
        data = json.loads(request.body)
        query = data.get('query', '').lower().strip()
    except:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    user = request.user
    
    # --- Context Data ---
    today = timezone.localtime(timezone.now()).date()
    stats_today = Detection.objects.filter(video__user=user, created_at__date=today).count()
    latest = Detection.objects.filter(video__user=user).order_by('-created_at').first()
    
    latest_info = "None"
    if latest:
        minutes = int((timezone.now() - latest.created_at).total_seconds() / 60)
        latest_info = f"{latest.animal_type} ({latest.severity}) - {minutes}m ago"

    # --- AI CLIENT ---
    api_key = getattr(settings, 'GEMINI_API_KEY', None)
    response_text = "Neural net offline."

    if api_key:
        try:
            client = genai.Client(api_key=api_key)
            
            system_prompt = f"""
            You are F.R.I.D.A.Y., a secure farm AI.
            Status: User={user.username} | Intrusions Today={stats_today} | Last Alert={latest_info}.
            User Query: "{query}"
            Keep response short, professional, and helpful.
            """
            
            # THE CRITICAL FIX: Use the models YOU actually have
            candidate_models = [
                "gemini-2.5-flash",          # 🚀 The Newest/Fastest (You have this!)
                "gemini-2.0-flash",          # Reliable Backup
                "gemini-flash-latest",       # Generic Alias
                "gemini-2.5-flash-lite",     # Ultra-fast
            ]
            
            success = False
            for model_name in candidate_models:
                try:
                    # print(f"Trying model: {model_name}...")
                    response = client.models.generate_content(
                        model=model_name, 
                        contents=system_prompt
                    )
                    if response.text:
                        response_text = response.text
                        success = True
                        break # Success!
                except Exception as e:
                    # print(f"Model {model_name} failed: {e}")
                    continue 
            
            if not success:
                response_text = "Error: Could not access any Gemini 2.5/2.0 models."

        except Exception as e:
            response_text = f"Connection Error: {str(e)[:50]}"

    return JsonResponse({'response': response_text, 'user': user.username})