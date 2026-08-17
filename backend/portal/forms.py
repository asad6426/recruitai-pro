from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from applications.models import Interview
from jobs.models import Job

User = get_user_model()


class SignupForm(forms.Form):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField()
    company = forms.CharField(max_length=150, required=False)
    password = forms.CharField(widget=forms.PasswordInput, min_length=8)
    terms = forms.BooleanField()

    def clean_email(self):
        email = self.cleaned_data["email"].lower().strip()
        if User.objects.filter(email=email).exists():
            raise ValidationError("An account with this email already exists.")
        return email

    def clean_password(self):
        password = self.cleaned_data["password"]
        validate_password(password)
        return password

    def save(self):
        email = self.cleaned_data["email"]
        base_username = email.split("@")[0]
        username = base_username
        suffix = 1
        while User.objects.filter(username=username).exists():
            suffix += 1
            username = f"{base_username}{suffix}"
        user = User(
            username=username,
            email=email,
            first_name=self.cleaned_data["first_name"],
            last_name=self.cleaned_data["last_name"],
        )
        user.set_password(self.cleaned_data["password"])
        user.save()
        return user


class NoteForm(forms.Form):
    body = forms.CharField(widget=forms.Textarea, min_length=1)


class InterviewForm(forms.Form):
    scheduled_at = forms.DateTimeField()
    mode = forms.ChoiceField(choices=Interview.Mode.choices)


class ApplyForm(forms.Form):
    resume_id = forms.IntegerField()
    note = forms.CharField(widget=forms.Textarea, required=False)
    consent = forms.BooleanField()


class ResumeUploadForm(forms.Form):
    file = forms.FileField()
    filename = forms.CharField(max_length=255, required=False)


class JobForm(forms.Form):
    """Field names mirror post-job.html's input ids so the template can be
    hand-authored 1:1 with the prototype rather than auto-rendered."""

    jobTitle = forms.CharField(max_length=150)
    jobDept = forms.ChoiceField(choices=Job.Department.choices)
    jobType = forms.ChoiceField(choices=Job.EmploymentType.choices)
    jobLocation = forms.CharField(max_length=120)
    jobWorkplace = forms.ChoiceField(choices=Job.Workplace.choices)
    salaryMin = forms.IntegerField(min_value=0)
    salaryMax = forms.IntegerField(min_value=0)
    jobSummary = forms.CharField(widget=forms.Textarea, required=False)
    jobRequirements = forms.CharField(widget=forms.Textarea, required=False)
    jobResponsibilities = forms.CharField(widget=forms.Textarea, required=False)
    jobBenefits = forms.CharField(widget=forms.Textarea, required=False)
    jobSkills = forms.CharField(required=False)
    teamName = forms.CharField(max_length=100, required=False)
    teamSize = forms.IntegerField(required=False, min_value=0)
    minExperience = forms.ChoiceField(
        choices=[("0", "Any level"), ("2", "2+ years"), ("5", "5+ years"), ("8", "8+ years")],
        required=False,
    )
    atsThreshold = forms.ChoiceField(
        choices=[("off", "Off"), ("70", "70%"), ("80", "80%"), ("90", "90%")], required=False
    )
    anonScreen = forms.BooleanField(required=False)
    autoReject = forms.BooleanField(required=False)
    hiringManager = forms.IntegerField(required=False)
    closeDate = forms.DateField(required=False)
    chCareers = forms.BooleanField(required=False)
    chLinkedin = forms.BooleanField(required=False)
    chBoard = forms.BooleanField(required=False)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("salaryMin") and cleaned.get("salaryMax") and cleaned["salaryMin"] > cleaned["salaryMax"]:
            raise ValidationError("Salary minimum can't exceed salary maximum.")
        return cleaned
