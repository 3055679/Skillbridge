from django.db import models
from accounts.models import StudentProfile, EmployerProfile
from django.utils import timezone
from django.core.validators import FileExtensionValidator
from django.conf import settings
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from accounts.models import Skill

class Job(models.Model):
    JOB_TYPE_CHOICES = [
        ('INT', 'Internship'),
        ('GIG', 'Gig'),
    ]
    
    INTERVIEW_TYPE_CHOICES = [
        ('DIGITAL', 'Digital'),
        ('FACE_TO_FACE', 'Face-to-Face'),
    ]

    PAID_CHOICES = [
        ('UNPAID', 'Unpaid'),
        ('PAID', 'Paid'),
    ]
    SALARY_TYPE_CHOICES = [
        ('HOURLY', 'Per Hour'),
        ('DAILY', 'Per Day'),
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
    application_deadline = models.DateTimeField(null=True, blank=True, help_text="Deadline for applications")
    max_applications = models.PositiveIntegerField(null=True, blank=True, help_text="Maximum number of applications allowed")
    interview_type = models.CharField(max_length=20, choices=INTERVIEW_TYPE_CHOICES, default='DIGITAL')
    location_address = models.CharField(max_length=255, null=True, blank=True, help_text="Physical address for Face-to-Face interviews")
    paid_type = models.CharField(max_length=6, choices=PAID_CHOICES, default='UNPAID')
    salary_type = models.CharField(max_length=6, choices=SALARY_TYPE_CHOICES, null=True, blank=True)
    is_physical = models.BooleanField(default=False, help_text="For internships: Check if physical presence required")
    media = models.FileField(
        upload_to='job_media/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'png', 'mp4'])]
    )
    media_type = models.CharField(
        max_length=10,
        choices=(('image', 'Image'), ('video', 'Video')),
        blank=True,
        null=True
    )

    def __str__(self):
        return f"{self.title} at {self.employer.company_name}"

    def is_accepting_applications(self):
        if not self.is_active:
            return False
        if self.application_deadline and self.application_deadline < timezone.now():
            self.is_active = False
            self.save()
            return False
        if self.max_applications:
            current_applications = self.applications.count()
            if current_applications >= self.max_applications:
                Notification.objects.get_or_create(
                    employer=self.employer,
                    job=self,
                    message=f"Job '{self.title}' has reached the maximum applications ({self.max_applications}).",
                    defaults={'created_at': timezone.now()}
                )
                return False
        return True

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
        ('WITHDRAWN', 'Withdrawn'),
    ]
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='applications')
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='applications')
    applied_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    cover_letter = models.TextField(blank=True)
    resume = models.FileField(upload_to='application_resumes/', blank=True, null=True)
    declared_skills = models.ManyToManyField(Skill, blank=True, related_name="applications_declared")

    def __str__(self):
        return f"{self.student.user.username} - {self.job.title}"

    class Meta:
        unique_together = ('student', 'job')
        indexes = [
            models.Index(fields=['student', 'applied_date']),
            models.Index(fields=['job', 'status']),
        ]

class Interview(models.Model):
    STATUS_CHOICES = [
        ('SCHEDULED', 'Scheduled'),
        ('CANCELED', 'Canceled'),
    ]
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='interviews')
    interview_date = models.DateTimeField()
    interview_type = models.CharField(max_length=50, choices=[
        ('ZOOM', 'Zoom Meeting'),
        ('PHONE', 'Phone Call'),
        ('IN_PERSON', 'In-Person'),
    ])
    details = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SCHEDULED')

    def __str__(self):
        return f"Interview for {self.application.job.title} with {self.application.student.user.username}"

class JobQuestion(models.Model):
    QUESTION_TYPE_CHOICES = [
        ('text', 'Text'),
        ('multiple_choice', 'Multiple Choice'),
    ]
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='questions')
    question_text = models.CharField(max_length=500)
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPE_CHOICES)
    choices = models.JSONField(blank=True, null=True)  # e.g., ["Option 1", "Option 2"]

    def __str__(self):
        return f"{self.question_text} for {self.job.title}"

class ApplicationResponse(models.Model):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='responses')
    question = models.ForeignKey(JobQuestion, on_delete=models.CASCADE)
    response = models.TextField()

    def __str__(self):
        return f"Response to '{self.question.question_text}' for {self.application}"

class ProposedInterviewSlot(models.Model):
    interview = models.ForeignKey(Interview, on_delete=models.CASCADE, related_name='proposed_slots')
    slot_time = models.DateTimeField()
    is_selected = models.BooleanField(default=False)

    def __str__(self):
        return f"Slot at {self.slot_time} for {self.interview}"

class Notification(models.Model):
    employer = models.ForeignKey(EmployerProfile, on_delete=models.CASCADE, related_name='notifications')
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"Notification for {self.employer.company_name}: {self.message}"
    
# ---------- Saved Jobs ----------
class SavedJob(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='saved_jobs')
    job = models.ForeignKey('Job', on_delete=models.CASCADE, related_name='saved_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'job')
        indexes = [
            models.Index(fields=['student', '-created_at']),
        ]

    def __str__(self):
        return f"{self.student.user.username} saved {self.job.title}"

# ---------- Community (Q&A) ----------
class CommunityQuestion(models.Model):
    author = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='questions')
    title = models.CharField(max_length=200)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    votes = GenericRelation('Vote', related_query_name='q_votes')
    reports = GenericRelation('AbuseReport', related_query_name='q_reports')

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['-created_at'])]

    def __str__(self):
        return self.title

    @property
    def score(self):
        return self.votes.aggregate(s=Coalesce(Sum('value'), 0))['s'] or 0

class CommunityAnswer(models.Model):
    question = models.ForeignKey(CommunityQuestion, on_delete=models.CASCADE, related_name='answers')
    author = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='answers')
    body = models.TextField()
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies')
    created_at = models.DateTimeField(auto_now_add=True)
    votes = GenericRelation('Vote', related_query_name='a_votes')
    reports = GenericRelation('AbuseReport', related_query_name='a_reports')

    class Meta:
        ordering = ['created_at']
        indexes = [models.Index(fields=['question', 'created_at'])]

    def __str__(self):
        return f"Answer by {self.author.user.username}"

    @property
    def score(self):
        return self.votes.aggregate(s=Coalesce(Sum('value'), 0))['s'] or 0

# ---------- Generic Vote (for Question/Answer) ----------
class Vote(models.Model):
    UPVOTE = 1
    DOWNVOTE = -1
    value = models.SmallIntegerField(choices=((UPVOTE, 'Upvote'), (DOWNVOTE, 'Downvote')))
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='votes')
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'content_type', 'object_id')
        indexes = [models.Index(fields=['content_type', 'object_id'])]

    def __str__(self):
        return f"{self.user} voted {self.value} on {self.content_type}:{self.object_id}"

# ---------- Abuse Reports (for moderation) ----------
class AbuseReport(models.Model):
    STATUS = (('OPEN', 'Open'), ('RESOLVED', 'Resolved'))
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reports')
    reason = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS, default='OPEN')
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['status', '-created_at'])]

    def __str__(self):
        return f"Report by {self.reporter} on {self.content_type}:{self.object_id}"

# ---------- User Settings ----------
class UserSettings(models.Model):
    student = models.OneToOneField(StudentProfile, on_delete=models.CASCADE, related_name='settings')
    # Notifications
    notify_job_updates = models.BooleanField(default=True)
    notify_interviews = models.BooleanField(default=True)
    notify_community_replies = models.BooleanField(default=True)
    weekly_digest = models.BooleanField(default=False)
    # Privacy
    show_profile_to_employers = models.BooleanField(default=True)
    show_resume_to_employers = models.BooleanField(default=True)
    # UI
    dark_mode = models.BooleanField(default=False)

     # -------- NEW (APPEARANCE-ONLY) FIELDS --------
    THEME_CHOICES = [('auto', 'Auto'), ('light', 'Light'), ('dark', 'Dark')]
    theme = models.CharField(max_length=10, choices=THEME_CHOICES, default='auto', blank=True)

    FONT_CHOICES = [('sm', 'Small'), ('md', 'Medium'), ('lg', 'Large')]
    font_size = models.CharField(max_length=2, choices=FONT_CHOICES, default='md', blank=True)

    reduced_motion = models.BooleanField(default=False)     # prefer fewer animations
    high_contrast = models.BooleanField(default=False)      # accessibility
    compact_mode = models.BooleanField(default=False)       # tighter paddings
    language = models.CharField(max_length=10, default='en', blank=True)

    def __str__(self):
        return f"Settings for {self.student.user.username}"

# jobs/models.py
# import uuid

# class UserSettings(models.Model):
#     # THEME_CHOICES = [('light', 'Light'), ('dark', 'Dark'), ('auto', 'Auto')]
#     # ALERT_FREQ = [('never', 'Never'), ('daily', 'Daily'), ('weekly', 'Weekly')]

#     student = models.OneToOneField(
#         StudentProfile, on_delete=models.CASCADE, related_name='settings'
#     )

#     # Notifications
#     notify_job_updates = models.BooleanField(default=True)
#     notify_interviews = models.BooleanField(default=True)
#     notify_community_replies = models.BooleanField(default=True)
#     weekly_digest = models.BooleanField(default=False)

#     # Privacy
#     show_profile_to_employers = models.BooleanField(default=True)
#     show_resume_to_employers = models.BooleanField(default=True)

#     # UI
#     dark_mode = models.BooleanField(default=False)

#     # ---------- NEW ADDITIVE FIELDS ----------
#     # Appearance / Timezone
#     THEME_CHOICES = [('light', 'Light'), ('dark', 'Dark'), ('auto', 'Auto')]
#     theme = models.CharField(max_length=10, choices=THEME_CHOICES, default='auto')
#     timezone = models.CharField(max_length=64, default='UTC')

#     # Recommendations (stored as CSV for simplicity)
#     preferred_job_types_csv = models.CharField(max_length=64, blank=True, default='')   # e.g. "INT,GIG"
#     preferred_locations_csv = models.CharField(max_length=255, blank=True, default='') # e.g. "Glasgow, Remote"
#     min_salary = models.PositiveIntegerField(null=True, blank=True)
#     keywords = models.CharField(max_length=255, blank=True, default='')                # e.g. "python, django"

#     # Resume defaults
#     RESUME_TEMPLATES = [('ats','ATS'), ('modern','Modern'), ('classic','Classic')]
#     resume_template = models.CharField(max_length=16, choices=RESUME_TEMPLATES, default='ats')
#     resume_include_photo = models.BooleanField(default=False)
#     auto_attach_resume_on_apply = models.BooleanField(default=True)

#     # Extra privacy
#     portfolio_public = models.BooleanField(default=True)

#     # Private calendar feed for interviews
#     # calendar_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
#     calendar_token = models.UUIDField(null=True, editable=False, unique=True)


#     # ---------- Helpers for CSV fields ----------
#     def job_types_list(self):
#         return [x.strip() for x in self.preferred_job_types_csv.split(',') if x.strip()]

#     def locations_list(self):
#         return [x.strip() for x in self.preferred_locations_csv.split(',') if x.strip()]

#     def keywords_list(self):
#         return [x.strip() for x in self.keywords.split(',') if x.strip()]

#     def __str__(self):
#         username = getattr(getattr(self.student, 'user', None), 'username', 'unknown')
#         return f"Settings for {username}"
