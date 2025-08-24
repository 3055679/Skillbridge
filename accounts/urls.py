from django.urls import path, reverse_lazy
from . import views
from django.contrib.auth import views as auth_views
from .forms import CustomPasswordResetForm, CustomPasswordChangeForm

app_name = 'accounts'

urlpatterns = [
    path('register/student/', views.student_signup, name='student_signup'),
    path('register/employer/', views.employer_signup, name='employer_signup'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('verify-email/<uuid:token>/', views.verify_email, name='verify_email'),
    path('email-verification-sent/', views.email_verification_sent, name='email_verification_sent'),
    path('pending-approval/', views.pending_approval, name='pending_approval'),
    path('password-reset/', 
         auth_views.PasswordResetView.as_view(
             template_name='accounts/password_reset.html',
             email_template_name='accounts/password_reset_email.html',
             subject_template_name='accounts/password_reset_subject.txt',
             success_url=reverse_lazy('accounts:password_reset_done'),
             form_class=CustomPasswordResetForm
         ), 
         name='password_reset'),
    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name='accounts/password_reset_done.html'
         ), 
         name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(
             template_name='accounts/password_reset_confirm.html',
             success_url=reverse_lazy('accounts:password_reset_complete')
         ), 
         name='password_reset_confirm'),
    path('password-reset-complete/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name='accounts/password_reset_complete.html'
         ), 
         name='password_reset_complete'),
    path('password-change/', 
         auth_views.PasswordChangeView.as_view(
             template_name='accounts/password_change.html',
             success_url=reverse_lazy('accounts:password_change_done'),
             form_class=CustomPasswordChangeForm
         ), 
         name='password_change'),
    path('password-change/done/', 
         auth_views.PasswordChangeDoneView.as_view(
             template_name='accounts/password_change_done.html'
         ), 
         name='password_change_done'),
    path('profile/student/', views.student_profile, name='student_profile'),
    path('profile/employer/', views.employer_profile, name='employer_profile'),
    path('skills/remove/<int:skill_id>/', views.remove_skill, name='remove_skill'),
    path('profile/add_skill/', views.add_skill, name='add_skill'),
    path('education/edit/<int:id>/', views.edit_education, name='edit_education'),
    path('education/delete/<int:id>/', views.delete_education, name='delete_education'),
    path('experience/edit/<int:id>/', views.edit_experience, name='edit_experience'),
    path('experience/delete/<int:id>/', views.delete_experience, name='delete_experience'),
    path('portfolio/edit/<int:id>/', views.edit_portfolio, name='edit_portfolio'),
    path('portfolio/delete/<int:id>/', views.delete_portfolio, name='delete_portfolio'),
    path('portfolio/view/<int:id>/', views.view_portfolio, name='view_portfolio'),
    path('home/', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path("profile/upload-picture/", views.upload_profile_picture, name="upload_profile_picture"),
    
]