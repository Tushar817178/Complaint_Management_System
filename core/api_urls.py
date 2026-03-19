from django.urls import path
from .api_views import (
    CategoryListAPIView,
    ComplaintDetailAPIView,
    ComplaintListCreateAPIView,
    NotificationListAPIView,
    StatusListAPIView,
)

urlpatterns = [
    path("complaints/", ComplaintListCreateAPIView.as_view(), name="api_complaints"),
    path(
        "complaints/<int:pk>/",
        ComplaintDetailAPIView.as_view(),
        name="api_complaint_detail",
    ),
    path("categories/", CategoryListAPIView.as_view(), name="api_categories"),
    path("statuses/", StatusListAPIView.as_view(), name="api_statuses"),
    path("notifications/", NotificationListAPIView.as_view(), name="api_notifications"),
]
