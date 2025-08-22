from django.contrib import admin
from .models import RoleProfile, AssessmentBlueprint, Question, Task, Assessment, Response, Report

admin.site.register([RoleProfile, AssessmentBlueprint, Question, Task])

@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ("id","application","blueprint","status","duration_minutes")

@admin.register(Response)
class ResponseAdmin(admin.ModelAdmin):
    list_display = ("assessment","ref_type","ref_id","score","is_correct")

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("assessment","total_score")
