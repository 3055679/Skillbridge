import stripe
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.urls import reverse
from django.http import HttpResponseRedirect
from .models import TaskAssignment, Feedback, Payment, TaskSubmission
from .forms import TaskAssignmentForm, FeedbackForm, TaskSubmissionForm
from accounts.models import EmployerProfile, StudentProfile
from jobs.models import Application
from django.utils import timezone

stripe.api_key = settings.STRIPE_SECRET_KEY

@csrf_protect
@login_required
def assign_task(request, application_id):
    application = get_object_or_404(Application, pk=application_id, job__employer__user=request.user, status='ACCEPTED')
    if request.method == 'POST':
        form = TaskAssignmentForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.application = application
            task.save()
            student_email = application.student.user.email
            send_mail(
                subject='Task Assigned',
                message=f'You have been assigned a task for {application.job.title}: {task.task_description}',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[student_email],
                fail_silently=True,
            )
            messages.success(request, 'Task assigned successfully.')
            return redirect('jobs:employer_dashboard')
    else:
        form = TaskAssignmentForm()
    return render(request, 'payment/assign_task.html', {
        'form': form,
        'application': application,
        'is_physical': application.job.is_physical,
    })

@csrf_protect
@login_required
def submit_task(request, task_id):
    task = get_object_or_404(TaskAssignment, pk=task_id, application__student__user=request.user)
    if request.method == 'POST':
        form = TaskSubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            submission = form.save(commit=False)
            submission.task_assignment = task
            submission.student = request.user.studentprofile
            submission.save()
            return redirect('jobs:student_dashboard')
    else:
        form = TaskSubmissionForm()
    return render(request, 'payment/submit_task.html', {'form': form, 'task': task})

@csrf_protect
@login_required
def submit_feedback(request, task_id):
    task = get_object_or_404(TaskAssignment, pk=task_id, application__job__employer__user=request.user)
    if not task.submission:
        messages.error(request, 'Student must submit work before feedback can be provided.')
        return redirect('jobs:employer_dashboard')
    if task.feedback.exists():  # Check for existing feedback
        messages.error(request, 'Feedback already submitted for this task.')
        return redirect('jobs:employer_dashboard')
    if request.method == 'POST':
        form = FeedbackForm(request.POST)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.task_assignment = task
            feedback.save()
            task.completed = True
            task.save()
            if task.application.job.paid_type == 'PAID':
                payment = Payment.objects.create(
                    application=task.application,
                    amount=task.application.job.salary,
                )
                try:
                    charge = stripe.Charge.create(
                        amount=int(payment.amount * 100),
                        currency='usd',
                        source='tok_visa',
                        description=f'Payment for {task.application.job.title}',
                    )
                    payment.stripe_payment_id = charge.id
                    payment.released = True
                    payment.release_date = timezone.now()
                    payment.save()
                    send_mail(
                        subject='Payment Released',
                        message=f'Your payment of ${payment.amount} for {task.application.job.title} has been released.',
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[task.application.student.user.email],
                        fail_silently=True,
                    )
                except stripe.error.StripeError as e:
                    messages.error(request, f'Payment release failed: {str(e)}')
            messages.success(request, 'Feedback submitted and task completed.')
            return redirect('jobs:employer_dashboard')
    else:
        form = FeedbackForm()
    return render(request, 'payment/submit_feedback.html', {'form': form, 'task': task})

@csrf_protect
@login_required
def withdraw_earnings(request):
    student = get_object_or_404(StudentProfile, user=request.user)
    payments = Payment.objects.filter(application__student=student, released=True, withdrawn=False)
    total_earnings = sum(p.amount for p in payments)
    if request.method == 'POST':
        if student.stripe_account_id:
            try:
                transfer = stripe.Transfer.create(
                    amount=int(total_earnings * 100),
                    currency='usd',
                    destination=student.stripe_account_id,
                    description='Earnings withdrawal',
                )
                payments.update(withdrawn=True)
                messages.success(request, 'Earnings withdrawn successfully.')
            except stripe.error.StripeError as e:
                messages.error(request, f'Withdrawal failed: {str(e)}')
        else:
            messages.error(request, 'Add bank details in your profile to withdraw earnings.')
        return redirect('jobs:student_dashboard')
    return render(request, 'payment/withdraw_earnings.html', {'total_earnings': total_earnings})

@csrf_protect
@login_required
def stripe_connect_onboarding(request):
    student = get_object_or_404(StudentProfile, user=request.user)
    if not student.stripe_account_id:
        try:
            account = stripe.Account.create(
                type='express',
                country='US',
                email=request.user.email,
                capabilities={'card_payments': {'requested': True}, 'transfers': {'requested': True}},
            )
            student.stripe_account_id = account.id
            student.save()
        except stripe.error.StripeError as e:
            messages.error(request, f'Failed to create Stripe account: {str(e)}')
            return redirect('jobs:student_dashboard')
    try:
        account_link = stripe.AccountLink.create(
            account=student.stripe_account_id,
            refresh_url=reverse('payment:stripe_connect_onboarding'),
            return_url=reverse('jobs:student_dashboard'),
            type='account_onboarding',
        )
        return HttpResponseRedirect(account_link.url)
    except stripe.error.StripeError as e:
        messages.error(request, f'Onboarding failed: {str(e)}')
        return redirect('jobs:student_dashboard')

@csrf_protect
@login_required
def task_submissions(request):
    if hasattr(request.user, 'employerprofile'):
        assignments = TaskAssignment.objects.filter(application__job__employer__user=request.user).select_related('submission', 'feedback')
        return render(request, 'payment/task_submissions.html', {'assignments': assignments, 'user_type': 'employer'})
    else:
        assignments = TaskAssignment.objects.filter(application__student__user=request.user).select_related('submission', 'feedback')
        return render(request, 'payment/task_submissions.html', {'assignments': assignments, 'user_type': 'student'})