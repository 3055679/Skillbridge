from django import forms
from .models import Application, Interview, Job
from django.utils import timezone

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
        fields = ['title', 'job_type', 'description', 'requirements', 'location', 'salary', 
                 'max_applications', 'application_deadline', 'interview_type', 'location_address']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
            'application_deadline': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'interview_type': forms.Select(),
        }

    def clean_max_applications(self):
        max_applications = self.cleaned_data.get('max_applications')
        if max_applications is not None and max_applications <= 0:
            raise forms.ValidationError("Maximum applications must be a positive number.")
        return max_applications

    def clean_application_deadline(self):
        deadline = self.cleaned_data.get('application_deadline')
        if deadline and deadline < timezone.now():
            raise forms.ValidationError("Application deadline must be in the future.")
        return deadline

    def clean(self):
        cleaned_data = super().clean()
        interview_type = cleaned_data.get('interview_type')
        location_address = cleaned_data.get('location_address')
        
        if interview_type == 'FACE_TO_FACE' and not location_address:
            raise forms.ValidationError("Location address is required for Face-to-Face interviews.")
        if interview_type == 'DIGITAL' and location_address:
            cleaned_data['location_address'] = None  # Clear address for digital interviews
        return cleaned_data

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