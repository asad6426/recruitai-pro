from django.db.models import Avg
from django.shortcuts import render

from organizations.models import Organization
from resumes.models import ResumeAnalysis


def index(request):
    avg_accuracy = ResumeAnalysis.objects.aggregate(avg=Avg("overall_match_pct"))["avg"]
    context = {
        "resumes_analyzed": ResumeAnalysis.objects.count(),
        "enterprise_clients": Organization.objects.count(),
        "avg_accuracy": round(avg_accuracy, 1) if avg_accuracy else 0,
    }
    return render(request, "marketing/index.html", context)
