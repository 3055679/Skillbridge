import re
from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, PasswordChangeForm, PasswordResetForm
from django.forms import ModelForm, inlineformset_factory
from django.core.validators import validate_email, FileExtensionValidator, RegexValidator
from django.core.exceptions import ValidationError
from .models import  StudentProfile, EmployerProfile, Skill, Education, Experience, PortfolioItem
from django.contrib.auth import get_user_model
User = get_user_model()

class StudentSignUpForm(UserCreationForm):
    first_name = forms.CharField(max_length=100, required=True)
    last_name = forms.CharField(max_length=100, required=True)
    personal_email = forms.EmailField(required=True)
    phone_number = forms.CharField(
        max_length=13,
        required=True,
        label='Phone Number',
        validators=[RegexValidator(
        regex=r'^\+\d{12}$',
        message="Phone number must be in the format: '+CCXXXXXXXXXX' (2-digit country code + 10-digit number)."
    )]
    )
    country = forms.CharField(max_length=100, required=True)
    university = forms.CharField(max_length=200, required=True)
    has_university_email = forms.BooleanField(
        required=False,
        initial=False,
        label="Do you have a university email address?"
    )
    university_email = forms.EmailField(required=False)
    student_id_document = forms.FileField(
        required=False,
        label="Upload Student ID (PDF or Image)",
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])]
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'personal_email', 'phone_number', 'country', 
                 'university', 'has_university_email', 'university_email', 'student_id_document', 
                 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        email_verified = kwargs.pop('email_verified', False)
        super().__init__(*args, **kwargs)
        if email_verified:
            self.fields['university_email'].disabled = True
            self.fields['student_id_document'].required = False
            self.fields['password1'].required = False
            self.fields['password2'].required = False
            self.fields['password1'].validators.append(PasswordValidator.validate_password)
            self.fields['password2'].validators.append(PasswordValidator.validate_password)

    def clean(self):
        cleaned_data = super().clean()
        university_email = cleaned_data.get('university_email')
        personal_email = cleaned_data.get('personal_email')
        has_university_email = cleaned_data.get('has_university_email')

        # Check for duplicate emails
        if personal_email and User.objects.filter(email=personal_email).exists():
            raise ValidationError("This personal email is already registered. Please use a different email or log in.")
        if university_email and User.objects.filter(email=university_email).exists():
            raise ValidationError("This university email is already registered. Please use a different email or log in.")

        # # Existing validations
        # if has_university_email and not university_email:
        #     raise ValidationError("Please provide a university email if you selected that option.")
        # if not has_university_email and not cleaned_data.get('student_id_document'):
        #     raise ValidationError("Please upload a student ID document if you do not have a university email.")
        # if university_email and not (university_email.endswith('.edu') or '@student.gla.ac.uk' in university_email):
        #     raise ValidationError("Please provide a valid .edu or @student.gla.ac.uk email address.")

        
        # Validate university email
        if has_university_email and not university_email:
            raise ValidationError("Please provide a university email if you selected that option.")
        if university_email and not (
            university_email.endswith('.edu') or 
            university_email.endswith('.ac.uk') or 
            '@student.gla.ac.uk' in university_email
        ):
            raise ValidationError("University email must end with .edu, .ac.uk, or be a valid university domain (e.g., @student.gla.ac.uk).")

        # Validate student ID requirement
        if not has_university_email and not cleaned_data.get('student_id_document'):
            raise ValidationError("Please upload a student ID document if you do not have a university email.")
        
        return cleaned_data
    


class EmployerSignUpForm(UserCreationForm):
    company_name = forms.CharField(max_length=200, required=True)
    email = forms.EmailField(required=True)
    phone_number = forms.CharField(
    max_length=14,
    required=True,
    label='Phone Number',
    validators=[RegexValidator(
        regex=r'^\+[1-9]\d{0,2}\d{10}$',
        message="Phone number must be in the format: '+<1-3 digit country code><10-digit number>' (e.g., +12025550123 or +447911123456)."
    )]
)
    country = forms.CharField(max_length=100, required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'phone_number', 'country', 'company_name', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].validators.append(PasswordValidator.validate_password)
        self.fields['password2'].validators.append(PasswordValidator.validate_password)

    # def clean(self):
    #     cleaned_data = super().clean()
    #     email = cleaned_data.get('email')
    #     if email:
    #         if User.objects.filter(email=email).exists():
    #             raise ValidationError("This email is already registered. Please use a different email or log in.")
    #         if EmployerProfile.objects.filter(email=email).exists():
    #             raise ValidationError("This email is already registered with an employer profile. Please use a different email.")
    #     return cleaned_data

    def clean_email(self):
        email = self.cleaned_data['email']
        free_domains = [
            'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com',
            'icloud.com', 'protonmail.com', 'mail.com', 'zoho.com', 'gmx.com',
            'yandex.com', 'live.com', 'msn.com', 'inbox.com', 'rocketmail.com'
        ]
        domain = email.split('@')[-1].lower()
        if domain in free_domains:
            raise ValidationError(
                "Please use a business or institutional email address, not a free service like Gmail, Yahoo, or Hotmail."
            )
        # Allow common educational domains or patterns
        educational_patterns = [
            r'\.edu$', r'\.ac\.[a-z]{2}$',  # e.g., .edu, .ac.uk
        ]
        is_educational = any(re.search(pattern, domain) for pattern in educational_patterns)
        # Optional: Add specific university domains if needed
        educational_domains = [
            'harvard.edu', 'mit.edu', 'stanford.edu', 'ox.ac.uk', 'cam.ac.uk'
        ]
        if domain not in free_domains and (is_educational or domain not in educational_domains):
            # Business or educational email, proceed with uniqueness check
            if User.objects.filter(email=email).exists():
                raise ValidationError("This email is already registered. Please use a different email or log in.")
            if EmployerProfile.objects.filter(email=email).exists():
                raise ValidationError("This email is already registered with an employer profile. Please use a different email.")
        return email

class LoginForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)

class EmployerProfileForm(forms.ModelForm):
    class Meta:
        model = EmployerProfile
        fields = ['company_name', 'phone_number', 'country', 'company_logo',
                 'company_website', 'company_description', 'industry',
                 'founded_year', 'company_size', 'headquarters']
        widgets = {
            'company_description': forms.Textarea(attrs={'rows': 3}),
        }

        widgets = {
            "phone_number": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter your company phone number",
                "data-bs-toggle": "tooltip",
                "data-bs-placement": "right",
                "title": "Enter your company phone number",
            }),
            "company_description": forms.Textarea(attrs={
                "rows": 3,
                "class": "form-control",
                "placeholder": "Describe your company in a few words",
                "data-bs-toggle": "tooltip",
                "data-bs-placement": "right",
                "title": "Describe your company in a few words",
            }),
            "company_website": forms.URLInput(attrs={
                "class": "form-control",
                "placeholder": "Type your official website (e.g., https://example.com)",
                "data-bs-toggle": "tooltip",
                "data-bs-placement": "right",
                "title": "Type your official website",
            }),
            "industry": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g., Information Technology",
                "data-bs-toggle": "tooltip",
                "data-bs-placement": "right",
                "title": "Select/enter your industry",
            }),
            "founded_year": forms.NumberInput(attrs={
                "class": "form-control",
                "placeholder": "e.g., 2016",
                "min": 1800, "max": 2100,
                "data-bs-toggle": "tooltip",
                "data-bs-placement": "right",
                "title": "Enter the year your company was founded",
            }),
            "company_size": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g., 11-50 employees",
                "data-bs-toggle": "tooltip",
                "data-bs-placement": "right",
                "title": "Enter your company size",
            }),
            "company_name": forms.TextInput(attrs={"class": "form-control"}),
            "country": forms.TextInput(attrs={"class": "form-control"}),
            "headquarters": forms.TextInput(attrs={"class": "form-control"}),
            "company_logo": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Make these fields REQUIRED at the form level
        required_fields = [
            "company_website",
            "company_description",
            "industry",
            "founded_year",
            "company_size",
        ]
        for f in required_fields:
            if f in self.fields:
                self.fields[f].required = True

class UserUpdateForm(UserChangeForm):
    email = forms.EmailField()
    password = None

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Disable username and email fields
        self.fields['username'].disabled = True
        self.fields['email'].disabled = True

        # Apply tooltips only for employers
        if self.instance and hasattr(self.instance, 'is_employer') and self.instance.is_employer:
            self.fields["first_name"].widget.attrs.update({
                "class": "form-control",
                "placeholder": "e.g., Priya",
                "data-bs-toggle": "tooltip",
                "data-bs-placement": "right",
                "title": "Write the name of the Company HR",
            })
            self.fields["last_name"].widget.attrs.update({
                "class": "form-control",
                "placeholder": "e.g., Sharma",
                "data-bs-toggle": "tooltip",
                "data-bs-placement": "right",
                "title": "Write the name of the Company HR",
            })
        else:
            # For non-employers (e.g., students), apply default attributes without tooltips
            self.fields["first_name"].widget.attrs.update({
                "class": "form-control",
                "placeholder": "e.g., Priya",
            })
            self.fields["last_name"].widget.attrs.update({
                "class": "form-control",
                "placeholder": "e.g., Sharma",
            })

class StudentProfileForm(ModelForm):
    new_skill = forms.CharField(required=False, widget=forms.TextInput(attrs={'placeholder': 'Add new skill'}))
    class Meta:
        model = StudentProfile
        fields = [
            'phone_number', 'bio', 'location', 'profile_picture', 'github_url',
            'personal_website', 'resume', 'skills', 'work_preference',
            'availability', 'student_id_document', 'university', 'country'
        ]
        widgets = {
            'phone_number': forms.TextInput(attrs={'required': True}),
            'work_preference': forms.RadioSelect(attrs={'required': True}),
            'availability': forms.RadioSelect(attrs={'required': True}),
            'student_id_document': forms.FileInput(attrs={'required': False}),
            'skills': forms.SelectMultiple(attrs={'required': True, 'class': 'select2-skills'}),
            'university': forms.TextInput(attrs={'required': True}),
            'country': forms.TextInput(attrs={'required': True}),
        }


class EducationForm(ModelForm):
    class Meta:
        model = Education
        fields = ['institution', 'degree', 'field_of_study', 'start_year', 'end_year', 'currently_studying']
        widgets = {
            'institution': forms.TextInput(attrs={'required': True}),
            'degree': forms.Select(attrs={'required': True}),
            'field_of_study': forms.TextInput(attrs={'required': True}),
            'start_year': forms.NumberInput(attrs={'required': True}),
            'end_year': forms.NumberInput(attrs={'required': False}),
        }

        

class ExperienceForm(ModelForm):
    class Meta:
        model = Experience
        fields = ['title', 'company', 'start_date', 'end_date', 'currently_working', 'description', 'document']
        widgets = {
            'title': forms.TextInput(attrs={'required': True}),
            'company': forms.TextInput(attrs={'required': True}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'required': True}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'document': forms.FileInput(attrs={'required': False}),
        }

       

class PortfolioForm(ModelForm):
    class Meta:
        model = PortfolioItem
        fields = ['title', 'description', 'media', 'media_type', 'is_certificate']
        widgets = {
            'title': forms.TextInput(attrs={'required': True}),
            'description': forms.Textarea(attrs={'required': True}),
            'media': forms.FileInput(attrs={'required': True}),
            'media_type': forms.Select(attrs={'required': True}),
        }

       

EducationFormSet = inlineformset_factory(StudentProfile, Education, form=EducationForm, extra=1, can_delete=True)
ExperienceFormSet = inlineformset_factory(StudentProfile, Experience, form=ExperienceForm, extra=1, can_delete=True)
PortfolioFormSet = inlineformset_factory(StudentProfile, PortfolioItem, form=PortfolioForm, extra=1, can_delete=True)

class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
            self.fields['new_password1'].validators.append(PasswordValidator.validate_password)
            self.fields['new_password2'].validators.append(PasswordValidator.validate_password)




class CustomPasswordResetForm(PasswordResetForm):
    username = forms.CharField(max_length=150, required=True)

    def clean(self):
        cleaned = super().clean()
        username = cleaned.get('username', '').strip()
        email    = cleaned.get('email', '').strip()

        if not username or not email:
            raise ValidationError("Please enter both username and email.")

        # Case-insensitive username lookup against the CORRECT user model
        user = User.objects.filter(username__iexact=username).first()
        if not user:
            raise ValidationError("No user found with this username.")

        # If they have student/employer profile, validate the email against the right field
        if hasattr(user, 'studentprofile'):
            personal = getattr(user.studentprofile, 'personal_email', None)
            if not personal or personal.lower() != email.lower():
                raise ValidationError("The email does not match the personal email associated with this username.")
        elif hasattr(user, 'employerprofile'):
            company_email = getattr(user.employerprofile, 'email', None)
            if not company_email or company_email.lower() != email.lower():
                raise ValidationError("The email does not match the company email associated with this username.")
        else:
            raise ValidationError("This username is not associated with a student or employer profile.")

        # Cache the user so get_users() can return it even if user.email differs
        self.user_cache = user
        return cleaned

    # The base class finds users by comparing email to user.email.
    # We want to send to 'email' but still reset THIS user.
    def get_users(self, email):
        user = getattr(self, 'user_cache', None)
        if user and user.is_active:
            return [user]
        return []
    
class PasswordValidator:
    @staticmethod
    def validate_password(value):
        if len(value) < 8 or len(value) > 12:
            raise ValidationError("Password must be between 8 and 12 characters long.")
        if not re.search(r'[A-Za-z]', value):
            raise ValidationError("Password must contain at least one letter.")
        if not re.search(r'\d', value):
            raise ValidationError("Password must contain at least one number.")
        if not re.search(r'[!@#$%^&*]', value):
            raise ValidationError("Password must contain at least one special character (!@#$%^&*).")