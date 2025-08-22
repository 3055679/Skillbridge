import time
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from django.contrib import messages
from django.core.mail import send_mail, mail_admins
from django.template.loader import render_to_string
from django.urls import reverse
from django.conf import settings
from django.db import transaction
import uuid
import logging
from django.db.models import Q  # Added import for Q
from jobs.models import Job
from .forms import StudentSignUpForm, EmployerSignUpForm, LoginForm, UserUpdateForm, StudentProfileForm, EmployerProfileForm, EducationForm, ExperienceForm, PortfolioForm, EducationFormSet, ExperienceFormSet, PortfolioFormSet
from .models import StudentProfile, EmployerProfile, Skill, Education, Experience, PortfolioItem, UserProfile
from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage
from django.contrib.staticfiles.storage import staticfiles_storage
User = get_user_model()

logger = logging.getLogger(__name__)

@csrf_protect
def student_signup(request):
    if request.user.is_authenticated and hasattr(request.user, 'userprofile') and request.user.userprofile.email_verified:
        messages.info(request, "You are already registered and verified. Please login.")
        return redirect('accounts:login')
    
    if request.method == 'POST':
        form = StudentSignUpForm(request.POST, request.FILES)
        if form.is_valid():
            university_email = form.cleaned_data.get('university_email')
            student_id_document = form.cleaned_data.get('student_id_document')
            has_university_email = form.cleaned_data.get('has_university_email')
            email = university_email if university_email else form.cleaned_data['personal_email']
            personal_email = form.cleaned_data['personal_email']
            username = form.cleaned_data['username']
            
            try:
                with transaction.atomic():
                    user = User(
                        username=username,
                        email=email,
                        first_name=form.cleaned_data['first_name'],
                        last_name=form.cleaned_data['last_name'],
                        is_active=False,
                        is_student=True,
                        is_verified=False,
                    )
                    user.set_password(form.cleaned_data['password1'])
                    
                    profile = UserProfile(user=user)
                    
                    student_profile = StudentProfile(
                        user=user,
                        university=form.cleaned_data['university'],
                        phone_number=form.cleaned_data['phone_number'],
                        country=form.cleaned_data['country'],
                        student_id_document=student_id_document,
                        student_id_verified=bool(university_email),
                        personal_email=form.cleaned_data['personal_email'],
                    )
                    
                    if has_university_email and university_email:
                        verification_token = uuid.uuid4()
                        profile.email_verification_token = verification_token
                        
                        verification_url = request.build_absolute_uri(
                            reverse('accounts:verify_email', kwargs={'token': str(verification_token)})
                        )
                        # email fo rpersonal
                        recipient_list = [personal_email]
                        if university_email and university_email != personal_email:
                            recipient_list.append(university_email)

                        send_mail(
                            'Verify Your Email - SkillBridge',
                            render_to_string('accounts/email_verification.txt', {
                                'user': user,
                                'verification_url': verification_url
                            }),
                            settings.DEFAULT_FROM_EMAIL,
                            [user.email],
                            fail_silently=False,
                        )
                        
                        user.save()
                        profile.save()
                        student_profile.save()

                        logger.info(f"Student signup successful for {username}, verification email sent to {recipient_list}")
                        
                        messages.success(request, "Verification email sent to your university email (if provided). Please check your inbox.")
                        return redirect('accounts:email_verification_sent')
                    else:
                        user.save()
                        profile.save()
                        student_profile.save()
                        notify_admin_for_approval(user)
                        messages.success(request, "Your account is under review. Try after few mins.")
                        return redirect('accounts:pending_approval')
            except Exception as e:
                logger.error(f"Failed to complete student registration for {email}: {str(e)}")
                messages.error(request, "Registration failed. Please try again.")
                return render(request, 'accounts/student_signup.html', {'form': form})
        else:
            if form.non_field_errors():
                for error in form.non_field_errors():
                    messages.error(request, error)
    else:
        form = StudentSignUpForm()
    
    return render(request, 'accounts/student_signup.html', {'form': form})




def verify_email(request, token):
    try:
        profile = UserProfile.objects.get(email_verification_token=token)
        user = profile.user
        
        profile.email_verified = True
        profile.email_verification_token = None
        profile.save()
        
        user.is_active = True
        user.is_verified = True
        user.save()
        
        if hasattr(user, 'studentprofile'):
            user.studentprofile.student_id_verified = True
            user.studentprofile.save()
        elif hasattr(user, 'employerprofile'):
            user.employerprofile.is_approved = True
            user.employerprofile.save()
        
        logger.info(f"Email verified for user {user.username}")
        messages.success(request, "Your email is verified. Please login here.")
        return redirect('accounts:login')
    
    except UserProfile.DoesNotExist:
        messages.error(request, 'Invalid or expired verification link.')
        return render(request, 'accounts/email_verification_invalid.html', {
            'message': 'Invalid or expired verification link.'
        }, status=404)

def email_verification_sent(request):
    return render(request, 'accounts/email_verification_sent.html')

@login_required(login_url='accounts:login')
def pending_approval(request):
    if not (hasattr(request.user, 'studentprofile') or hasattr(request.user, 'employerprofile')):
        return redirect('accounts:home')
    
    if hasattr(request.user, 'studentprofile') and request.user.studentprofile.student_id_verified:
        messages.success(request, "Your account has been approved. Please login.")
        return redirect('accounts:login')
    elif hasattr(request.user, 'employerprofile') and request.user.employerprofile.is_approved:
        messages.success(request, "Your account has been approved. Please login.")
        return redirect('accounts:login')
    
    return render(request, 'accounts/pending_approval.html')

def notify_admin_for_approval(user):
    student_profile = user.studentprofile
    subject = f"Student Approval Required: {user.get_full_name()}"
    message = render_to_string('accounts/admin/approval_notification.txt', {
        'user': user,
        'profile': student_profile,
        'admin_url': settings.ADMIN_URL
    })
    try:
        mail_admins(
            subject=subject,
            message=message,
            fail_silently=False
        )
    except Exception as e:
        logger.error(f"Failed to send admin notification for {user.email}: {str(e)}")

def notify_admin_for_employer_approval(user):
    employer_profile = user.employerprofile
    subject = f"Employer Approval Required: {user.get_full_name()}"
    message = render_to_string('accounts/admin/employer_approval_notification.txt', {
        'user': user,
        'profile': employer_profile,
        'admin_url': settings.ADMIN_URL
    })
    try:
        mail_admins(
            subject=subject,
            message=message,
            fail_silently=False
        )
    except Exception as e:
        logger.error(f"Failed to send admin notification for {user.email}: {str(e)}")

@csrf_protect
def user_login(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                if user.is_active:
                    login(request, user)
                    if user.is_student:
                        if hasattr(user, 'studentprofile') and user.studentprofile.student_id_document and not user.studentprofile.student_id_verified:
                            messages.warning(request, 'Your account is still under review.')
                            return redirect('accounts:pending_approval')
                        return redirect('jobs:student_dashboard')
                    elif user.is_employer:
                        if hasattr(user, 'employerprofile') and not user.employerprofile.is_approved:
                            messages.warning(request, 'Your account is still under review.')
                            return redirect('accounts:pending_approval')
                        return redirect('jobs:employer_dashboard')
                else:
                    messages.error(request, 'Your account is pending verification. Please check your email to verify your account or contact support.')
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = LoginForm()
    return render(request, 'accounts/login.html', {'form': form})

# @csrf_protect
# def user_login(request):
#     if request.method == 'POST':
#         form = LoginForm(request.POST)
#         if form.is_valid():
#             username = form.cleaned_data['username']
#             password = form.cleaned_data['password']
#             user = authenticate(request, username=username, password=password)
#             if user is not None:
#                 if user.is_active:
#                     login(request, user)
#                     if user.is_student:
#                         if hasattr(user, 'studentprofile') and user.studentprofile.student_id_document and not user.studentprofile.is_approved:
#                             messages.warning(request, 'Your account is still under review.')
#                             return redirect('accounts:pending_approval')
#                         return redirect('jobs:student_dashboard')
#                     elif user.is_employer:
#                         if hasattr(user, 'employerprofile') and not user.employerprofile.is_approved:
#                             messages.warning(request, 'Your account is still under review.')
#                             return redirect('accounts:pending_approval')
#                         return redirect('jobs:employer_dashboard')
#                     else:
#                         return redirect('accounts:home')  # Fallback for users without profile
#                 else:
#                     messages.error(request, 'Your account is pending verification. Please check your email to verify your account or contact support.')
#             else:
#                 messages.error(request, 'Invalid username or password.')
#             return redirect('accounts:login')  # Redirect on failure
#         else:
#             messages.error(request, 'Please correct the errors below.')
#             return redirect('accounts:login')
#     else:
#         form = LoginForm()
#     return render(request, 'accounts/login.html', {'form': form})

def user_logout(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('accounts:home')

@csrf_protect
def employer_signup(request):
    if request.user.is_authenticated and hasattr(request.user, 'userprofile') and request.user.userprofile.email_verified:
        messages.info(request, "You are already registered and verified. Please login.")
        return redirect('accounts:login')
    
    if request.method == 'POST':
        form = EmployerSignUpForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                with transaction.atomic():
                    user = User(
                        username=form.cleaned_data['username'],
                        email=email,
                        is_employer=True,
                        is_active=False,
                    )
                    user.set_password(form.cleaned_data['password1'])
                    
                    employer_profile = EmployerProfile(
                        user=user,
                        company_name=form.cleaned_data['company_name'],
                        email=email,
                        phone_number=form.cleaned_data['phone_number'],
                        country=form.cleaned_data['country'],
                    )
                    
                    profile = UserProfile(user=user)
                    verification_token = uuid.uuid4()
                    profile.email_verification_token = verification_token
                    
                    verification_url = request.build_absolute_uri(
                        reverse('accounts:verify_email', kwargs={'token': str(verification_token)})
                    )
                    send_mail(
                        'Verify Your Email - SkillBridge',
                        render_to_string('accounts/email_verification.txt', {
                            'user': user,
                            'verification_url': verification_url
                        }),
                        settings.DEFAULT_FROM_EMAIL,
                        [user.email],
                        fail_silently=False,
                    )
                    
                    user.save()
                    employer_profile.save()
                    profile.save()
                    
                    messages.success(request, "Verification email sent. Please check your inbox.")
                    return redirect('accounts:email_verification_sent')
            except Exception as e:
                logger.error(f"Failed to complete employer registration for {email}: {str(e)}")
                messages.error(request, "Registration failed. Please try again.")
                return render(request, 'accounts/employer_signup.html', {'form': form})
        else:
            if form.non_field_errors():
                for error in form.non_field_errors():
                    messages.error(request, error)
    else:
        form = EmployerSignUpForm()
    return render(request, 'accounts/employer_signup.html', {'form': form})

@login_required
def dashboard(request):
    if request.user.is_student and not request.user.studentprofile.student_id_verified:
        return render(request, 'accounts/pending_approval.html')
    return render(request, 'dashboard.html')

# @csrf_protect
# @login_required
# def employer_profile(request):
#     if not hasattr(request.user, 'employerprofile'):
#         return redirect('accounts:home')
    
#     if request.method == 'POST':
#         user_form = UserUpdateForm(request.POST, instance=request.user)
#         profile_form = EmployerProfileForm(
#             request.POST, 
#             request.FILES, 
#             instance=request.user.employerprofile
#         )
        
#         if user_form.is_valid() and profile_form.is_valid():
#             user_form.save()
#             profile_form.save()
#             messages.success(request, 'Your profile has been updated!')
#             return redirect('accounts:employer_profile')
#     else:
#         user_form = UserUpdateForm(instance=request.user)
#         profile_form = EmployerProfileForm(instance=request.user.employerprofile)

#     context = {
#         'user_form': user_form,
#         'profile_form': profile_form
#     }
#     return render(request, 'accounts/employer_profile.html', context)

# @csrf_protect
# @login_required
# def student_profile(request):
#     profile = get_object_or_404(StudentProfile, user=request.user)
#     all_skills = Skill.objects.all()
    
#     if request.method == 'POST':
#         form_type = request.POST.get('form_type')
        
#         if form_type == 'profile' and user_form.is_valid() and profile_form.is_valid():
#             user_form = UserUpdateForm(request.POST, instance=request.user)
#             profile_form = StudentProfileForm(request.POST, request.FILES, instance=profile)
#             user_form.save()
#             profile_form.save()
#             messages.success(request, 'Profile updated successfully.')
#             return redirect('accounts:student_profile')
#         elif form_type == 'education':
#             education_formset = EducationFormSet(request.POST, instance=profile)
#             if education_formset.is_valid():
#                 education_formset.save()
#                 messages.success(request, 'Education updated successfully.')
#                 return redirect('accounts:student_profile')
#         elif form_type == 'experience':
#             experience_formset = ExperienceFormSet(request.POST, request.FILES, instance=profile)
#             if experience_formset.is_valid():
#                 experience_formset.save()
#                 messages.success(request, 'Experience updated successfully.')
#                 return redirect('accounts:student_profile')
#         elif form_type == 'portfolio':
#             portfolio_formset = PortfolioFormSet(request.POST, request.FILES, instance=profile)
#             if portfolio_formset.is_valid():
#                 portfolio_formset.save()
#                 messages.success(request, 'Portfolio updated successfully.')
#                 return redirect('accounts:student_profile')
#         else:
#             messages.error(request, 'Please correct the errors below.')
#     else:
#         user_form = UserUpdateForm(instance=request.user)
#         profile_form = StudentProfileForm(instance=profile)
#         education_formset = EducationFormSet(instance=profile)
#         experience_formset = ExperienceFormSet(instance=profile)
#         portfolio_formset = PortfolioFormSet(instance=profile)
    
#     context = {
#         'student': profile,
#         'user_form': user_form,
#         'profile_form': profile_form,
#         'education_formset': education_formset,
#         'experience_formset': experience_formset,
#         'portfolio_formset': portfolio_formset,
#         'all_skills': all_skills,
#         'educations': profile.educations.all(),
#         'experiences': profile.experiences.all(),
#         'portfolio_items': profile.portfolio_items.all(),
#     }
    
#     return render(request, 'accounts/student_profile.html', context)



@csrf_protect
@login_required
def employer_profile(request):
    if not hasattr(request.user, 'employerprofile'):
        return redirect('accounts:home')

    employer = request.user.employerprofile

    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = EmployerProfileForm(request.POST, request.FILES, instance=employer)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Your profile has been updated!')
            return redirect('accounts:employer_profile')
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = EmployerProfileForm(instance=employer)

    # Build a cache-busted logo URL for the sidebar/profile
    if employer.company_logo and default_storage.exists(employer.company_logo.name):
        try:
            mtime = int(default_storage.get_modified_time(employer.company_logo.name).timestamp())
        except Exception:
            mtime = int(time.time())
        company_logo_url = f"{employer.company_logo.url}?v={mtime}"
    else:
        company_logo_url = staticfiles_storage.url('images/default-logo.png')

    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'employer': employer,
        'company_logo_url': company_logo_url,
    }
    return render(request, 'accounts/employer_profile.html', context)

@csrf_protect
@login_required
def student_profile(request):
    profile = get_object_or_404(StudentProfile, user=request.user)
    all_skills = Skill.objects.all()

    def profile_image_url_for(profile_obj):
        if profile_obj.profile_picture and default_storage.exists(profile_obj.profile_picture.name):
            try:
                mtime = int(default_storage.get_modified_time(profile_obj.profile_picture.name).timestamp())
            except Exception:
                mtime = int(time.time())
            return f"{profile_obj.profile_picture.url}?v={mtime}"
        return staticfiles_storage.url('images/default-profile.png')

    if request.method == 'POST':
        form_type = request.POST.get('form_type')
    
        # Prepare defaults for re-render on error:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = StudentProfileForm(instance=profile)
        education_formset = EducationFormSet(instance=profile)
        experience_formset = ExperienceFormSet(instance=profile)
        portfolio_formset = PortfolioFormSet(instance=profile)

        if form_type == 'profile':
            user_form = UserUpdateForm(request.POST, instance=request.user)
            profile_form = StudentProfileForm(request.POST, request.FILES, instance=profile)
            if user_form.is_valid() and profile_form.is_valid():
                user_form.save()
                profile_form.save()
                messages.success(request, 'Profile updated successfully.')
                return redirect('accounts:student_profile')
            else:
                messages.error(request, 'Please correct the errors in your profile.')

        elif form_type == 'education':
            education_formset = EducationFormSet(request.POST, instance=profile)
            if education_formset.is_valid():
                education_formset.save()
                messages.success(request, 'Education updated successfully.')
                return redirect('accounts:student_profile')
            else:
                messages.error(request, 'Please correct the education errors.')

        elif form_type == 'experience':
            experience_formset = ExperienceFormSet(request.POST, request.FILES, instance=profile)
            if experience_formset.is_valid():
                experience_formset.save()
                messages.success(request, 'Experience updated successfully.')
                return redirect('accounts:student_profile')
            else:
                messages.error(request, 'Please correct the experience errors.')

        elif form_type == 'portfolio':
            portfolio_formset = PortfolioFormSet(request.POST, request.FILES, instance=profile)
            if portfolio_formset.is_valid():
                portfolio_formset.save()
                messages.success(request, 'Portfolio updated successfully.')
                return redirect('accounts:student_profile')
            else:
                messages.error(request, 'Please correct the portfolio errors.')

    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = StudentProfileForm(instance=profile)
        education_formset = EducationFormSet(instance=profile)
        experience_formset = ExperienceFormSet(instance=profile)
        portfolio_formset = PortfolioFormSet(instance=profile)

    context = {
        'student': profile,
        'user_form': user_form,
        'profile_form': profile_form,
        'education_formset': education_formset,
        'experience_formset': experience_formset,
        'portfolio_formset': portfolio_formset,
        'all_skills': all_skills,
        'educations': profile.educations.all(),
        'experiences': profile.experiences.all(),
        'portfolio_items': profile.portfolio_items.all(),
        'profile_image_url': profile_image_url_for(profile),
    }
    return render(request, 'accounts/student_profile.html', context)

@csrf_protect
@login_required
def add_skill(request):
    if request.method == 'POST':
        profile = get_object_or_404(StudentProfile, user=request.user)
        new_skill_name = request.POST.get('new_skill')
        if new_skill_name:
            skill, created = Skill.objects.get_or_create(name=new_skill_name.strip())
            profile.skills.add(skill)
            messages.success(request, f"Skill '{skill.name}' added successfully!")
        else:
            messages.error(request, "Please enter a skill name.")
        return redirect('accounts:student_profile')
    return redirect('accounts:student_profile')

@csrf_protect
@login_required
def remove_skill(request, skill_id):
    student = request.user.studentprofile
    skill = get_object_or_404(Skill, id=skill_id)
    student.skills.remove(skill)
    messages.success(request, f"Skill '{skill.name}' removed successfully!")
    return redirect('accounts:student_profile')

@login_required
def edit_education(request, id):
    education = get_object_or_404(Education, id=id, student__user=request.user)
    if request.method == 'POST':
        form = EducationForm(request.POST, instance=education)
        if form.is_valid():
            form.save()
            messages.success(request, 'Education updated successfully.')
            return redirect('accounts:student_profile')
    else:
        form = EducationForm(instance=education)
    return render(request, 'accounts/edit_education.html', {'form': form})

@login_required
def delete_education(request, id):
    education = get_object_or_404(Education, id=id, student__user=request.user)
    if request.method == 'POST':
        education.delete()
        messages.success(request, 'Education deleted successfully.')
        return redirect('accounts:student_profile')
    return redirect('accounts:student_profile')

@login_required
def edit_experience(request, id):
    experience = get_object_or_404(Experience, id=id, student__user=request.user)
    if request.method == 'POST':
        form = ExperienceForm(request.POST, request.FILES, instance=experience)
        if form.is_valid():
            form.save()
            messages.success(request, 'Experience updated successfully.')
            return redirect('accounts:student_profile')
    else:
        form = ExperienceForm(instance=experience)
    return render(request, 'accounts/edit_experience.html', {'form': form})

@login_required
def delete_experience(request, id):
    experience = get_object_or_404(Experience, id=id, student__user=request.user)
    if request.method == 'POST':
        experience.delete()
        messages.success(request, 'Experience deleted successfully.')
        return redirect('accounts:student_profile')
    return redirect('accounts:student_profile')

@login_required
def edit_portfolio(request, id):
    portfolio_item = get_object_or_404(PortfolioItem, id=id, student__user=request.user)
    if request.method == 'POST':
        form = PortfolioForm(request.POST, request.FILES, instance=portfolio_item)
        if form.is_valid():
            form.save()
            messages.success(request, 'Portfolio item updated successfully.')
            return redirect('accounts:student_profile')
    else:
        form = PortfolioForm(instance=portfolio_item)
    return render(request, 'accounts/edit_portfolio.html', {'form': form})

@login_required
def delete_portfolio(request, id):
    portfolio_item = get_object_or_404(PortfolioItem, id=id, student__user=request.user)
    if request.method == 'POST':
        portfolio_item.delete()
        messages.success(request, 'Portfolio item deleted successfully.')
        return redirect('accounts:student_profile')
    return redirect('accounts:student_profile')

@login_required
def view_portfolio(request, id):
    portfolio_item = get_object_or_404(PortfolioItem, id=id, student__user=request.user)
    return render(request, 'accounts/view_portfolio.html', {'portfolio_item': portfolio_item})

def home(request):
    featured_jobs = Job.objects.filter(
        is_active=True,
        job_type__in=['INT', 'GIG']
    ).select_related('employer')[:6]
    return render(request, 'home.html', {'featured_jobs': featured_jobs})

def about(request):
    return render(request, 'about.html', {'title': 'About Us'})

def contact(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        message = request.POST.get('message')
        send_mail(
            subject=f'Contact Form Submission from {name}',
            message=f'Message from {name} ({email}):\n\n{message}',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.DEFAULT_FROM_EMAIL],
            fail_silently=True,
        )
        messages.success(request, 'Your message has been sent successfully.')
        return redirect('contact')
    return render(request, 'contact.html', {'title': 'Contact Us'})

