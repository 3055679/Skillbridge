from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from django.contrib import messages
from django.utils import timezone
from accounts.models import StudentProfile, EmployerProfile
from .models import Job, Application, Interview
from .forms import ApplicationForm, JobForm, InterviewForm

@csrf_protect
@login_required
def student_dashboard(request):
    try:
        student = request.user.studentprofile
    except StudentProfile.DoesNotExist:
        student = StudentProfile.objects.create(user=request.user)
        messages.warning(request, 'Please complete your profile to get started.')
    
    applications = Application.objects.filter(student=student)
    total_applications = applications.count()
    interviews = applications.filter(status='INTERVIEW').count()
    pending = applications.filter(status='PENDING').count()
    rejected = applications.filter(status='REJECTED').count()
    
    recent_applications = applications.order_by('-applied_date')[:3]
    
    upcoming_interviews = Interview.objects.filter(
        application__student=student,
        interview_date__gte=timezone.now()
    ).order_by('interview_date')[:2]
    
    recommended_jobs = Job.objects.filter(
        is_active=True,
        application_deadline__gt=timezone.now()
    ).order_by('-posted_date')[:3]
    
    context = {
        'student': student,
        'total_applications': total_applications,
        'interviews': interviews,
        'pending': pending,
        'rejected': rejected,
        'recent_applications': recent_applications,
        'upcoming_interviews': upcoming_interviews,
        'recommended_jobs': recommended_jobs,
    }
    return render(request, 'jobs/student_dashboard.html', context)

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
        messages.error(request, f"Please complete the following required fields in your profile: {', '.join(missing_fields)}")
        return redirect('accounts:student_profile')
    
    if request.method == 'POST':
        form = ApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            application = form.save(commit=False)
            application.student = profile
            application.job = job
            application.save()
            messages.success(request, 'Application submitted successfully.')
            return redirect('jobs:my_applications')
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
    
    context = {
        'employer': employer,
        'jobs': jobs,
        'applications': applications,
    }
    return render(request, 'jobs/employer_dashboard.html', context)

@csrf_protect
@login_required
def post_job(request):
    try:
        employer = request.user.employerprofile
    except EmployerProfile.DoesNotExist:
        messages.error(request, 'Please complete your employer profile.')
        return redirect('accounts:employer_profile')
       
    if request.method == 'POST':
        form = JobForm(request.POST)
        if form.is_valid():
            job = form.save(commit=False)
            job.employer = employer
            job.is_active = True
            job.posted_date = timezone.now()
            job.save()
            messages.success(request, 'Job posted successfully!')
            return redirect('jobs:employer_dashboard')
    else:
        form = JobForm()
       
    return render(request, 'jobs/post_job.html', {'form': form})

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
def manage_application(request, application_id):
    application = get_object_or_404(Application, pk=application_id, job__employer__user=request.user)
    if request.method == 'POST':
        status = request.POST.get('status')
        if status in [choice[0] for choice in Application.STATUS_CHOICES]:
            application.status = status
            application.save()
            messages.success(request, f'Application status updated to {application.get_status_display()}')
            return redirect('jobs:employer_dashboard')
    
    return render(request, 'jobs/manage_application.html', {'application': application})

@csrf_protect
@login_required
def schedule_interview(request, application_id):
    application = get_object_or_404(Application, pk=application_id, job__employer__user=request.user)
    if request.method == 'POST':
        form = InterviewForm(request.POST)
        if form.is_valid():
            interview = form.save(commit=False)
            interview.application = application
            interview.save()
            application.status = 'INTERVIEW'
            application.save()
            messages.success(request, 'Interview scheduled successfully!')
            return redirect('jobs:employer_dashboard')
    else:
        form = InterviewForm()
    
    return render(request, 'jobs/schedule_interview.html', {'form': form, 'application': application})

def job_list(request):
    jobs = Job.objects.filter(is_active=True).order_by('-posted_date')
    context = {
        'jobs': jobs,
    }
    return render(request, 'jobs/job_list.html', context)

def job_detail(request, pk):
    job = get_object_or_404(Job, id=pk)
    is_closed = not job.is_accepting_applications()
    return render(request, 'jobs/job_detail.html', {
        'job': job,
        'is_closed': is_closed,
    })

@csrf_protect
@login_required
def application_detail(request, application_id):
    application = get_object_or_404(Application, pk=application_id)
    if request.user.is_student and application.student.user != request.user:
        messages.error(request, "You can only view your own applications.")
        return redirect('jobs:student_dashboard')
    elif request.user.is_employer and application.job.employer.user != request.user:
        messages.error(request, "You can only view applications for your jobs.")
        return redirect('jobs:employer_dashboard')
    return render(request, 'jobs/application_detail.html', {'application': application})