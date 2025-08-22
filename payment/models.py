from django.db import models
from django.utils import timezone
from jobs.models import Application
from decimal import Decimal
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings

class TaskAssignment(models.Model):
    application = models.OneToOneField(Application, on_delete=models.CASCADE, related_name='task_assignment')
    task_description = models.TextField(help_text="Describe the task or internship duties")
    due_date = models.DateField(null=True, blank=True)
    assigned_date = models.DateTimeField(default=timezone.now)
    completed = models.BooleanField(default=False)

    def __str__(self):
        return f"Task for {self.application.job.title}"

class TaskSubmission(models.Model):
    task_assignment = models.OneToOneField(TaskAssignment, on_delete=models.CASCADE, related_name='submission')
    work_file = models.FileField(upload_to='task_submissions/', blank=True, null=True, help_text="Upload your work file")
    description = models.TextField(help_text="Describe tools, technologies, or details of your work")
    submitted_date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Submission for {self.task_assignment.application.job.title}"

class Feedback(models.Model):
    task_assignment = models.OneToOneField(TaskAssignment, on_delete=models.CASCADE, related_name='feedback')
    task_given = models.TextField(help_text="What was the task given?")
    performance = models.TextField(help_text="How did the student perform?")
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)], help_text="Rating out of 5")
    submitted_date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Feedback for {self.task_assignment.application.job.title}"

class Payment(models.Model):
    application = models.OneToOneField(Application, on_delete=models.CASCADE, related_name='payment')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    released = models.BooleanField(default=False)
    release_date = models.DateTimeField(null=True, blank=True)
    stripe_payment_id = models.CharField(max_length=255, blank=True)
    withdrawn = models.BooleanField(default=False)

    def __str__(self):
        return f"Payment for {self.application.job.title} - {self.amount}"
    
@receiver(post_save, sender=TaskSubmission)
def notify_employer_on_submission(sender, instance, created, **kwargs):
    if created:
        task = instance.task_assignment
        employer_email = task.application.job.employer.user.email
        student_username = task.application.student.user.username
        send_mail(
            subject='New Task Submission',
            message=f'{student_username} has submitted work for the task in {task.application.job.title}. Review and provide feedback.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[employer_email],
            fail_silently=True,
        )