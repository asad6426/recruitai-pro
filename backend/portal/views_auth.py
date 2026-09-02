from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from accounts.models import ApplicantProfile, RecruiterProfile
from organizations.models import Organization

from .forms import SignupForm

User = get_user_model()


def signup(request):
    if request.user.is_authenticated:
        return redirect("login_redirect")

    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            request.session["signup_company"] = form.cleaned_data.get("company", "")
            messages.success(request, "Account created. Let's personalise your workspace.")
            return redirect("role_select")
    else:
        form = SignupForm()

    return render(request, "auth/signup.html", {"form": form})


@login_required
def role_select(request):
    if request.user.role:
        return redirect("login_redirect")

    if request.method == "POST":
        role = request.POST.get("role")
        if role not in (User.Role.RECRUITER, User.Role.APPLICANT):
            messages.error(request, "Choose one of the two options to continue.")
            return render(request, "auth/role_select.html")

        user = request.user
        if role == User.Role.RECRUITER:
            company_name = request.session.pop("signup_company", "") or f"{user.get_full_name()}'s Company"
            org, _ = Organization.objects.get_or_create(name=company_name)
            RecruiterProfile.objects.get_or_create(user=user, defaults={"organization": org})
        else:
            ApplicantProfile.objects.get_or_create(user=user)

        user.role = role
        user.save(update_fields=["role"])
        messages.success(request, "Welcome! Your workspace is ready.")
        return redirect("login_redirect")

    return render(request, "auth/role_select.html")


@login_required
def login_redirect(request):
    """LOGIN_REDIRECT_URL target — routes a freshly logged-in user by role."""
    if not request.user.role:
        return redirect("role_select")
    if request.user.role == User.Role.RECRUITER:
        return redirect("recruiter_dashboard")
    return redirect("applicant_dashboard")
