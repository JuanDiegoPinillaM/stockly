from django.urls import path

from . import analytics, views

urlpatterns = [
    path('health/', views.health, name='health'),
    path('analytics/overview/', analytics.overview, name='analytics-overview'),
    path('analytics/export/', analytics.export, name='analytics-export'),
]
