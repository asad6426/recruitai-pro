from django.shortcuts import redirect, render


def user_role(request):
    return request.COOKIES.get("role")


def require_hr(request):
    return user_role(request) in {"recruiter", "admin"}


def screen(name, page="dashboard", **extra):
    data = {"initial_screen": name, "page": page}
    data.update(extra)
    return data


def index(request):
    return render(request, "portal/index.html", screen("landing"))


def login(request):
    if request.method == "POST":
        email = request.POST.get("username", "").strip().lower()
        if email == "admin@recruitai.com":
            response = redirect("admin_dashboard")
            response.set_cookie("role", "admin")
            return response
        if email == "alex@company.com":
            response = redirect("applicant")
            response.set_cookie("role", "applicant")
            return response
        response = redirect("dashboard")
        response.set_cookie("role", "recruiter")
        return response
    return render(request, "portal/index.html", screen("login"))


def logout(request):
    response = redirect("login")
    response.delete_cookie("role")
    return response


def role(request):
    return render(request, "portal/index.html", screen("role"))


def dashboard(request):
    if user_role(request) == "applicant":
        return redirect("applicant")
    return render(request, "portal/index.html", screen("app", "dashboard"))


def admin_dashboard(request):
    if user_role(request) != "admin":
        return redirect("dashboard")
    return render(request, "portal/index.html", screen("app", "admin"))


def applicant(request):
    if user_role(request) in {"recruiter", "admin"}:
        return redirect("dashboard")
    return render(request, "portal/index.html", screen("app", "applicant"))


def jobs(request):
    return render(request, "portal/index.html", screen("app", "jobs"))


def job_post(request):
    if not require_hr(request):
        return redirect("applicant")
    posted_job = None
    if request.method == "POST":
        posted_job = {
            "title": request.POST.get("title", "").strip(),
            "company": request.POST.get("company", "").strip(),
            "location": request.POST.get("location", "").strip(),
            "job_type": request.POST.get("job_type", "").strip(),
            "salary": request.POST.get("salary", "").strip(),
            "experience": request.POST.get("experience", "").strip(),
            "skills": request.POST.get("skills", "").strip(),
            "description": request.POST.get("description", "").strip(),
        }
    return render(request, "portal/index.html", screen("app", "job_post", posted_job=posted_job))


def interviews(request):
    if not require_hr(request):
        return redirect("applicant")
    return render(request, "portal/index.html", screen("app", "interviews"))


def analytics(request):
    if not require_hr(request):
        return redirect("applicant")
    return render(request, "portal/index.html", screen("app", "analytics"))


def notifications(request):
    if not require_hr(request):
        return redirect("applicant")
    return render(request, "portal/index.html", screen("app", "notifications"))


def settings(request):
    if not require_hr(request):
        return redirect("applicant")
    return render(request, "portal/index.html", screen("app", "settings"))


def candidates(request):
    if not require_hr(request):
        return redirect("applicant")
    return render(request, "portal/index.html", screen("app", "candidates"))


def analysis(request):
    if not require_hr(request):
        return redirect("applicant")
    return render(request, "portal/index.html", screen("app", "analysis"))


def profile(request):
    if not require_hr(request):
        return redirect("applicant")
    return render(request, "portal/index.html", screen("app", "profile"))
