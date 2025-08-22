from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator

User = get_user_model()

# Reuse your Skill model from accounts (adjust path if different)
from accounts.models import Skill
# Reuse your Job/Application/Gig if you have Gig (adjust path if different)
from jobs.models import Job, Application  # Gig optional; import when you add it

class RoleProfile(models.Model):
    """For Gigs (e.g., designer, video_editor, web_developer)."""
    key = models.SlugField(unique=True)
    name = models.CharField(max_length=64)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

class AssessmentBlueprint(models.Model):
    """Rules defining sections and weights."""
    KIND_CHOICES = [("internship", "Internship"), ("gig", "Gig")]
    name = models.CharField(max_length=128)
    kind = models.CharField(max_length=16, choices=KIND_CHOICES)
    role = models.ForeignKey(RoleProfile, null=True, blank=True, on_delete=models.SET_NULL)
    rules = models.JSONField()  # see examples in fixtures/seed
    duration_minutes = models.PositiveIntegerField(
        default=60, validators=[MinValueValidator(10), MaxValueValidator(240)]
    )

    def __str__(self):
        return f"{self.kind}: {self.name}"

class Question(models.Model):
    QTYPE = [("mcq","MCQ"), ("short","Short"), ("code","Code")]
    text = models.TextField()
    qtype = models.CharField(max_length=8, choices=QTYPE)
    skills = models.ManyToManyField(Skill, blank=True)
    difficulty = models.IntegerField(default=1, validators=[MinValueValidator(1), MaxValueValidator(3)])
    # MCQ
    choices = models.JSONField(null=True, blank=True)  # [{"key":"A","text":"..."}, ...]
    answer_key = models.CharField(max_length=8, blank=True)
    # Code
    language = models.CharField(max_length=32, blank=True)
    starter_code = models.TextField(blank=True)
    tests = models.JSONField(null=True, blank=True)
    section = models.CharField(max_length=24, default="technical")  # technical/hr/aptitude
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"[{self.qtype}] {self.text[:60]}"

class Task(models.Model):
    """Gig artifacts (uploads/critique) that don’t fit Question."""
    TTYPE = [("upload","Upload"), ("critique","Critique")]
    role = models.ForeignKey(RoleProfile, on_delete=models.CASCADE)
    title = models.CharField(max_length=160)
    instructions = models.TextField()
    ttype = models.CharField(max_length=16, choices=TTYPE)
    skills = models.ManyToManyField(Skill, blank=True)
    artifact_type = models.CharField(max_length=24, blank=True)  # image/video/link/code/pdf
    rubric = models.JSONField(null=True, blank=True)
    max_score = models.IntegerField(default=10)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.role.name}: {self.title}"

class Assessment(models.Model):
    """Frozen questions/tasks for a specific application."""
    application = models.OneToOneField(Application, on_delete=models.CASCADE, related_name="assessment")
    blueprint = models.ForeignKey(AssessmentBlueprint, on_delete=models.PROTECT)
    questions = models.JSONField()  # frozen list of questions (dicts)
    tasks = models.JSONField(null=True, blank=True)  # frozen list of tasks (dicts)
    token = models.CharField(max_length=64, unique=True)
    duration_minutes = models.PositiveIntegerField(default=60)
    status = models.CharField(max_length=24, default="invited")  # invited, started, submitted, scored
    started_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

class Response(models.Model):
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name="responses")
    ref_type = models.CharField(max_length=8, default="q")  # q=Question, t=Task
    ref_id = models.IntegerField()  # original Question/Task id
    answer = models.JSONField()     # "B" / text / code / file refs / links
    is_correct = models.BooleanField(null=True)
    score = models.FloatField(default=0.0)

class Report(models.Model):
    assessment = models.OneToOneField(Assessment, on_delete=models.CASCADE)
    total_score = models.FloatField()
    per_skill = models.JSONField()
    per_section = models.JSONField(default=dict)
    summary = models.TextField()
    pdf_path = models.CharField(max_length=256, blank=True)

# NEW: A separate master list just for assessment selections
class AssessmentSkill(models.Model):
    name = models.CharField(max_length=64, unique=True, db_index=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

# NEW: Link what the user picked at apply-time to their application
class ApplicantChosenSkill(models.Model):
    application = models.ForeignKey("jobs.Application", on_delete=models.CASCADE, related_name="assessment_skills")
    skill = models.ForeignKey(AssessmentSkill, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("application", "skill")

