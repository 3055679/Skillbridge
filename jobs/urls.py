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
    path('application/<int:pk>/', views.application_detail, name='application_detail'),
    path('saved-jobs/', views.saved_jobs, name='saved_jobs'),
    path('job/<int:pk>/save/', views.toggle_save_job, name='save_job'),

    path('community/', views.community_list, name='community'),
    path('community/ask/', views.ask_question, name='community_ask'),
    path('community/<int:pk>/', views.community_detail, name='community_detail'),
    path('community/<int:pk>/answer/', views.post_answer, name='community_answer'),
    path('community/vote/', views.vote_view, name='community_vote'),
    path('community/report/', views.report_view, name='community_report'),

    path('settings/', views.settings_view, name='settings'),
    path('application/<int:application_id>/withdraw/', views.withdraw_application, name='withdraw_application'),
    path('assessment-reports/', views.assessment_reports, name='assessment_reports'),
    # path('settings/calendar/<uuid:token>.ics', views.settings_calendar, name='settings_calendar'),
    # path('employer/notifications/mark-read/', views.mark_notifications_read, name='mark_notifications_read'),
    path('notifications/mark-read/', views.mark_notifications_read, name='mark_notifications_read'),
    path('notifications/', views.student_notifications, name='student_notifications'),
    path('notifications/<int:pk>/read/', views.student_notification_read, name='student_notification_read'),
    path('notifications/mark-all-read/', views.student_notifications_mark_all_read, name='student_notifications_mark_all_read'),

    path('employer/jobs/', views.employer_jobs, name='employer_jobs'),
    path('employer/edit-job/<int:job_id>/', views.edit_job, name='edit_job'),
]