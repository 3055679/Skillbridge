from django import forms
from .models import Job, Application, Interview

class JobForm(forms.ModelForm):
    requirements = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': 'Example:\n- Proficiency in Python\n- Basic knowledge of Django\n- 2+ years experience'
        }),
        required=False,
        help_text="List the specific skills/requirements for this position"
    )

    class Meta:
        model = Job
        fields = ['title', 'job_type', 'description', 'requirements', 'location', 'salary']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
        }

class ApplicationForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ['cover_letter', 'resume']
        widgets = {
            'cover_letter': forms.Textarea(attrs={'rows': 5}),
        }

class InterviewForm(forms.ModelForm):
    class Meta:
        model = Interview
        fields = ['interview_date', 'interview_type', 'details']
        widgets = {
            'interview_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'details': forms.Textarea(attrs={'rows': 3}),
        }