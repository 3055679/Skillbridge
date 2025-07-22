from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.utils.html import mark_safe
from django.contrib.auth.models import User

class User(AbstractUser):
    is_student = models.BooleanField(default=False)
    is_employer = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='userprofile')
    email_verification_token = models.UUIDField(blank=True, null=True)
    email_verified = models.BooleanField(default=False)

class EmployerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    company_name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    phone_regex = RegexValidator(regex=r'^\+?1?\d{9,15}$', message="Phone number must be entered in the format: '+999999999'.")
    phone_number = models.CharField(validators=[phone_regex], max_length=17)
    country = models.CharField(max_length=100)
    company_logo = models.ImageField(upload_to='company_logos/', blank=True, null=True)
    company_website = models.URLField(blank=True)
    company_description = models.TextField(blank=True)
    industry = models.CharField(max_length=100, blank=True)
    founded_year = models.PositiveIntegerField(blank=True, null=True)
    company_size = models.CharField(max_length=50, blank=True)
    headquarters = models.CharField(max_length=100, blank=True)
    is_approved = models.BooleanField(default=False)
    approved_date = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return self.company_name

class Skill(models.Model):
    name = models.CharField(max_length=100, unique=True)
    def __str__(self): return self.name
    class Meta:
        ordering = ['name']

class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE,primary_key=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    profile_picture_url = models.URLField(blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    location = models.CharField(max_length=100, blank=True, null=True)
    github_url = models.URLField(blank=True, null=True)
    personal_website = models.URLField(blank=True, null=True)
    resume = models.FileField(upload_to='resumes/', blank=True, null=True)
    skills = models.ManyToManyField(Skill, blank=True)
    work_preference = models.CharField(max_length=4, choices=[
        ('INT', 'Internship'), ('GIG', 'Gigs'), ('BOTH', 'Both')
    ], blank=True, null=True)
    availability = models.CharField(max_length=10, choices=[
        ('FULL', 'Full-time'), ('PART', 'Part-time'), ('FLEX', 'Flexible')
    ], blank=True, null=True)
    student_id_document = models.FileField(upload_to='student_ids/', blank=True, null=True)
    phone_regex = RegexValidator(regex=r'^\+?1?\d{9,15}$', message="Phone number must be entered in the format: '+999999999'.")
    phone_number = models.CharField(validators=[phone_regex], max_length=17, blank=True, null=True)
    university = models.CharField(max_length=200, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    student_id_verified = models.BooleanField(default=False)
    
    def __str__(self): return self.user.username

    def admin_photo(self):
        if self.profile_picture:
            return mark_safe(f'<img src="{self.profile_picture.url}" width="100" />')
        return "No Image"
    admin_photo.short_description = 'Profile Picture'
    admin_photo.allow_tags = True

    @property
    def profile_picture_url(self):
        if self.profile_picture and hasattr(self.profile_picture, 'url'):
            return self.profile_picture.url
        return '/static/images/default-profile.jpg'

class Education(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='educations')
    institution = models.CharField(max_length=200)
    degree = models.CharField(max_length=100, choices=[
        ('HS', 'High School'), ('BA', 'Bachelor'), ('MA', 'Master'), ('PHD', 'PhD'), ('OTHER', 'Other')
    ])
    field_of_study = models.CharField(max_length=100)
    start_year = models.PositiveIntegerField()
    end_year = models.PositiveIntegerField(blank=True, null=True)
    currently_studying = models.BooleanField(default=False)
    def __str__(self): return f"{self.get_degree_display()} in {self.field_of_study}"

class Experience(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='experiences')
    title = models.CharField(max_length=100)
    company = models.CharField(max_length=200)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    currently_working = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    document = models.FileField(upload_to='experience_docs/', blank=True, null=True)
    def __str__(self): return f"{self.title} at {self.company}"

class PortfolioItem(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='portfolio_items')
    title = models.CharField(max_length=100)
    description = models.TextField()
    media = models.FileField(upload_to='portfolio_media/', blank=True, null=True)
    media_type = models.CharField(max_length=10, choices=[('image', 'Image'), ('video', 'Video'), ('other', 'Other')], blank=True)
    is_certificate = models.BooleanField(default=False)
    def __str__(self): return self.title

class PortfolioImage(models.Model):
    portfolio_item = models.ForeignKey(PortfolioItem, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='portfolio_images/')
    caption = models.CharField(max_length=100, blank=True)

class PortfolioVideo(models.Model):
    portfolio_item = models.ForeignKey(PortfolioItem, on_delete=models.CASCADE)
    video_url = models.URLField()
    caption = models.CharField(max_length=100, blank=True)