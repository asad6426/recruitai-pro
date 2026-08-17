from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views_applicant, views_auth, views_marketing, views_recruiter

urlpatterns = [
    path("", views_marketing.index, name="index"),
    # --- auth ---------------------------------------------------------
    path("signup/", views_auth.signup, name="signup"),
    path("role-select/", views_auth.role_select, name="role_select"),
    path("dashboard/", views_auth.login_redirect, name="login_redirect"),
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="auth/login.html", redirect_authenticated_user=True),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="auth/forgot_password.html",
            email_template_name="auth/password_reset_email.txt",
            success_url=reverse_lazy("password_reset_done"),
        ),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(template_name="auth/password_reset_done.html"),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="auth/password_reset_confirm.html", success_url=reverse_lazy("password_reset_complete")
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(template_name="auth/password_reset_complete.html"),
        name="password_reset_complete",
    ),
    # --- recruiter ------------------------------------------------------
    path("recruiter/", views_recruiter.dashboard, name="recruiter_dashboard"),
    path("recruiter/candidates/", views_recruiter.candidate_list, name="recruiter_candidates"),
    path(
        "recruiter/candidates/<int:application_id>/",
        views_recruiter.candidate_profile,
        name="recruiter_candidate_profile",
    ),
    path(
        "recruiter/candidates/<int:application_id>/resume-analysis/",
        views_recruiter.resume_analysis,
        name="recruiter_resume_analysis",
    ),
    path(
        "recruiter/candidates/<int:application_id>/stage/",
        views_recruiter.application_stage_update,
        name="recruiter_application_stage",
    ),
    path(
        "recruiter/candidates/<int:application_id>/interview/",
        views_recruiter.interview_schedule,
        name="recruiter_interview_schedule",
    ),
    path(
        "recruiter/suggestions/<int:suggestion_id>/toggle/",
        views_recruiter.suggestion_toggle,
        name="recruiter_suggestion_toggle",
    ),
    path("recruiter/jobs/", views_recruiter.jobs_list, name="recruiter_jobs"),
    path("recruiter/jobs/new/", views_recruiter.post_job, name="recruiter_post_job"),
    path("recruiter/jobs/<int:job_id>/edit/", views_recruiter.post_job, name="recruiter_edit_job"),
    path("recruiter/jobs/<int:job_id>/status/", views_recruiter.job_status_update, name="recruiter_job_status"),
    path("recruiter/jobs/<int:job_id>/delete-draft/", views_recruiter.job_delete_draft, name="recruiter_job_delete"),
    # --- applicant --------------------------------------------------------
    path("applicant/", views_applicant.dashboard, name="applicant_dashboard"),
    path("applicant/jobs/", views_applicant.browse_jobs, name="applicant_browse_jobs"),
    path("applicant/jobs/<int:job_id>/", views_applicant.job_detail, name="applicant_job_detail"),
    path("applicant/jobs/<int:job_id>/apply/", views_applicant.apply, name="applicant_apply"),
    path("applicant/jobs/<int:job_id>/save/", views_applicant.saved_job_toggle, name="applicant_saved_job_toggle"),
    path("applicant/resumes/upload/", views_applicant.resume_upload, name="applicant_resume_upload"),
]
