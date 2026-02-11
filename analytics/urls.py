from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard_view, name='analytics-dashboard'),
    path('export/csv/', views.export_detections_csv, name='analytics-export-csv'),
    path('export/pdf/', views.export_report_pdf, name='analytics-export-pdf'),
    path('ai-query/', views.ai_query, name='ai-query'),
]
