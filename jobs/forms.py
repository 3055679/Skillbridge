from django import forms
from django.forms import formset_factory
from .models import Application, Interview, Job, JobQuestion
from django.utils import timezone
from .models import Job, Application, Interview, JobQuestion, ProposedInterviewSlot
from django.core.validators import FileExtensionValidator

class JobForm(forms.ModelForm):
    requirements = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': 'Example:\n- Proficiency in Python\n- Basic knowledge of Django\n- 2+ years experience'
        }),
        required=False,
        help_text="List the specific skills/requirements for this position"
    )
    media = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(attrs={'accept': 'image/jpeg,image/png,video/mp4'}),
        help_text="Upload an image or video to showcase your job (JPG, PNG, MP4)"
    )

    class Meta:
        model = Job
        fields = ['title', 'job_type', 'description', 'requirements', 'location', 'salary', 
                 'max_applications', 'application_deadline', 'interview_type', 'location_address', 'media', 'media_type']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
            'application_deadline': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'interview_type': forms.Select(),
            'media_type': forms.Select(choices=(('', 'Select media type'), ('image', 'Image'), ('video', 'Video'))),
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
        media = cleaned_data.get('media')
        media_type = cleaned_data.get('media_type')
        
        if interview_type == 'FACE_TO_FACE' and not location_address:
            raise forms.ValidationError("Location address is required for Face-to-Face interviews.")
        if interview_type == 'DIGITAL' and location_address:
            cleaned_data['location_address'] = None
        if media and not media_type:
            raise forms.ValidationError("Please select a media type (Image or Video).")
        if media_type and not media:
            raise forms.ValidationError("Please upload a file for the selected media type.")
        return cleaned_data

class JobQuestionForm(forms.ModelForm):
    choices = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Enter options, one per line'}),
        required=False,
        help_text="For multiple-choice questions, enter one option per line."
    )

    class Meta:
        model = JobQuestion
        fields = ['question_text', 'question_type', 'choices']
        widgets = {
            'question_text': forms.TextInput(attrs={'placeholder': 'Enter your question'}),
            'question_type': forms.Select(),
        }

    def clean_choices(self):
        choices = self.cleaned_data.get('choices')
        question_type = self.cleaned_data.get('question_type')
        if question_type == 'multiple_choice' and not choices:
            raise forms.ValidationError("Multiple-choice questions require at least one option.")
        if choices:
            choices_list = [choice.strip() for choice in choices.split('\n') if choice.strip()]
            return choices_list
        return []

JobQuestionFormSet = formset_factory(JobQuestionForm, extra=1, can_delete=True)

class ApplicationForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ['cover_letter', 'resume']
        widgets = {
            'cover_letter': forms.Textarea(attrs={'rows': 5}),
        }

class InterviewForm(forms.ModelForm):
    proposed_slots = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Enter proposed slots (one per line, e.g., 2025-08-10 14:00)'}),
        required=False,
        help_text="Enter multiple proposed interview times (one per line)."
    )

    class Meta:
        model = Interview
        fields = ['interview_date', 'interview_type', 'details']
        widgets = {
            'interview_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'details': forms.Textarea(attrs={'rows': 3}),
        }

class MaxApplicationsForm(forms.ModelForm):
    class Meta:
        model = Job
        fields = ['max_applications']
        widgets = {
            'max_applications': forms.NumberInput(attrs={'min': 1}),
        }



# class ResumeForm(forms.Form):
#     # Personal Information
#     first_name = forms.CharField(max_length=100, required=True, label="First Name")
#     last_name = forms.CharField(max_length=100, required=True, label="Last Name")
#     email = forms.EmailField(required=True, label="Email")
#     phone = forms.CharField(max_length=15, required=True, label="Phone Number")
#     address = forms.CharField(max_length=200, required=False, label="Address")
    
#     # Education
#     education = forms.CharField(widget=forms.Textarea, required=True, label="Education (e.g., Degree, University, Year)")
    
#     # Work Experience
#     experience = forms.CharField(widget=forms.Textarea, required=True, label="Work Experience (e.g., Job Title, Company, Dates, Responsibilities)")
    
#     # Skills
#     skills = forms.CharField(widget=forms.Textarea, required=True, label="Skills (one per line)")
    
#     # Optional: Additional Information
#     additional_info = forms.CharField(widget=forms.Textarea, required=False, label="Additional Information (e.g., Certifications, Projects)")


# from django import forms

# class ResumeForm(forms.Form):
#     # Personal Information
#     first_name = forms.CharField(max_length=100, required=True)
#     last_name = forms.CharField(max_length=100, required=True)
#     email = forms.EmailField(required=True)
#     phone = forms.CharField(max_length=20, required=True)
#     address = forms.CharField(widget=forms.Textarea, required=True)
    
#     # Professional Information
#     education = forms.CharField(
#         widget=forms.Textarea,
#         help_text="Enter each education entry on a new line"
#     )
#     experience = forms.CharField(
#         widget=forms.Textarea, 
#         help_text="Enter each experience entry on a new line"
#     )
#     skills = forms.CharField(
#         widget=forms.Textarea,
#         help_text="List each skill on a new line"
#     )
#     additional_info = forms.CharField(
#         widget=forms.Textarea, 
#         required=False,
#         help_text="Optional: Include certifications, projects, etc."
#     )

from django import forms

class ResumeForm(forms.Form):
    # Personal Information
    first_name = forms.CharField(max_length=100, required=True, label="First name")
    last_name  = forms.CharField(max_length=100, required=True, label="Last name")
    email      = forms.EmailField(required=True, label="Email")
    phone      = forms.CharField(max_length=20, required=True, label="Phone")
    address    = forms.CharField(widget=forms.Textarea, required=True, label="Address")

    # Professional Information
    skills = forms.CharField(
        widget=forms.Textarea,
        help_text="List each skill on a new line",
        required=True,
        label="Skills"
    )
    additional_info = forms.CharField(
        widget=forms.Textarea,
        required=False,
        help_text="Optional: certifications, projects, awards, etc.",
        label="Additional information"
    )

    # Select from profile (limit to 2)
    education_ids = forms.MultipleChoiceField(
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Education (select up to 2)"
    )
    experience_ids = forms.MultipleChoiceField(
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Work experience (select up to 2)"
    )

    # Simple theme choice for the PDF
    theme = forms.ChoiceField(
        choices=[('ats', 'ATS Clean'), ('modern', 'Modern Accent')],
        initial='ats',
        required=True,
        label="Resume theme"
    )

    def __init__(self, *args, user=None, **kwargs):
        """
        Pass the logged-in user as `user=request.user` so we can
        populate choices from their StudentProfile.
        """
        super().__init__(*args, **kwargs)

        sp = getattr(user, 'studentprofile', None)

        # ---------- Education choices ----------
        edu_choices = []
        if sp and hasattr(sp, 'educations'):
            try:
                edu_qs = sp.educations.all().order_by('-start_year')
                for e in edu_qs:
                    # Degree name (via choices)
                    if hasattr(e, 'get_degree_display'):
                        try:
                            degree = e.get_degree_display()
                        except Exception:
                            degree = getattr(e, 'degree', '') or ''
                    else:
                        degree = getattr(e, 'degree', '') or ''

                    fos  = getattr(e, 'field_of_study', '') or ''
                    inst = getattr(e, 'institution', '') or ''
                    sy   = str(getattr(e, 'start_year', '') or '')
                    ey   = 'Present' if bool(getattr(e, 'currently_studying', False)) else str(getattr(e, 'end_year', '') or '')

                    label = f"{degree} in {fos} — {inst} ({sy}–{ey})".strip()
                    edu_choices.append((str(getattr(e, 'id')), label))
            except Exception:
                pass
        self.fields['education_ids'].choices = edu_choices

        # ---------- Experience choices ----------
        def fmt_month(d):
            try:
                return d.strftime('%b %Y') if d else ''
            except Exception:
                return ''

        exp_choices = []
        if sp and hasattr(sp, 'experiences'):
            try:
                exp_qs = sp.experiences.all().order_by('-start_date')
                for x in exp_qs:
                    title = getattr(x, 'title', '') or 'Role'
                    company = getattr(x, 'company', '') or ''
                    sd = fmt_month(getattr(x, 'start_date', None))
                    ed = 'Present' if bool(getattr(x, 'currently_working', False)) else fmt_month(getattr(x, 'end_date', None))
                    label = f"{title} — {company} ({sd}–{ed})".strip()
                    exp_choices.append((str(getattr(x, 'id')), label))
            except Exception:
                pass
        self.fields['experience_ids'].choices = exp_choices

        # ---------- Prefill basics from profile ----------
        if sp and not self.is_bound:
            user_obj = getattr(sp, 'user', None)
            self.fields['first_name'].initial = getattr(user_obj, 'first_name', '') or ''
            self.fields['last_name'].initial  = getattr(user_obj, 'last_name', '') or ''
            # prefer personal_email if present, fallback to auth user email
            self.fields['email'].initial      = getattr(sp, 'personal_email', None) or getattr(user_obj, 'email', '') or ''
            self.fields['phone'].initial      = getattr(sp, 'phone_number', '') or ''
            # compose address from location + country if available
            addr_parts = [p for p in [getattr(sp, 'location', None), getattr(sp, 'country', None)] if p]
            if addr_parts:
                self.fields['address'].initial = ", ".join(addr_parts)

            # Skills prefill from M2M
            if hasattr(sp, 'skills'):
                try:
                    names = [str(getattr(s, 'name', '')).strip() for s in sp.skills.all() if getattr(s, 'name', None)]
                    if names:
                        self.fields['skills'].initial = "\n".join(names)
                except Exception:
                    pass

    # ---------- Validation ----------
    def clean(self):
        cleaned = super().clean()
        edu = cleaned.get('education_ids') or []
        exp = cleaned.get('experience_ids') or []

        # Enforce max selections
        if len(edu) > 2:
            self.add_error('education_ids', "Select at most two education entries.")
        if len(exp) > 2:
            self.add_error('experience_ids', "Select at most two work experiences.")

        # Require at least 1 education
        if len(edu) == 0:
            self.add_error('education_ids', "At least one education entry is required.")

        # Anti-tampering: only allow IDs present in choices
        def _only_valid(selected, fieldname):
            valid_ids = {c[0] for c in self.fields[fieldname].choices}
            return [i for i in selected if i in valid_ids]

        cleaned['education_ids']  = _only_valid(edu, 'education_ids')
        cleaned['experience_ids'] = _only_valid(exp, 'experience_ids')

        return cleaned

