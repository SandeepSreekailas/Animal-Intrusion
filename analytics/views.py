import csv
import json
import io
from datetime import timedelta
from django.shortcuts import render
from django.utils import timezone
from django.http import HttpResponse
from django.db.models import Count
from django.db.models.functions import TruncDate, TruncHour, TruncWeek, TruncMonth
from django.contrib.auth.decorators import login_required
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

from videos.models import Video
from detection.models import Detection
from alerts.models import Alert
from farmland.models import Farmland

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
        'animal_data_json': json.dumps(animal_data),
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
