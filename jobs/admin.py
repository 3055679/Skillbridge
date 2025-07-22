from django.contrib import admin
from .models import Job, Application, Interview
from accounts.models import StudentProfile, EmployerProfile

class JobAdmin(admin.ModelAdmin):
    list_display = ('title', 'employer', 'job_type', 'location', 'posted_date', 'is_active')
    list_filter = ('job_type', 'is_active', 'posted_date')
    search_fields = ('title', 'employer__company_name')
    list_editable = ('is_active',)

class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('student', 'job', 'status', 'applied_date')
    list_filter = ('status', 'applied_date')
    search_fields = ('student__user__username', 'job__title')
    list_editable = ('status',)

class InterviewAdmin(admin.ModelAdmin):
    list_display = ('application', 'interview_date', 'interview_type')
    list_filter = ('interview_type', 'interview_date')
    search_fields = ('application__student__user__username', 'application__job__title')

admin.site.register(Job, JobAdmin)
admin.site.register(Application, ApplicationAdmin)
admin.site.register(Interview, InterviewAdmin)