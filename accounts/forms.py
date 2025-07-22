from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, PasswordChangeForm
from django.forms import ModelForm, inlineformset_factory
from django.core.validators import validate_email, FileExtensionValidator, RegexValidator
from django.core.exceptions import ValidationError
from .models import User, StudentProfile, EmployerProfile, Skill, Education, Experience, PortfolioItem

class StudentSignUpForm(UserCreationForm):
    first_name = forms.CharField(max_length=100, required=True)
    last_name = forms.CharField(max_length=100, required=True)
    personal_email = forms.EmailField(required=True)
    phone_number = forms.CharField(
        max_length=17,
        required=True,
        validators=[RegexValidator(regex=r'^\+?1?\d{9,15}$', message="Phone number must be entered in the format: '+999999999'.")]
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

        # Existing validations
        if has_university_email and not university_email:
            raise ValidationError("Please provide a university email if you selected that option.")
        if not has_university_email and not cleaned_data.get('student_id_document'):
            raise ValidationError("Please upload a student ID document if you do not have a university email.")
        if university_email and not (university_email.endswith('.edu') or '@student.gla.ac.uk' in university_email):
            raise ValidationError("Please provide a valid .edu or @student.gla.ac.uk email address.")
        
        return cleaned_data

class EmployerSignUpForm(UserCreationForm):
    company_name = forms.CharField(max_length=200, required=True)
    email = forms.EmailField(required=True)
    phone_number = forms.CharField(
        max_length=17,
        required=True,
        validators=[RegexValidator(regex=r'^\+?1?\d{9,15}$', message="Phone number must be entered in the format: '+999999999'.")]
    )
    country = forms.CharField(max_length=100, required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'phone_number', 'country', 'company_name', 'password1', 'password2')

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        if email and User.objects.filter(email=email).exists():
            raise ValidationError("This email is already registered. Please use a different email or log in.")
        return cleaned_data

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

class UserUpdateForm(UserChangeForm):
    email = forms.EmailField()
    password = None

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']

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