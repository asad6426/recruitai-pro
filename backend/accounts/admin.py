from django.contrib import admin

from .models import ApplicantProfile, RecruiterGoal, RecruiterProfile, User

admin.site.register(User)
admin.site.register(RecruiterProfile)
admin.site.register(ApplicantProfile)
admin.site.register(RecruiterGoal)
