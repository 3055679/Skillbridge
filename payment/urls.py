from django.urls import path
from . import views

app_name = 'payment'

urlpatterns = [
    path('assign-task/<int:application_id>/', views.assign_task, name='assign_task'),
    path('submit-task/<int:task_id>/', views.submit_task, name='submit_task'),
    path('submit-feedback/<int:task_id>/', views.submit_feedback, name='submit_feedback'),
    path('withdraw-earnings/', views.withdraw_earnings, name='withdraw_earnings'),
    path('task-submissions/', views.task_submissions, name='task_submissions'),
    path('stripe-connect-onboarding/', views.stripe_connect_onboarding, name='stripe_connect_onboarding'),
]