from django.contrib import admin

from .models import Application, Interview, Note

admin.site.register(Application)
admin.site.register(Note)
admin.site.register(Interview)
