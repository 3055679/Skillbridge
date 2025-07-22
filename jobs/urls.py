from django.shortcuts import redirect, render
from django.urls import path
from . import views

app_name = 'jobs'

urlpatterns = [
    path('dashboard/', views.student_dashboard, name='student_dashboard'),
    path('applications/', views.my_applications, name='my_applications'),
    path('job/<int:job_id>/apply/', views.apply_job, name='apply_job'),
    path('employer/dashboard/', views.employer_dashboard, name='employer_dashboard'),
    path('employer/post-job/', views.post_job, name='post_job'),
    path('employer/application/<int:application_id>/', views.manage_application, name='manage_application'),
    path('employer/interview/<int:application_id>/', views.schedule_interview, name='schedule_interview'),
    path('job/<int:pk>/', views.job_detail, name='job_detail'),
    # Placeholder URLs
    path('resume-builder/', lambda request: render(request, 'jobs/resume_builder.html'), name='resume_builder'),
    path('saved-jobs/', lambda request: render(request, 'jobs/saved_jobs.html'), name='saved_jobs'),
    path('interviews/', lambda request: render(request, 'jobs/interviews.html'), name='interviews'),
    path('community/', lambda request: render(request, 'jobs/community.html'), name='community'),
    path('settings/', lambda request: render(request, 'jobs/settings.html'), name='settings'),
    # path('job/<int:pk>/', lambda request, pk: render(request, 'jobs/job_detail.html'), name='job_detail'),
    path('application/<int:pk>/', lambda request, pk: render(request, 'jobs/application_detail.html'), name='application_detail'),
    path('interview/<int:pk>/', lambda request, pk: render(request, 'jobs/interview_detail.html'), name='interview_detail'),
    path('job/save/<int:pk>/', lambda request, pk: redirect('jobs:saved_jobs'), name='save_job'),
    path('interview/reschedule/<int:pk>/', lambda request, pk: redirect('jobs:interviews'), name='reschedule_interview'),
    path('jobs/', views.job_list, name='job_list'),
]