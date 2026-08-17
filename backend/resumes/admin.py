from django.contrib import admin

from .models import OptimizationSuggestion, Resume, ResumeAnalysis, ResumeSkillMatch

admin.site.register(Resume)
admin.site.register(ResumeAnalysis)
admin.site.register(ResumeSkillMatch)
admin.site.register(OptimizationSuggestion)
