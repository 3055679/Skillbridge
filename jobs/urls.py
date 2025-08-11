from django.urls import path
from . import views
from django.shortcuts import render, redirect

app_name = 'jobs'

urlpatterns = [
    path('dashboard/', views.student_dashboard, name='student_dashboard'),
    path('applications/', views.my_applications, name='my_applications'),
    path('job/<int:job_id>/apply/', views.apply_job, name='apply_job'),
    path('employer/dashboard/', views.employer_dashboard, name='employer_dashboard'),
    path('employer/post-job/', views.post_job, name='post_job'),
    path('employer/application/<int:application_id>/', views.manage_application, name='manage_application'),
    path('employer/interview/<int:application_id>/', views.schedule_interview, name='schedule_interview'),
    path('employer/interviews/', views.employer_interviews, name='employer_interviews'),
    path('job/<int:pk>/', views.job_detail, name='job_detail'),
    path('job/<int:pk>/status/', views.job_status_update, name='job_status_update'),
    path('job/<int:pk>/manage-max-applications/', views.manage_max_applications, name='manage_max_applications'),
    path('employer/bulk-manage/', views.bulk_manage_applications, name='bulk_manage_applications'),
    path('jobs/', views.job_list, name='job_list'),
    path('interview/<int:pk>/', views.interview_detail, name='interview_detail'),
    path('interview/reschedule/<int:pk>/', views.reschedule_interview, name='reschedule_interview'),
    path('interview/cancel/<int:pk>/', views.cancel_interview, name='cancel_interview'),
    path('interviews/', views.student_interviews, name='interviews'),
    path("resume-builder/", views.resume_builder, name="resume_builder"),
    path('saved-jobs/', lambda request: render(request, 'jobs/saved_jobs.html'), name='saved_jobs'),
    path('community/', lambda request: render(request, 'jobs/community.html'), name='community'),
    path('settings/', lambda request: render(request, 'jobs/settings.html'), name='settings'),
    path('application/<int:pk>/', views.application_detail, name='application_detail'),
    path('job/save/<int:pk>/', lambda request, pk: redirect('jobs:saved_jobs'), name='save_job'),
]