from django.urls import path
from . import views

urlpatterns = [
    path('', views.farmland_list, name='farmland-list'),
    path('create/', views.farmland_create, name='farmland-create'),
    path('<int:pk>/update/', views.farmland_update, name='farmland-update'),
    path('<int:pk>/delete/', views.farmland_delete, name='farmland-delete'),
]
