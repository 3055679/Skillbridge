import uuid
from venv import logger
from django.db import IntegrityError
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.views.decorators.csrf import csrf_protect
from django.contrib import messages
from django.utils import timezone
from accounts.models import StudentProfile, EmployerProfile
from payment.models import Payment, TaskAssignment
from .models import ApplicationResponse, Job, Application, Interview, JobQuestion, ProposedInterviewSlot, Notification
from .forms import ApplicationForm, JobForm, InterviewForm, JobQuestionFormSet, MaxApplicationsForm, ResumeForm
from django.http import Http404, HttpResponse
import tempfile
import subprocess
import re
import os
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.contrib.contenttypes.models import ContentType
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.db.models import Q
from django.db import transaction, IntegrityError
from assessments.models import ApplicantChosenSkill, AssessmentBlueprint  # NEW
from assessments.services import create_assessment_for_application         # NEW
from django.db.models import Prefetch


@csrf_protect
@login_required
def student_dashboard(request):
    try:
        student = request.user.studentprofile
    except StudentProfile.DoesNotExist:
        student = StudentProfile.objects.create(user=request.user)
        messages.warning(request, 'Please complete your profile to get started.')

    applications = Application.objects.filter(student=student).select_related('job__employer')
    task_assignments = TaskAssignment.objects.filter(application__student=student).select_related('application__job', 'submission', 'feedback')
    # applications = Application.objects.filter(student=student)
    total_applications = applications.count()
    interviews = applications.filter(status='INTERVIEW').count()
    pending = applications.filter(status='PENDING').count()
    rejected = applications.filter(status='REJECTED').count()
    payments = Payment.objects.filter(application__student=student, released=True, withdrawn=False)
    total_earnings = sum(p.amount for p in payments)
    sidebar_profile_image_url = cache_busted_media_url(
        student.profile_picture, 'images/default-profile.png'
    )
    
    recent_applications = applications.order_by('-applied_date')[:3]
    
    upcoming_interviews = Interview.objects.filter(
        application__student=student,
        status='SCHEDULED',
        interview_date__gte=timezone.now()
    ).order_by('interview_date')[:2]
    
    recommended_jobs = Job.objects.filter(
        is_active=True,
        application_deadline__gt=timezone.now()
    ).order_by('-posted_date')[:3]

    saved_job_ids = []
    if hasattr(request.user, 'studentprofile'):
        saved_job_ids = list(
            SavedJob.objects.filter(student=request.user.studentprofile)
            .values_list('job_id', flat=True)
        )

    
    context = {
        'student': student,
        'total_applications': total_applications,
        'interviews': interviews,
        'pending': pending,
        'rejected': rejected,
        'recent_applications': recent_applications,
        'upcoming_interviews': upcoming_interviews,
        'recommended_jobs': recommended_jobs,
        'saved_job_ids': saved_job_ids,
        'total_earnings': total_earnings,
        'task_assignments': task_assignments,
        'sidebar_profile_image_url': sidebar_profile_image_url,
    }
    return render(request, 'jobs/student_dashboard.html', context)

@csrf_protect
@login_required
def student_interviews(request):
    try:
        student = request.user.studentprofile
    except StudentProfile.DoesNotExist:
        student = StudentProfile.objects.create(user=request.user)
        messages.warning(request, 'Please complete your profile to get started.')
    
    interviews = Interview.objects.filter(
        application__student=student
    ).order_by('-interview_date')
    
    context = {
        'student': student,
        'interviews': interviews,
    }
    return render(request, 'jobs/student_interviews.html', context)

@csrf_protect
@login_required
def my_applications(request):
    try:
        student = request.user.studentprofile
    except StudentProfile.DoesNotExist:
        student = StudentProfile.objects.create(user=request.user)
        messages.warning(request, 'Please complete your profile to get started.')
    
    applications = Application.objects.filter(student=student).order_by('-applied_date')
    
    context = {
        'student': student,
        'applications': applications,
    }
    return render(request, 'jobs/my_applications.html', context)

# @csrf_protect
# @login_required
# def apply_job(request, job_id):
#     job = get_object_or_404(Job, id=job_id, is_active=True)
#     if not job.is_accepting_applications():
#         messages.error(request, "This job is closed and no longer accepting applications.")
#         return redirect('jobs:job_list')
    
#     profile = get_object_or_404(StudentProfile, user=request.user)
    
#     # Check mandatory fields
#     missing_fields = []
#     if not profile.student_id_document:
#         missing_fields.append("Student ID Document")
#     if not profile.skills.exists():
#         missing_fields.append("Skills")
#     if not profile.work_preference:
#         missing_fields.append("Work Preference")
#     if not profile.availability:
#         missing_fields.append("Availability")
#     if not profile.resume:
#         missing_fields.append("Resume")
#     if not profile.educations.exists():
#         missing_fields.append("Education")
#     if not profile.experiences.exists():
#         missing_fields.append("Experience")
#     if not profile.portfolio_items.exists():
#         missing_fields.append("Portfolio Items")
    
#     if missing_fields:
#         messages.error(
#             request,
#             f"Please complete the following required fields in your profile: {', '.join(missing_fields)}"
#         )
#         return redirect('accounts:student_profile')

#     # 👉 Prevent duplicate applications (works for GET and POST)
#     existing = Application.objects.filter(student=profile, job=job).first()
#     if existing:
#         messages.info(
#             request,
#             f"You've already applied to '{job.title}' at {job.employer.company_name} "
#             f"on {existing.applied_date:%b %d, %Y}."
#         )
#         return redirect('jobs:application_detail', pk=existing.pk)

#     if request.method == 'POST':
#         form = ApplicationForm(request.POST, request.FILES)
#         if form.is_valid():
#             cover_letter = form.cleaned_data.get('cover_letter', '')
#             resume_file = form.cleaned_data.get('resume')

#             # Check again in case of race condition
#             if not job.is_accepting_applications():
#                 messages.error(request, "This job just closed and is no longer accepting applications.")
#                 return redirect('jobs:job_list')

#             try:
#                 with transaction.atomic():
#                     application, created = Application.objects.get_or_create(
#                         student=profile,
#                         job=job,
#                         defaults={'cover_letter': cover_letter, 'resume': resume_file}
#                     )
#                     if not created:
#                         # Another request created it first
#                         messages.info(
#                             request,
#                             f"You've already applied to '{job.title}'."
#                         )
#                         return redirect('jobs:application_detail', pk=application.pk)

#                     # Save custom question responses
#                     for question in job.questions.all():
#                         response_key = f'question_{question.id}'
#                         response_val = request.POST.get(response_key)
#                         if response_val:
#                             ApplicationResponse.objects.create(
#                                 application=application,
#                                 question=question,
#                                 response=response_val
#                             )

#                     # NEW: store picked assessment skills (max 3) for this application
#                     picked = form.cleaned_data.get("assessment_skills")
#                     if picked:
#                         # ensure clean slate if needed
#                         ApplicantChosenSkill.objects.filter(application=application).delete()
#                         ApplicantChosenSkill.objects.bulk_create([
#                             ApplicantChosenSkill(application=application, skill=s) for s in picked
#                         ])

#                     # NEW: Create internship assessment & send invite
#                     blueprint = getattr(job, "assessment_blueprint", None) or AssessmentBlueprint.objects.filter(kind="internship").first()
#                     if blueprint:
#                         create_assessment_for_application(application, blueprint)

#                 messages.success(request, 'Application submitted successfully.')
#                 return redirect('jobs:my_applications')

#             except IntegrityError:
#                 # Safety net for any rare race condition on the unique constraint
#                 existing = Application.objects.filter(student=profile, job=job).first()
#                 if existing:
#                     messages.info(
#                         request,
#                         f"You've already applied to '{job.title}'."
#                     )
#                     return redirect('jobs:application_detail', pk=existing.pk)
#                 messages.error(request, "Something went wrong while submitting your application. Please try again.")
#                 return redirect('jobs:job_detail', pk=job.pk)
#         else:
#             messages.error(request, "Please correct the errors in the form.")
#     else:
#         form = ApplicationForm()

#     return render(request, 'jobs/apply_job.html', {'form': form, 'job': job})

@csrf_protect
@login_required
def apply_job(request, job_id):
    job = get_object_or_404(Job, id=job_id, is_active=True)
    if not job.is_accepting_applications():
        messages.error(request, "This job is closed and no longer accepting applications.")
        return redirect('jobs:job_list')
    
    profile = get_object_or_404(StudentProfile, user=request.user)

    # Check mandatory fields
    missing_fields = []
    if not profile.student_id_document:
        missing_fields.append("Student ID Document")
    if not profile.skills.exists():
        missing_fields.append("Skills")
    if not profile.work_preference:
        missing_fields.append("Work Preference")
    if not profile.availability:
        missing_fields.append("Availability")
    if not profile.resume:
        missing_fields.append("Resume")
    if not profile.educations.exists():
        missing_fields.append("Education")
    if not profile.experiences.exists():
        missing_fields.append("Experience")
    if not profile.portfolio_items.exists():
        missing_fields.append("Portfolio Items")
    
    if missing_fields:
        messages.error(
            request,
            f"Please complete the following required fields in your profile: {', '.join(missing_fields)}"
        )
        return redirect('accounts:student_profile')

    # Prevent duplicate applications
    existing = Application.objects.filter(student=profile, job=job).first()
    if existing:
        messages.info(
            request,
            f"You've already applied to '{job.title}' at {job.employer.company_name} "
            f"on {existing.applied_date:%b %d, %Y}."
        )
        return redirect('jobs:application_detail', pk=existing.pk)

    if request.method == 'POST':
        form = ApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            cover_letter = form.cleaned_data.get('cover_letter', '')
            resume_file = form.cleaned_data.get('resume')
            picked_skills = form.cleaned_data.get('assessment_skills')  # <-- AssessmentSkill queryset

            if not job.is_accepting_applications():
                messages.error(request, "This job just closed and is no longer accepting applications.")
                return redirect('jobs:job_list')

            try:
                with transaction.atomic():
                    application, created = Application.objects.get_or_create(
                        student=profile,
                        job=job,
                        defaults={'cover_letter': cover_letter, 'resume': resume_file}
                    )
                    if not created:
                        messages.info(request, f"You've already applied to '{job.title}'.")
                        return redirect('jobs:application_detail', pk=application.pk)

                    # Save custom job question responses
                    for question in job.questions.all():
                        response_key = f'question_{question.id}'
                        response_val = request.POST.get(response_key)
                        if response_val:
                            ApplicationResponse.objects.create(
                                application=application,
                                question=question,
                                response=response_val
                            )

                    # ✅ Store the assessment picks in ApplicantChosenSkill (NOT application.declared_skills)
                    ApplicantChosenSkill.objects.filter(application=application).delete()
                    if picked_skills:
                        ApplicantChosenSkill.objects.bulk_create([
                            ApplicantChosenSkill(application=application, skill=s)
                            for s in picked_skills
                        ])

                    # ✅ Create assessment immediately if a blueprint exists
                    blueprint = AssessmentBlueprint.objects.filter(kind="internship").first()
                    if blueprint:
                        create_assessment_for_application(application, blueprint)

                messages.success(
                    request,
                    'Application submitted. You can start your assessment from My Applications or the email we sent.'
                )
                return redirect('jobs:my_applications')

            except IntegrityError:
                existing = Application.objects.filter(student=profile, job=job).first()
                if existing:
                    messages.info(request, f"You've already applied to '{job.title}'.")
                    return redirect('jobs:application_detail', pk=existing.pk)
                messages.error(request, "Something went wrong while submitting your application. Please try again.")
                return redirect('jobs:job_detail', pk=job.pk)
        else:
            messages.error(request, "Please correct the errors in the form.")
    else:
        form = ApplicationForm()

    return render(request, 'jobs/apply_job.html', {'form': form, 'job': job})


@csrf_protect
@login_required
def employer_dashboard(request):
    try:
        employer = request.user.employerprofile
    except EmployerProfile.DoesNotExist:
        messages.error(request, 'Please complete your employer profile.')
        return redirect('accounts:employer_profile')
    
    jobs = Job.objects.filter(employer=employer)
    applications = Application.objects.filter(job__employer=employer)
    # notifications = Notification.objects.filter(employer=employer, is_read=False)
    notifications = (Notification.objects
                 .filter(employer=request.user.employerprofile, is_read=False)
                 .order_by('-created_at'))
    reports = Report.objects.filter(assessment__application__job__employer=employer).order_by('-assessment__submitted_at')
    sidebar_company_logo_url = cache_busted_media_url(
        employer.company_logo, 'images/default-logo.png'
    )

    logger.debug("Loaded %s unseen notifications for employer %s", notifications.count(), employer.company_name)
    
    context = {
        'employer': employer,
        'jobs': jobs,
        'applications': applications,
        'notifications': notifications,
        'status_choices': Application.STATUS_CHOICES,  # Add this line
        'reports': reports,
        'sidebar_company_logo_url': sidebar_company_logo_url,
    }
    return render(request, 'jobs/employer_dashboard.html', context)

# @csrf_protect
# @login_required(login_url='accounts:login')
# def mark_notifications_read(request):
#     if request.method == "POST":
#         notification_ids = request.POST.getlist('notification_ids')
#         if notification_ids:
#             updated = Notification.objects.filter(
#                 employer__user=request.user,
#                 id__in=notification_ids,
#                 is_read=False
#             ).update(is_read=True)
#             logger.debug("Marked %s notifications as read for employer %s", updated, request.user.employerprofile.company_name)
#             return JsonResponse({'status': 'success', 'updated': updated})
#         return JsonResponse({'status': 'error', 'message': 'No notification IDs provided'}, status=400)
#     return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

@require_POST
@csrf_protect
def mark_notifications_read(request):
    ids = request.POST.getlist('ids[]') or request.POST.getlist('ids')
    qs = Notification.objects.filter(
        id__in=ids,
        employer=request.user.employerprofile
    )
    updated = qs.update(is_read=True)
    return JsonResponse({'updated': updated})

@csrf_protect
@login_required
def post_job(request):
    try:
        employer = request.user.employerprofile
    except EmployerProfile.DoesNotExist:
        messages.error(request, 'Please complete your employer profile.')
        return redirect('accounts:employer_profile')
       
    if request.method == 'POST':
        form = JobForm(request.POST, request.FILES)
        question_formset = JobQuestionFormSet(request.POST)
        if form.is_valid() and question_formset.is_valid():
            job = form.save(commit=False)
            job.employer = employer
            job.is_active = True
            job.posted_date = timezone.now()
            job.save()
            for form in question_formset:
                if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                    question = form.save(commit=False)
                    question.job = job
                    question.save()
            messages.success(request, 'Job posted successfully!')
            return redirect('jobs:employer_dashboard')
    else:
        form = JobForm()
        question_formset = JobQuestionFormSet()
       
    return render(request, 'jobs/post_job.html', {'form': form, 'question_formset': question_formset})

@csrf_protect
@login_required
def job_status_update(request, pk):
    job = get_object_or_404(Job, pk=pk, employer__user=request.user)
    if request.method == 'POST':
        is_active = request.POST.get('is_active') == 'True'
        job.is_active = is_active
        job.save()
        messages.success(request, f"Job status updated to {'Active' if is_active else 'Closed'}.")
        return redirect('jobs:employer_dashboard')
    
    return render(request, 'jobs/job_status_form.html', {'job': job})

@csrf_protect
@login_required
def manage_max_applications(request, pk):
    job = get_object_or_404(Job, pk=pk, employer__user=request.user)
    if request.method == 'POST':
        form = MaxApplicationsForm(request.POST, instance=job)
        action = request.POST.get('action')
        if action == 'close':
            job.is_active = False
            job.save()
            messages.success(request, f"Job '{job.title}' closed.")
            Notification.objects.filter(job=job).update(is_read=True)
            return redirect('jobs:employer_dashboard')
        elif form.is_valid():
            form.save()
            messages.success(request, f"Maximum applications for '{job.title}' updated.")
            Notification.objects.filter(job=job).update(is_read=True)
            return redirect('jobs:employer_dashboard')
    else:
        form = MaxApplicationsForm(instance=job)
    
    return render(request, 'jobs/manage_max_applications.html', {'form': form, 'job': job})

@csrf_protect
@login_required
def bulk_manage_applications(request):
    if not hasattr(request.user, 'employerprofile'):
        messages.error(request, "Only employers can manage applications.")
        return redirect('jobs:student_dashboard')
    if request.method == 'POST':
        application_ids = request.POST.getlist('application_ids')
        status = request.POST.get('status')
        message = request.POST.get('message', '')
        applications = Application.objects.filter(
            id__in=application_ids, 
            job__employer__user=request.user
        )
        if status in [choice[0] for choice in Application.STATUS_CHOICES]:
            applications.update(status=status)
            if message:
                # In a real app, send email or notification to students
                for app in applications:
                    Notification.objects.create(
                        employer=app.job.employer,
                        job=app.job,
                        message=f"Application status updated: {message}"
                    )
            messages.success(request, f"Updated {applications.count()} applications.")
        return redirect('jobs:employer_dashboard')
    return redirect('jobs:employer_dashboard')

@csrf_protect
@login_required
def manage_application(request, application_id):
    application = get_object_or_404(Application, pk=application_id, job__employer__user=request.user)
    student_profile = application.student
    
    if request.method == 'POST':
        status = request.POST.get('status')
        if status in [choice[0] for choice in Application.STATUS_CHOICES]:
            application.status = status
            application.save()
            messages.success(request, f'Application status updated to {application.get_status_display()}')
            return redirect('jobs:employer_dashboard')
    
    context = {
        'application': application,
        'student_profile': student_profile,
        'status_choices': Application.STATUS_CHOICES,
    }
    return render(request, 'jobs/manage_application.html', context)

@csrf_protect
@login_required
def schedule_interview(request, application_id):
    application = get_object_or_404(Application, pk=application_id, job__employer__user=request.user)
    if request.method == 'POST':
        form = InterviewForm(request.POST)
        if form.is_valid():
            interview = form.save(commit=False)
            interview.application = application
            interview.status = 'SCHEDULED'
            interview.save()
            proposed_slots = form.cleaned_data.get('proposed_slots')
            if proposed_slots:
                for slot in proposed_slots.split('\n'):
                    slot = slot.strip()
                    if slot:
                        try:
                            slot_time = timezone.datetime.strptime(slot, '%Y-%m-%d %H:%M')
                            ProposedInterviewSlot.objects.create(
                                interview=interview,
                                slot_time=slot_time
                            )
                        except ValueError:
                            messages.warning(request, f"Invalid slot format: {slot}")
            application.status = 'INTERVIEW'
            application.save()
            messages.success(request, 'Interview scheduled successfully!')
            return redirect('jobs:employer_dashboard')
    else:
        form = InterviewForm()
    
    return render(request, 'jobs/schedule_interview.html', {'form': form, 'application': application})

@csrf_protect
@login_required
def employer_interviews(request):
    try:
        employer = request.user.employerprofile
    except EmployerProfile.DoesNotExist:
        messages.error(request, 'Please complete your employer profile.')
        return redirect('accounts:employer_profile')
    
    interviews = Interview.objects.filter(
        application__job__employer=employer,
        status='SCHEDULED'
    ).order_by('interview_date')
    
    context = {
        'employer': employer,
        'interviews': interviews,
    }
    return render(request, 'jobs/employer_interviews.html', context)

# @csrf_protect
# @login_required
# def interview_detail(request, pk):
#     interview = get_object_or_404(Interview, pk=pk)
#     if request.user.is_student and interview.application.student.user != request.user:
#         messages.error(request, "You can only view your own interviews.")
#         return redirect('jobs:student_dashboard')
#     elif request.user.is_employer and interview.application.job.employer.user != request.user:
#         messages.error(request, "You can only view interviews for your jobs.")
#         return redirect('jobs:employer_dashboard')
#     return render(request, 'jobs/interview_detail.html', {
#         'interview': interview,
#         'application': interview.application,
#         'student_profile': interview.application.student,
#     })


@csrf_protect
@login_required
def interview_detail(request, pk):
    interview = get_object_or_404(Interview, pk=pk)
    
    # Check if user is a student and owns the application
    if hasattr(request.user, 'studentprofile') and interview.application.student.user == request.user:
        return render(request, 'jobs/interview_detail.html', {
            'interview': interview,
            'application': interview.application,
            'student_profile': interview.application.student,
            'user_type': 'student',
        })
    
    # Check if user is an employer and owns the job
    elif hasattr(request.user, 'employerprofile') and interview.application.job.employer.user == request.user:
        return render(request, 'jobs/interview_detail.html', {
            'interview': interview,
            'application': interview.application,
            'student_profile': interview.application.student,
            'user_type': 'employer',
        })
    
    # Unauthorized access
    else:
        messages.error(request, "You do not have permission to view this interview.")
        if hasattr(request.user, 'employerprofile'):
            return redirect('jobs:employer_dashboard')
        elif hasattr(request.user, 'studentprofile'):
            return redirect('jobs:student_dashboard')
        else:
            return redirect('jobs:job_list')

@csrf_protect
@login_required
def reschedule_interview(request, pk):
    interview = get_object_or_404(Interview, pk=pk)
    if not hasattr(request.user, 'employerprofile'):
        messages.error(request, "Only employers can reschedule interviews.")
        return redirect('jobs:student_dashboard')
    if interview.application.job.employer.user != request.user:
        messages.error(request, "You can only reschedule interviews for your jobs.")
        return redirect('jobs:employer_dashboard')
    if interview.status != 'SCHEDULED':
        messages.error(request, 'Only scheduled interviews can be rescheduled.')
        return redirect('jobs:employer_interviews')
    
    if request.method == 'POST':
        form = InterviewForm(request.POST, instance=interview)
        if form.is_valid():
            form.save()
            proposed_slots = form.cleaned_data.get('proposed_slots')
            if proposed_slots:
                interview.proposed_slots.all().delete()  # Clear existing slots
                for slot in proposed_slots.split('\n'):
                    slot = slot.strip()
                    if slot:
                        try:
                            slot_time = timezone.datetime.strptime(slot, '%Y-%m-%d %H:%M')
                            ProposedInterviewSlot.objects.create(
                                interview=interview,
                                slot_time=slot_time
                            )
                        except ValueError:
                            messages.warning(request, f"Invalid slot format: {slot}")
            messages.success(request, 'Interview rescheduled successfully.')
            return redirect('jobs:employer_interviews')
    else:
        form = InterviewForm(instance=interview)
    
    return render(request, 'jobs/reschedule_interview.html', {
        'form': form,
        'interview': interview,
        'application': interview.application,
    })

@csrf_protect
@login_required
def cancel_interview(request, pk):
    interview = get_object_or_404(Interview, pk=pk)
    if not hasattr(request.user, 'employerprofile'):
        messages.error(request, "Only employers can cancel interviews.")
        return redirect('jobs:student_dashboard')
    if interview.application.job.employer.user != request.user:
        messages.error(request, "You can only cancel interviews for your jobs.")
        return redirect('jobs:employer_dashboard')
    if interview.status != 'SCHEDULED':
        messages.error(request, 'Only scheduled interviews can be canceled.')
        return redirect('jobs:employer_interviews')
    
    if request.method == 'POST':
        interview.status = 'CANCELED'
        interview.save()
        interview.application.status = 'PENDING'
        interview.application.save()
        messages.success(request, 'Interview canceled successfully.')
        return redirect('jobs:employer_interviews')
    
    return render(request, 'jobs/cancel_interview.html', {
        'interview': interview,
        'application': interview.application,
    })

# def job_list(request):
#     jobs = Job.objects.filter(is_active=True).order_by('-posted_date')
#     context = {
#         'jobs': jobs,
#     }
#     return render(request, 'jobs/job_list.html', context)

def job_list(request):
    time_range = request.GET.get('time_range', 'all')
    now = timezone.now()
    
    # Define time range filters
    if time_range == 'today':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif time_range == 'week':
        start_date = now - timedelta(days=now.weekday())  # Start of the week (Monday)
    elif time_range == 'month':
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        start_date = None  # All time

    # Filter jobs based on time range
    jobs = Job.objects.filter(is_active=True)
    if start_date:
        jobs = jobs.filter(posted_date__gte=start_date)
    jobs = jobs.order_by('-posted_date').select_related('employer')

    context = {
        'jobs': jobs,
        'time_range': time_range,
    }

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        jobs_data = [
            {
                'id': job.id,
                'title': job.title,
                'employer': {'company_name': job.employer.company_name},
                'location': job.location,
                'job_type': job.job_type,
                'job_type_display': job.get_job_type_display(),
                'description': job.description,
                'interview_type_display': job.get_interview_type_display(),
                'skills_required': [skill.name for skill in job.skills_required.all()],
                'posted_date': job.posted_date.strftime('%b %d, %Y'),
                'application_deadline': job.application_deadline.strftime('%b %d, %Y') if job.application_deadline else None,
                'is_accepting_applications': job.is_accepting_applications(),
            } for job in jobs
        ]
        return JsonResponse({
            'jobs': jobs_data,
            'is_student': request.user.is_authenticated and hasattr(request.user, 'studentprofile'),
        })

    return render(request, 'jobs/job_list.html', context)

def job_detail(request, pk):
    job = get_object_or_404(Job, id=pk)
    is_closed = not job.is_accepting_applications()
    return render(request, 'jobs/job_detail.html', {
        'job': job,
        'is_closed': is_closed,
    })

# @csrf_protect
# @login_required
# def application_detail(request, pk):
#     application = get_object_or_404(Application, pk=pk)
#     if request.user.is_student and application.student.user != request.user:
#         messages.error(request, "You can only view your own applications.")
#         return redirect('jobs:student_dashboard')
#     elif request.user.is_employer and application.job.employer.user != request.user:
#         messages.error(request, "You can only view applications for your jobs.")
#         return redirect('jobs:employer_dashboard')
#     return render(request, 'jobs/application_detail.html', {'application': application})

from assessments.models import Assessment, Report  # add this import

@csrf_protect
@login_required
def application_detail(request, pk):
    application = get_object_or_404(Application, pk=pk)

    # Permission checks
    if request.user.is_student and application.student.user != request.user:
        messages.error(request, "You can only view your own applications.")
        return redirect('jobs:student_dashboard')
    elif request.user.is_employer and application.job.employer.user != request.user:
        messages.error(request, "You can only view applications for your jobs.")
        return redirect('jobs:employer_dashboard')

    # Get assessment and report if available
    assessment = getattr(application, "assessment", None)
    report = getattr(assessment, "report", None) if assessment else None

    return render(request, 'jobs/application_detail.html', {
        'application': application,
        'assessment': assessment,
        'report': report,
    })





@csrf_protect
@login_required
def resume_builder(request):
    if not hasattr(request.user, 'studentprofile'):
        messages.error(request, "Only students can access the resume builder.")
        return redirect('jobs:job_list')

    sp = request.user.studentprofile

    def latex_escape(s: str) -> str:
        if not s:
            return ""
        repl = {
            '\\': r'\textbackslash{}',
            '&': r'\&',
            '%': r'\%',
            '$': r'\$',
            '#': r'\#',
            '_': r'\_',
            '{': r'\{',
            '}': r'\}',
            '~': r'\textasciitilde{}',
            '^': r'\textasciicircum{}',
        }
        out = []
        for ch in str(s):
            out.append(repl.get(ch, ch))
        return "".join(out)

    def fmt_month(d):
        try:
            return d.strftime('%b %Y') if d else ''
        except Exception:
            return ''

    # Build LaTeX (two themes; a minimal fallback avoids titlesec/titlerule)
    def build_latex(form, educations, experiences, theme='ats', minimal=False):
        first = latex_escape(form.cleaned_data['first_name'])
        last  = latex_escape(form.cleaned_data['last_name'])
        email = latex_escape(form.cleaned_data['email'])
        phone = latex_escape(form.cleaned_data['phone'])
        addr  = latex_escape(form.cleaned_data['address'])
        addl  = latex_escape(form.cleaned_data.get('additional_info', '')).replace('\n', r'\\')
        skills_lines = [s.strip() for s in form.cleaned_data['skills'].splitlines() if s.strip()]
        # skill_items = "".join([rf"\item {latex_escape(s)}\n" for s in skills_lines])
        skill_items = "\n".join([r"\item " + latex_escape(s) for s in skills_lines])

        def edu_block():
            lines = []
            for e in educations:
                try:
                    degree = e.get_degree_display()
                except Exception:
                    degree = getattr(e, 'degree', '') or ''
                fos  = latex_escape(getattr(e, 'field_of_study', '') or '')
                inst = latex_escape(getattr(e, 'institution', '') or '')
                sy   = latex_escape(getattr(e, 'start_year', '') or '')
                ey   = "Present" if getattr(e, 'currently_studying', False) else latex_escape(getattr(e, 'end_year', '') or '')
                line = rf"\textbf{{{latex_escape(degree)}}} in {fos} --- {inst} \hfill {sy}--{ey}"
                lines.append(line)
            return r"\par ".join(lines) if lines else r"\emph{None selected}"

        def exp_block():
            lines = []
            for x in experiences:
                title   = latex_escape(getattr(x, 'title', '') or '')
                company = latex_escape(getattr(x, 'company', '') or '')
                sd      = fmt_month(getattr(x, 'start_date', None))
                ed      = 'Present' if getattr(x, 'currently_working', False) else fmt_month(getattr(x, 'end_date', None))
                desc    = latex_escape(getattr(x, 'description', '') or '').replace('\n', r'\\')
                line = rf"\textbf{{{title}}} --- {company} \hfill {sd}--{ed}\\\small {desc}"
                lines.append(line)
            return r"\par ".join(lines) if lines else r"\emph{None selected}"

        accent_rgb = "0,0,0" if theme == 'ats' else "67,97,238"

        if minimal:
            # No titlesec, no titlerule — maximally compatible
            return rf"""
\documentclass[a4paper,10pt]{{article}}
\usepackage[utf8]{{inputenc}}
\usepackage[T1]{{fontenc}}
\usepackage[margin=1in]{{geometry}}
\usepackage[hidelinks]{{hyperref}}
\usepackage{{enumitem}}
\usepackage{{xcolor}}
\usepackage{{helvet}}
\renewcommand\familydefault{{\sfdefault}}
\definecolor{{Accent}}{{RGB}}{{{accent_rgb}}}
\setlength{{\parindent}}{{0pt}}
\setlength{{\parskip}}{{4pt}}

\begin{{document}}
\begin{{center}}
    {{\LARGE\bfseries {first} {last}}}\\[0.2cm]
    \href{{mailto:{email}}}{{{email}}} \textbullet\ {phone} \textbullet\ {addr}
\end{{center}}

{{\large\bfseries Education}}\par
{edu_block()}

{{\large\bfseries Experience}}\par
{exp_block()}

{{\large\bfseries Skills}}\par
\begin{{itemize}}
{skill_items}
\end{{itemize}}

{("\\n{\\large\\bfseries Additional Information}\\par\\n" + addl) if form.cleaned_data.get('additional_info') else ""}

\end{{document}}
"""
        else:
            # Pretty (uses titlesec + titlerule)
            return rf"""
\documentclass[a4paper,10pt]{{article}}
\usepackage[utf8]{{inputenc}}
\usepackage[T1]{{fontenc}}
\usepackage[margin=1in]{{geometry}}
\usepackage[hidelinks]{{hyperref}}
\usepackage{{titlesec}}
\usepackage{{enumitem}}
\usepackage{{xcolor}}
\usepackage{{helvet}}
\renewcommand\familydefault{{\sfdefault}}
\definecolor{{Accent}}{{RGB}}{{{accent_rgb}}}
\titleformat{{\section}}{{\large\bfseries\color{{Accent}}}}{{--}}{{0em}}{{}}[\titlerule]
\titlespacing*{{\section}}{{0pt}}{{6pt}}{{6pt}}
\setlist[itemize]{{leftmargin=*, itemsep=2pt, topsep=2pt}}
\setlength{{\parindent}}{{0pt}}
\setlength{{\parskip}}{{4pt}}

\begin{{document}}
\begin{{center}}
    {{\LARGE\bfseries {first} {last}}}\\[0.2cm]
    \href{{mailto:{email}}}{{{email}}} \textbullet\ {phone} \textbullet\ {addr}
\end{{center}}

\section*{{Education}}
{edu_block()}

\section*{{Experience}}
{exp_block()}

\section*{{Skills}}
\begin{{itemize}}
{skill_items}
\end{{itemize}}

{("\\n\\section*{Additional Information}\\n" + addl) if form.cleaned_data.get('additional_info') else ""}

\end{{document}}
"""

    if request.method == 'POST':
        form = ResumeForm(request.POST, user=request.user)
        if form.is_valid():
            # Fetch selected Education/Experience (limit to 2 server-side)
            edu_ids = [int(i) for i in form.cleaned_data.get('education_ids', [])][:2]
            exp_ids = [int(i) for i in form.cleaned_data.get('experience_ids', [])][:2]
            educations  = list(sp.educations.filter(id__in=edu_ids)) if hasattr(sp, 'educations') else []
            experiences = list(sp.experiences.filter(id__in=exp_ids)) if hasattr(sp, 'experiences') else []

            theme = form.cleaned_data.get('theme', 'ats')

            def compile_and_send(latex_content):
                with tempfile.TemporaryDirectory() as tmpdirname:
                    tex_path = os.path.join(tmpdirname, 'resume.tex')
                    pdf_path = os.path.join(tmpdirname, 'resume.pdf')
                    with open(tex_path, 'w', encoding='utf-8') as f:
                        f.write(latex_content)
                    try:
                        for _ in range(2):
                            subprocess.run(
                                ['pdflatex', '-interaction=nonstopmode', 'resume.tex'],
                                cwd=tmpdirname,
                                check=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True
                            )
                        with open(pdf_path, 'rb') as f:
                            resp = HttpResponse(f.read(), content_type='application/pdf')
                            resp['Content-Disposition'] = 'attachment; filename="resume.pdf"'
                            return resp, None
                    except subprocess.CalledProcessError as e:
                        log = (e.stdout or '') + '\n' + (e.stderr or '')
                        return None, log

            # Try pretty template first
            latex_pretty = build_latex(form, educations, experiences, theme=theme, minimal=False)
            resp, log = compile_and_send(latex_pretty)
            if resp:
                return resp

            # If titlesec/titlerule missing, fall back to minimal
            if log and ('titlesec.sty' in log or 'Undefined control sequence' in log):
                latex_min = build_latex(form, educations, experiences, theme=theme, minimal=True)
                resp2, log2 = compile_and_send(latex_min)
                if resp2:
                    return resp2
                else:
                    messages.error(request, "Failed to generate resume PDF. Please see LaTeX errors below.")
                    return render(request, 'jobs/resume_builder.html', {'form': form, 'latex_error': (log2 or log)[:8000]})

            # Otherwise show the actual error log
            messages.error(request, "Failed to generate resume PDF. Please see LaTeX errors below.")
            return render(request, 'jobs/resume_builder.html', {'form': form, 'latex_error': (log or '')[:8000]})
        else:
            messages.error(request, "Please correct the errors in the form.")
            return render(request, 'jobs/resume_builder.html', {'form': form})

    else:
        form = ResumeForm(user=request.user)
        return render(request, 'jobs/resume_builder.html', {'form': form})


    
# jobs/views.py


from accounts.models import StudentProfile
from .models import Job, SavedJob, CommunityQuestion, CommunityAnswer, Vote, AbuseReport, UserSettings
from .forms import QuestionForm, AnswerForm, ReportForm, UserSettingsForm

# ---------- Saved Jobs ----------
@login_required
def saved_jobs(request):
    if not hasattr(request.user, 'studentprofile'):
        messages.error(request, "Only students can view saved jobs.")
        return redirect('jobs:job_list')
    saved = SavedJob.objects.filter(student=request.user.studentprofile).select_related('job', 'job__employer').order_by('-created_at')
    return render(request, 'jobs/saved_jobs.html', {'saved': saved})

@login_required
@require_POST
def toggle_save_job(request, pk):
    if not hasattr(request.user, 'studentprofile'):
        return HttpResponseBadRequest("Only students can save jobs.")
    job = get_object_or_404(Job, pk=pk)

    obj, created = SavedJob.objects.get_or_create(student=request.user.studentprofile, job=job)
    if not created:
        obj.delete()
        status = 'removed'
    else:
        status = 'saved'

    # AJAX? return json
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': status})

    # Safe fallback: only redirect with pk when using a view name, not a URL string
    ref = request.META.get('HTTP_REFERER')
    if ref:
        return redirect(ref)
    return redirect('jobs:job_detail', pk=pk)

# ---------- Community ----------
@login_required
def community_list(request):
    qs = CommunityQuestion.objects.all()
    q = request.GET.get('q')
    if q:
        qs = qs.filter(title__icontains=q) | qs.filter(body__icontains=q)
    # Annotated score optional: simple order by created_at is fine
    return render(request, 'jobs/community.html', {
        'questions': qs.select_related('author', 'author__user'),
        'form': QuestionForm(),  # quick access to ask form (or use separate page)
    })

@login_required
def ask_question(request):
    if not hasattr(request.user, 'studentprofile'):
        messages.error(request, "Only students can post questions.")
        return redirect('jobs:community')
    if request.method == 'POST':
        form = QuestionForm(request.POST)
        if form.is_valid():
            q = form.save(commit=False)
            q.author = request.user.studentprofile
            q.save()
            messages.success(request, "Question posted!")
            return redirect('jobs:community_detail', pk=q.pk)
    else:
        form = QuestionForm()
    return render(request, 'jobs/community_ask.html', {'form': form})

@login_required
def community_detail(request, pk):
    question = get_object_or_404(CommunityQuestion, pk=pk)
    answers = question.answers.select_related('author', 'author__user').prefetch_related('replies')
    answer_form = AnswerForm()
    report_form = ReportForm(initial={'target_model': 'question', 'target_id': question.id})
    return render(request, 'jobs/community_detail.html', {
        'question': question,
        'answers': answers,
        'answer_form': answer_form,
        'report_form': report_form,
    })

@login_required
@require_POST
def post_answer(request, pk):
    question = get_object_or_404(CommunityQuestion, pk=pk)
    if not hasattr(request.user, 'studentprofile'):
        messages.error(request, "Only students can answer.")
        return redirect('jobs:community_detail', pk=pk)
    form = AnswerForm(request.POST)
    if form.is_valid():
        ans = CommunityAnswer(
            question=question,
            author=request.user.studentprofile,
            body=form.cleaned_data['body']
        )
        parent_id = form.cleaned_data.get('parent_id')
        if parent_id:
            parent = CommunityAnswer.objects.filter(pk=parent_id, question=question).first()
            if parent:
                ans.parent = parent
        ans.save()
        messages.success(request, "Posted!")
    else:
        messages.error(request, "Please write an answer.")
    return redirect('jobs:community_detail', pk=pk)

@login_required
@require_POST
def vote_view(request):
    model = request.POST.get('model')   # 'question' or 'answer'
    obj_id = request.POST.get('id')
    direction = request.POST.get('direction')  # 'up' or 'down'
    if model not in ('question', 'answer') or direction not in ('up', 'down'):
        return HttpResponseBadRequest("Invalid request")
    ct = ContentType.objects.get_for_model(CommunityQuestion if model=='question' else CommunityAnswer)
    target = get_object_or_404(ct.model_class(), pk=obj_id)
    val = 1 if direction == 'up' else -1
    vote, created = Vote.objects.get_or_create(
        user=request.user, content_type=ct, object_id=target.id,
        defaults={'value': val}
    )
    if not created:
        # toggle/flip
        vote.value = val if vote.value != val else 0  # allow unvote if same click
        if vote.value == 0:
            vote.delete()
        else:
            vote.save()
    # Return JSON for AJAX
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        # recompute score
        score = target.votes.aggregate(s=Coalesce(Sum('value'), 0))['s'] or 0
        return JsonResponse({'score': score})
    # fallback
    ref = request.META.get('HTTP_REFERER') or 'jobs:community'
    return redirect(ref)

@login_required
@require_POST
def report_view(request):
    form = ReportForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest("Invalid")
    model = form.cleaned_data['target_model']
    obj_id = form.cleaned_data['target_id']
    ct = ContentType.objects.get_for_model(CommunityQuestion if model=='question' else CommunityAnswer)
    target = get_object_or_404(ct.model_class(), pk=obj_id)
    AbuseReport.objects.create(
        reporter=request.user,
        reason=form.cleaned_data['reason'],
        content_type=ct,
        object_id=target.id
    )
    messages.success(request, "Reported to moderators.")
    return redirect(request.META.get('HTTP_REFERER') or 'jobs:community')

# ---------- Settings ----------
@login_required
def settings_view(request):
    if not hasattr(request.user, 'studentprofile'):
        messages.error(request, "Settings available for student accounts.")
        return redirect('jobs:job_list')

    sp = request.user.studentprofile
    settings_obj, _ = UserSettings.objects.get_or_create(student=sp)  # ✅ FIX

    if request.method == 'POST':
        form = UserSettingsForm(request.POST, instance=settings_obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Settings saved.")
            return redirect('jobs:settings')
    else:
        form = UserSettingsForm(instance=settings_obj)

    return render(request, 'jobs/settings.html', {'form': form})


from django.core.mail import EmailMultiAlternatives
from django.conf import settings

@csrf_protect
@login_required
def withdraw_application(request, application_id):
    application = get_object_or_404(Application, pk=application_id, student__user=request.user)
    
    # Prevent withdrawal if already withdrawn or accepted
    if application.status in ['WITHDRAWN', 'ACCEPTED']:
        messages.error(request, f"Cannot withdraw application: already {application.get_status_display().lower()}.")
        return redirect('jobs:my_applications')
    
    if request.method == 'POST':
        # Update status
        application.status = 'WITHDRAWN'
        application.save()
        
        # Notify employer
        employer_email = application.job.employer.user.email
        subject = "Application Withdrawn"
        body = f"{application.student.user.username} has withdrawn their application for {application.job.title}."
        msg = EmailMultiAlternatives(
            subject=subject,
            body=body,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@skillbridge.com"),
            to=[employer_email],
        )
        msg.send(fail_silently=True)
        
        # Optional: Create notification for employer
        Notification.objects.create(
            employer=application.job.employer,
            job=application.job,
            message=f"{application.student.user.username} withdrew their application."
        )
        
        messages.success(request, "Application withdrawn successfully.")
        return redirect('jobs:my_applications')
    
    # GET request: Show confirmation page/modal (handled in template)
    return render(request, 'jobs/withdraw_application.html', {'application': application})

@csrf_protect
@login_required
def assessment_reports(request):
    employer = get_object_or_404(EmployerProfile, user=request.user)
    reports = Report.objects.filter(assessment__application__job__employer=employer).order_by('-assessment__submitted_at')
    
    context = {
        'employer': employer,
        'reports': reports,
    }
    return render(request, 'jobs/assessment_reports.html', context)

# jobs/views.py

# @login_required
# def settings_view(request):
#     if not hasattr(request.user, 'studentprofile'):
#         messages.error(request, "Settings are available for student accounts.")
#         return redirect('jobs:job_list')

#     sp = request.user.studentprofile
#     settings_obj, _ = UserSettings.objects.get_or_create(student=sp)

#     if not settings_obj.calendar_token:
#         settings_obj.calendar_token = uuid.uuid4()
#         settings_obj.save(update_fields=['calendar_token'])

#     if request.method == 'POST':
#         form = UserSettingsForm(request.POST, instance=settings_obj)
#         if form.is_valid():
#             form.save()
#             messages.success(request, "Settings updated.")
#             return redirect('jobs:settings')
#     else:
#         form = UserSettingsForm(instance=settings_obj)

#     ics_url = request.build_absolute_uri(
#         reverse('jobs:settings_calendar', kwargs={'token': settings_obj.calendar_token})
#     )
#     return render(request, 'jobs/settings.html', {'form': form, 'ics_url': ics_url})


# # jobs/views.py (continued)
# from django.urls import reverse

# def _format_ics_dt(dt):
#     # ICS expects UTC in YYYYMMDDTHHMMSSZ
#     dt_utc = dt.astimezone(timezone.utc)
#     return dt_utc.strftime('%Y%m%dT%H%M%SZ')

# def _escape_ics(text):
#     return (text or '').replace('\\','\\\\').replace(';','\\;').replace(',','\\,').replace('\n','\\n')

# def _fold_ics_line(line, limit=75):
#     # Fold long lines per RFC
#     if len(line) <= limit:
#         return line
#     parts = [line[i:i+limit] for i in range(0, len(line), limit)]
#     return ("\r\n ".join(parts))

# def _ics(*lines):
#     # minimal ICS builder
#     return "\r\n".join(lines) + "\r\n"

# def _student_by_calendar_token(token):
#     try:
#         settings_obj = UserSettings.objects.select_related('student__user').get(calendar_token=token)
#         return settings_obj.student
#     except UserSettings.DoesNotExist:
#         return None

# def _interviews_for_student(student):
#     return Interview.objects.filter(
#         application__student=student,
#         status='SCHEDULED',
#         interview_date__gte=timezone.now() - timezone.timedelta(days=180)
#     ).select_related('application__job__employer')

# def _vevent_for_interview(iv):
#     job = iv.application.job
#     summary = f"Interview: {job.title} @ {job.employer.company_name}"
#     desc = f"Type: {iv.get_interview_type_display()}"
#     if iv.details:
#         desc += f" | Details: {iv.details}"
#     uid = f"skillbridge-{iv.pk}@example"  # make unique, domain can be your site
#     lines = [
#         "BEGIN:VEVENT",
#         f"UID:{uid}",
#         f"DTSTAMP:{_format_ics_dt(timezone.now())}",
#         f"DTSTART:{_format_ics_dt(iv.interview_date)}",
#         f"DTEND:{_format_ics_dt(iv.interview_date + timezone.timedelta(minutes=30))}",
#         _fold_ics_line(f"SUMMARY:{_escape_ics(summary)}"),
#         _fold_ics_line(f"DESCRIPTION:{_escape_ics(desc)}"),
#         _fold_ics_line(f"LOCATION:{_escape_ics(getattr(iv, 'location', '') or job.location)}"),
#         "END:VEVENT",
#     ]
#     return _ics(*lines)

# from uuid import UUID

# def settings_calendar(request, token):
#     # /jobs/settings/calendar/<uuid>.ics
#     try:
#         UUID(str(token))
#     except Exception:
#         raise Http404()

#     student = _student_by_calendar_token(token)
#     if not student:
#         raise Http404()

#     events = "".join(_vevent_for_interview(iv) for iv in _interviews_for_student(student))
#     body = _ics(
#         "BEGIN:VCALENDAR",
#         "VERSION:2.0",
#         "PRODID:-//SkillBridge//Student Interviews//EN",
#         "CALSCALE:GREGORIAN",
#         events,
#         "END:VCALENDAR"
#     )
#     return HttpResponse(body, content_type="text/calendar")
import time
from datetime import datetime, timedelta
from django.core.files.storage import default_storage
from django.contrib.staticfiles.storage import staticfiles_storage

def cache_busted_media_url(filefield, fallback_static_path):
    """
    Return filefield.url with ?v=<mtime> if exists; otherwise a static fallback.
    """
    if filefield and getattr(filefield, 'name', None) and default_storage.exists(filefield.name):
        try:
            mtime = int(default_storage.get_modified_time(filefield.name).timestamp())
        except Exception:
            mtime = int(time.time())
        return f"{filefield.url}?v={mtime}"
    return staticfiles_storage.url(fallback_static_path)









