from django.db import models
from accounts.models import StudentProfile, EmployerProfile
from django.utils import timezone
from datetime import timedelta

class Job(models.Model):
    JOB_TYPE_CHOICES = [
        ('INT', 'Internship'),
        ('GIG', 'Gig'),
    ]
    
    INTERNSHIP_DESCRIPTION = "Long-term work experience (typically 3-6 months)"
    GIG_DESCRIPTION = "Short-term project or task (typically 1 day - 1 month)"
    
    employer = models.ForeignKey(EmployerProfile, on_delete=models.CASCADE, related_name='jobs')
    title = models.CharField(max_length=200)
    description = models.TextField()
    requirements = models.TextField(blank=True, help_text="Enter specific job requirements here")
    location = models.CharField(max_length=100)
    job_type = models.CharField(max_length=3, choices=JOB_TYPE_CHOICES)
    salary = models.CharField(max_length=100, blank=True)
    posted_date = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(default=timezone.now() + timedelta(days=30))

    def __str__(self):
        return f"{self.title} at {self.employer.company_name}"

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=30)
        super().save(*args, **kwargs)

    class Meta:
        indexes = [
            models.Index(fields=['employer', 'posted_date']),
            models.Index(fields=['is_active']),
        ]

class Application(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('INTERVIEW', 'Interview Scheduled'),
        ('ACCEPTED', 'Accepted'),
        ('REJECTED', 'Rejected'),
    ]
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='applications')
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='applications')
    applied_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    cover_letter = models.TextField(blank=True)
    resume = models.FileField(upload_to='application_resumes/', blank=True, null=True)

    def __str__(self):
        return f"{self.student.user.username} - {self.job.title}"

    class Meta:
        unique_together = ('student', 'job')
        indexes = [
            models.Index(fields=['student', 'applied_date']),
            models.Index(fields=['job', 'status']),
        ]

class Interview(models.Model):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='interviews')
    interview_date = models.DateTimeField()
    interview_type = models.CharField(max_length=50, choices=[
        ('ZOOM', 'Zoom Meeting'),
        ('PHONE', 'Phone Call'),
        ('IN_PERSON', 'In-Person'),
    ])
    details = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Interview for {self.application.job.title} with {self.application.student.user.username}"