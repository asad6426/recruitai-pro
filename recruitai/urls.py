from django.urls import path

from portal import views


urlpatterns = [
    path("", views.index, name="home"),
    path("accounts/login/", views.login, name="login"),
    path("logout/", views.logout, name="logout"),
    path("role/", views.role, name="role"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("applicant/", views.applicant, name="applicant"),
    path("jobs/", views.jobs, name="jobs"),
    path("post-job/", views.job_post, name="job_post"),
    path("interviews/", views.interviews, name="interviews"),
    path("analytics/", views.analytics, name="analytics"),
    path("notifications/", views.notifications, name="notifications"),
    path("settings/", views.settings, name="settings"),
    path("candidates/", views.candidates, name="candidates"),
    path("resume-analysis/", views.analysis, name="analysis"),
    path("candidate-profile/", views.profile, name="profile"),
]
