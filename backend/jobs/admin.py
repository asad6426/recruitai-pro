from django.contrib import admin

from .models import Job, JobBenefit, JobPayment, JobRequirement, JobResponsibility, JobSkill, SavedJob

admin.site.register(Job)
admin.site.register(JobSkill)
admin.site.register(JobRequirement)
admin.site.register(JobResponsibility)
admin.site.register(JobBenefit)
admin.site.register(SavedJob)


@admin.register(JobPayment)
class JobPaymentAdmin(admin.ModelAdmin):
    list_display = ("tran_id", "job", "amount", "currency", "status", "created_at")
    list_filter = ("status", "currency")
    search_fields = ("tran_id", "job__title", "val_id")
