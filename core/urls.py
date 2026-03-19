from django.urls import path
from . import views

urlpatterns = [
    path("", views.user_login, name="login"),
    path("register/", views.register, name="register"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("logout/", views.user_logout, name="logout"),
    path("create/", views.create_complaint, name="create_complaint"),
    path("my-complaints/", views.my_complaints, name="my_complaints"),
    path("complaints/<int:complaint_id>/", views.complaint_detail, name="complaint_detail"),
    path("complaints/<int:complaint_id>/pdf/", views.complaint_pdf, name="complaint_pdf"),
    path(
        "complaints/<int:complaint_id>/edit/",
        views.edit_complaint,
        name="edit_complaint",
    ),
    path(
        "complaints/<int:complaint_id>/withdraw/",
        views.withdraw_complaint,
        name="withdraw_complaint",
    ),
    path("panel/complaints/", views.admin_complaints, name="admin_complaints"),
    path("panel/users/", views.manage_users, name="admin_users"),
    path("panel/categories/", views.manage_categories, name="admin_categories"),
    path("panel/statuses/", views.manage_statuses, name="admin_statuses"),
    path("panel/audit-logs/", views.admin_audit_logs, name="admin_audit_logs"),
    path("notifications/", views.notifications, name="notifications"),
    path("track/", views.public_track, name="public_track"),
]
