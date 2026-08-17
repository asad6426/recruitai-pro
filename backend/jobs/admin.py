from django.contrib import admin

from .models import Job, JobBenefit, JobRequirement, JobResponsibility, JobSkill, SavedJob

admin.site.register(Job)
admin.site.register(JobSkill)
admin.site.register(JobRequirement)
admin.site.register(JobResponsibility)
admin.site.register(JobBenefit)
admin.site.register(SavedJob)
