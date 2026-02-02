from django.urls import path
from . import views

urlpatterns = [
    path('', views.alert_list, name='alert-list'),
    path('read/<int:pk>/', views.mark_alert_read, name='mark-alert-read'),
]
