from django.contrib import admin

from .models import CandidateSkill, Certification, Education, WorkExperience

admin.site.register(WorkExperience)
admin.site.register(Education)
admin.site.register(CandidateSkill)
admin.site.register(Certification)
