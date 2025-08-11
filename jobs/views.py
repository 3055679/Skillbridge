from venv import logger
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from django.contrib import messages
from django.utils import timezone
from accounts.models import StudentProfile, EmployerProfile
from .models import ApplicationResponse, Job, Application, Interview, JobQuestion, ProposedInterviewSlot, Notification
from .forms import ApplicationForm, JobForm, InterviewForm, JobQuestionFormSet, MaxApplicationsForm, ResumeForm
from django.http import HttpResponse
import tempfile
import subprocess
import re
import os

@csrf_protect
@login_required
def student_dashboard(request):
    try:
        student = request.user.studentprofile
    except StudentProfile.DoesNotExist:
        student = StudentProfile.objects.create(user=request.user)
        messages.warning(request, 'Please complete your profile to get started.')
    
    applications = Application.objects.filter(student=student)
    total_applications = applications.count()
    interviews = applications.filter(status='INTERVIEW').count()
    pending = applications.filter(status='PENDING').count()
    rejected = applications.filter(status='REJECTED').count()
    
    recent_applications = applications.order_by('-applied_date')[:3]
    
    upcoming_interviews = Interview.objects.filter(
        application__student=student,
        status='SCHEDULED',
        interview_date__gte=timezone.now()
    ).order_by('interview_date')[:2]
    
    recommended_jobs = Job.objects.filter(
        is_active=True,
        application_deadline__gt=timezone.now()
    ).order_by('-posted_date')[:3]
    
    context = {
        'student': student,
        'total_applications': total_applications,
        'interviews': interviews,
        'pending': pending,
        'rejected': rejected,
        'recent_applications': recent_applications,
        'upcoming_interviews': upcoming_interviews,
        'recommended_jobs': recommended_jobs,
    }
    return render(request, 'jobs/student_dashboard.html', context)

@csrf_protect
@login_required
def student_interviews(request):
    try:
        student = request.user.studentprofile
    except StudentProfile.DoesNotExist:
        student = StudentProfile.objects.create(user=request.user)
        messages.warning(request, 'Please complete your profile to get started.')
    
    interviews = Interview.objects.filter(
        application__student=student
    ).order_by('-interview_date')
    
    context = {
        'student': student,
        'interviews': interviews,
    }
    return render(request, 'jobs/student_interviews.html', context)

@csrf_protect
@login_required
def my_applications(request):
    try:
        student = request.user.studentprofile
    except StudentProfile.DoesNotExist:
        student = StudentProfile.objects.create(user=request.user)
        messages.warning(request, 'Please complete your profile to get started.')
    
    applications = Application.objects.filter(student=student).order_by('-applied_date')
    
    context = {
        'student': student,
        'applications': applications,
    }
    return render(request, 'jobs/my_applications.html', context)

@csrf_protect
@login_required
def apply_job(request, job_id):
    job = get_object_or_404(Job, id=job_id, is_active=True)
    if not job.is_accepting_applications():
        messages.error(request, "This job is closed and no longer accepting applications.")
        return redirect('jobs:job_list')
    
    profile = get_object_or_404(StudentProfile, user=request.user)
    
    # Check mandatory fields
    missing_fields = []
    if not profile.student_id_document:
        missing_fields.append("Student ID Document")
    if not profile.skills.exists():
        missing_fields.append("Skills")
    if not profile.work_preference:
        missing_fields.append("Work Preference")
    if not profile.availability:
        missing_fields.append("Availability")
    if not profile.resume:
        missing_fields.append("Resume")
    if not profile.educations.exists():
        missing_fields.append("Education")
    if not profile.experiences.exists():
        missing_fields.append("Experience")
    if not profile.portfolio_items.exists():
        missing_fields.append("Portfolio Items")
    
    if missing_fields:
        messages.error(request, f"Please complete the following required fields in your profile: {', '.join(missing_fields)}")
        return redirect('accounts:student_profile')
    
    if request.method == 'POST':
        form = ApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            application = form.save(commit=False)
            application.student = profile
            application.job = job
            application.save()
            # Save custom question responses
            for question in job.questions.all():
                response_key = f'question_{question.id}'
                if response_key in request.POST:
                    ApplicationResponse.objects.create(
                        application=application,
                        question=question,
                        response=request.POST[response_key]
                    )
            messages.success(request, 'Application submitted successfully.')
            return redirect('jobs:my_applications')
    else:
        form = ApplicationForm()
    
    return render(request, 'jobs/apply_job.html', {'form': form, 'job': job})

@csrf_protect
@login_required
def employer_dashboard(request):
    try:
        employer = request.user.employerprofile
    except EmployerProfile.DoesNotExist:
        messages.error(request, 'Please complete your employer profile.')
        return redirect('accounts:employer_profile')
    
    jobs = Job.objects.filter(employer=employer)
    applications = Application.objects.filter(job__employer=employer)
    notifications = Notification.objects.filter(employer=employer, is_read=False)
    
    context = {
        'employer': employer,
        'jobs': jobs,
        'applications': applications,
        'notifications': notifications,
        'status_choices': Application.STATUS_CHOICES,  # Add this line
    }
    return render(request, 'jobs/employer_dashboard.html', context)

@csrf_protect
@login_required
def post_job(request):
    try:
        employer = request.user.employerprofile
    except EmployerProfile.DoesNotExist:
        messages.error(request, 'Please complete your employer profile.')
        return redirect('accounts:employer_profile')
       
    if request.method == 'POST':
        form = JobForm(request.POST, request.FILES)
        question_formset = JobQuestionFormSet(request.POST)
        if form.is_valid() and question_formset.is_valid():
            job = form.save(commit=False)
            job.employer = employer
            job.is_active = True
            job.posted_date = timezone.now()
            job.save()
            for form in question_formset:
                if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                    question = form.save(commit=False)
                    question.job = job
                    question.save()
            messages.success(request, 'Job posted successfully!')
            return redirect('jobs:employer_dashboard')
    else:
        form = JobForm()
        question_formset = JobQuestionFormSet()
       
    return render(request, 'jobs/post_job.html', {'form': form, 'question_formset': question_formset})

@csrf_protect
@login_required
def job_status_update(request, pk):
    job = get_object_or_404(Job, pk=pk, employer__user=request.user)
    if request.method == 'POST':
        is_active = request.POST.get('is_active') == 'True'
        job.is_active = is_active
        job.save()
        messages.success(request, f"Job status updated to {'Active' if is_active else 'Closed'}.")
        return redirect('jobs:employer_dashboard')
    
    return render(request, 'jobs/job_status_form.html', {'job': job})

@csrf_protect
@login_required
def manage_max_applications(request, pk):
    job = get_object_or_404(Job, pk=pk, employer__user=request.user)
    if request.method == 'POST':
        form = MaxApplicationsForm(request.POST, instance=job)
        action = request.POST.get('action')
        if action == 'close':
            job.is_active = False
            job.save()
            messages.success(request, f"Job '{job.title}' closed.")
            Notification.objects.filter(job=job).update(is_read=True)
            return redirect('jobs:employer_dashboard')
        elif form.is_valid():
            form.save()
            messages.success(request, f"Maximum applications for '{job.title}' updated.")
            Notification.objects.filter(job=job).update(is_read=True)
            return redirect('jobs:employer_dashboard')
    else:
        form = MaxApplicationsForm(instance=job)
    
    return render(request, 'jobs/manage_max_applications.html', {'form': form, 'job': job})

@csrf_protect
@login_required
def bulk_manage_applications(request):
    if not hasattr(request.user, 'employerprofile'):
        messages.error(request, "Only employers can manage applications.")
        return redirect('jobs:student_dashboard')
    if request.method == 'POST':
        application_ids = request.POST.getlist('application_ids')
        status = request.POST.get('status')
        message = request.POST.get('message', '')
        applications = Application.objects.filter(
            id__in=application_ids, 
            job__employer__user=request.user
        )
        if status in [choice[0] for choice in Application.STATUS_CHOICES]:
            applications.update(status=status)
            if message:
                # In a real app, send email or notification to students
                for app in applications:
                    Notification.objects.create(
                        employer=app.job.employer,
                        job=app.job,
                        message=f"Application status updated: {message}"
                    )
            messages.success(request, f"Updated {applications.count()} applications.")
        return redirect('jobs:employer_dashboard')
    return redirect('jobs:employer_dashboard')

@csrf_protect
@login_required
def manage_application(request, application_id):
    application = get_object_or_404(Application, pk=application_id, job__employer__user=request.user)
    student_profile = application.student
    
    if request.method == 'POST':
        status = request.POST.get('status')
        if status in [choice[0] for choice in Application.STATUS_CHOICES]:
            application.status = status
            application.save()
            messages.success(request, f'Application status updated to {application.get_status_display()}')
            return redirect('jobs:employer_dashboard')
    
    context = {
        'application': application,
        'student_profile': student_profile,
        'status_choices': Application.STATUS_CHOICES,
    }
    return render(request, 'jobs/manage_application.html', context)

@csrf_protect
@login_required
def schedule_interview(request, application_id):
    application = get_object_or_404(Application, pk=application_id, job__employer__user=request.user)
    if request.method == 'POST':
        form = InterviewForm(request.POST)
        if form.is_valid():
            interview = form.save(commit=False)
            interview.application = application
            interview.status = 'SCHEDULED'
            interview.save()
            proposed_slots = form.cleaned_data.get('proposed_slots')
            if proposed_slots:
                for slot in proposed_slots.split('\n'):
                    slot = slot.strip()
                    if slot:
                        try:
                            slot_time = timezone.datetime.strptime(slot, '%Y-%m-%d %H:%M')
                            ProposedInterviewSlot.objects.create(
                                interview=interview,
                                slot_time=slot_time
                            )
                        except ValueError:
                            messages.warning(request, f"Invalid slot format: {slot}")
            application.status = 'INTERVIEW'
            application.save()
            messages.success(request, 'Interview scheduled successfully!')
            return redirect('jobs:employer_dashboard')
    else:
        form = InterviewForm()
    
    return render(request, 'jobs/schedule_interview.html', {'form': form, 'application': application})

@csrf_protect
@login_required
def employer_interviews(request):
    try:
        employer = request.user.employerprofile
    except EmployerProfile.DoesNotExist:
        messages.error(request, 'Please complete your employer profile.')
        return redirect('accounts:employer_profile')
    
    interviews = Interview.objects.filter(
        application__job__employer=employer,
        status='SCHEDULED'
    ).order_by('interview_date')
    
    context = {
        'employer': employer,
        'interviews': interviews,
    }
    return render(request, 'jobs/employer_interviews.html', context)

# @csrf_protect
# @login_required
# def interview_detail(request, pk):
#     interview = get_object_or_404(Interview, pk=pk)
#     if request.user.is_student and interview.application.student.user != request.user:
#         messages.error(request, "You can only view your own interviews.")
#         return redirect('jobs:student_dashboard')
#     elif request.user.is_employer and interview.application.job.employer.user != request.user:
#         messages.error(request, "You can only view interviews for your jobs.")
#         return redirect('jobs:employer_dashboard')
#     return render(request, 'jobs/interview_detail.html', {
#         'interview': interview,
#         'application': interview.application,
#         'student_profile': interview.application.student,
#     })


@csrf_protect
@login_required
def interview_detail(request, pk):
    interview = get_object_or_404(Interview, pk=pk)
    
    # Check if user is a student and owns the application
    if hasattr(request.user, 'studentprofile') and interview.application.student.user == request.user:
        return render(request, 'jobs/interview_detail.html', {
            'interview': interview,
            'application': interview.application,
            'student_profile': interview.application.student,
            'user_type': 'student',
        })
    
    # Check if user is an employer and owns the job
    elif hasattr(request.user, 'employerprofile') and interview.application.job.employer.user == request.user:
        return render(request, 'jobs/interview_detail.html', {
            'interview': interview,
            'application': interview.application,
            'student_profile': interview.application.student,
            'user_type': 'employer',
        })
    
    # Unauthorized access
    else:
        messages.error(request, "You do not have permission to view this interview.")
        if hasattr(request.user, 'employerprofile'):
            return redirect('jobs:employer_dashboard')
        elif hasattr(request.user, 'studentprofile'):
            return redirect('jobs:student_dashboard')
        else:
            return redirect('jobs:job_list')

@csrf_protect
@login_required
def reschedule_interview(request, pk):
    interview = get_object_or_404(Interview, pk=pk)
    if not hasattr(request.user, 'employerprofile'):
        messages.error(request, "Only employers can reschedule interviews.")
        return redirect('jobs:student_dashboard')
    if interview.application.job.employer.user != request.user:
        messages.error(request, "You can only reschedule interviews for your jobs.")
        return redirect('jobs:employer_dashboard')
    if interview.status != 'SCHEDULED':
        messages.error(request, 'Only scheduled interviews can be rescheduled.')
        return redirect('jobs:employer_interviews')
    
    if request.method == 'POST':
        form = InterviewForm(request.POST, instance=interview)
        if form.is_valid():
            form.save()
            proposed_slots = form.cleaned_data.get('proposed_slots')
            if proposed_slots:
                interview.proposed_slots.all().delete()  # Clear existing slots
                for slot in proposed_slots.split('\n'):
                    slot = slot.strip()
                    if slot:
                        try:
                            slot_time = timezone.datetime.strptime(slot, '%Y-%m-%d %H:%M')
                            ProposedInterviewSlot.objects.create(
                                interview=interview,
                                slot_time=slot_time
                            )
                        except ValueError:
                            messages.warning(request, f"Invalid slot format: {slot}")
            messages.success(request, 'Interview rescheduled successfully.')
            return redirect('jobs:employer_interviews')
    else:
        form = InterviewForm(instance=interview)
    
    return render(request, 'jobs/reschedule_interview.html', {
        'form': form,
        'interview': interview,
        'application': interview.application,
    })

@csrf_protect
@login_required
def cancel_interview(request, pk):
    interview = get_object_or_404(Interview, pk=pk)
    if not hasattr(request.user, 'employerprofile'):
        messages.error(request, "Only employers can cancel interviews.")
        return redirect('jobs:student_dashboard')
    if interview.application.job.employer.user != request.user:
        messages.error(request, "You can only cancel interviews for your jobs.")
        return redirect('jobs:employer_dashboard')
    if interview.status != 'SCHEDULED':
        messages.error(request, 'Only scheduled interviews can be canceled.')
        return redirect('jobs:employer_interviews')
    
    if request.method == 'POST':
        interview.status = 'CANCELED'
        interview.save()
        interview.application.status = 'PENDING'
        interview.application.save()
        messages.success(request, 'Interview canceled successfully.')
        return redirect('jobs:employer_interviews')
    
    return render(request, 'jobs/cancel_interview.html', {
        'interview': interview,
        'application': interview.application,
    })

def job_list(request):
    jobs = Job.objects.filter(is_active=True).order_by('-posted_date')
    context = {
        'jobs': jobs,
    }
    return render(request, 'jobs/job_list.html', context)

def job_detail(request, pk):
    job = get_object_or_404(Job, id=pk)
    is_closed = not job.is_accepting_applications()
    return render(request, 'jobs/job_detail.html', {
        'job': job,
        'is_closed': is_closed,
    })

@csrf_protect
@login_required
def application_detail(request, pk):
    application = get_object_or_404(Application, pk=pk)
    if request.user.is_student and application.student.user != request.user:
        messages.error(request, "You can only view your own applications.")
        return redirect('jobs:student_dashboard')
    elif request.user.is_employer and application.job.employer.user != request.user:
        messages.error(request, "You can only view applications for your jobs.")
        return redirect('jobs:employer_dashboard')
    return render(request, 'jobs/application_detail.html', {'application': application})




# @csrf_protect
# @login_required
# def resume_builder(request):
#     if not hasattr(request.user, 'studentprofile'):
#         messages.error(request, "Only students can access the resume builder.")
#         return redirect('jobs:job_list')
    
#     if request.method == 'POST':
#         form = ResumeForm(request.POST)
#         if form.is_valid():
#             latex_content = r"""
# \documentclass[a4paper,10pt]{article}
# \usepackage[utf8]{inputenc}
# \usepackage[T1]{fontenc}
# \usepackage[margin=1in]{geometry}
# \usepackage{titlesec}
# \usepackage{enumitem}
# \usepackage{xcolor}
# \usepackage{helvet}
# \renewcommand{\familydefault}{\sfdefault}

# \titleformat{\section}{\large\bfseries\color{blue!70}}{}{0em}{}[\titlerule]
# \setlist[itemize]{leftmargin=*,itemsep=0pt}
# \setlength{\parindent}{0pt}
# \setlength{\parskip}{6pt}

# \begin{document}
# \begin{center}
#     {\Large\bfseries """ + form.cleaned_data['first_name'] + " " + form.cleaned_data['last_name'] + r"""}\\[0.2cm]
#     """ + form.cleaned_data['email'] + r""" \textbullet\ """ + form.cleaned_data['phone'] + (r""" \textbullet\ """ + form.cleaned_data['address'] if form.cleaned_data['address'] else "") + r"""
# \end{center}

# \section*{Education}
# """ + form.cleaned_data['education'].replace('\n', r'\\') + r"""

# \section*{Experience}
# """ + form.cleaned_data['experience'].replace('\n', r'\\') + r"""

# \section*{Skills}
# \begin{itemize}
# """ + "".join([r"\item " + skill.strip() + "\n" for skill in form.cleaned_data['skills'].splitlines() if skill.strip()]) + r"""
# \end{itemize}

# """ + (r"""
# \section*{Additional Information}
# """ + form.cleaned_data['additional_info'].replace('\n', r'\\') if form.cleaned_data['additional_info'] else "") + r"""

# \end{document}
# """
#             with tempfile.TemporaryDirectory() as tmpdirname:
#                 tex_path = os.path.join(tmpdirname, 'resume.tex')
#                 pdf_path = os.path.join(tmpdirname, 'resume.pdf')

#                 with open(tex_path, 'w', encoding='utf-8') as f:
#                     f.write(latex_content)

#                 try:
#                     # Run pdflatex twice to resolve references properly
#                     for _ in range(2):
#                         subprocess.run(
#                             ['pdflatex', '-interaction=nonstopmode', tex_path],
#                             cwd=tmpdirname,
#                             check=True,
#                             stdout=subprocess.PIPE,
#                             stderr=subprocess.PIPE,
#                             text=True
#                         )

#                     with open(pdf_path, 'rb') as f:
#                         response = HttpResponse(f.read(), content_type='application/pdf')
#                         response['Content-Disposition'] = 'attachment; filename="resume.pdf"'
#                         return response

#                 except subprocess.CalledProcessError as e:
#                     messages.error(request, "Failed to generate resume PDF. Please try again.")
#                     print("LaTeX error output:", e.stderr)
#                     return render(request, 'jobs/resume_builder.html', {'form': form})
#         else:
#             messages.error(request, "Please correct the errors in the form.")
#     else:
#         form = ResumeForm()

#     return render(request, 'jobs/resume_builder.html', {'form': form})


# @csrf_protect
# @login_required
# def resume_builder(request):
#     if not hasattr(request.user, 'studentprofile'):
#         messages.error(request, "Only students can access the resume builder.")
#         return redirect('jobs:job_list')

#     # Helper: escape LaTeX special chars
#     def latex_escape(s: str) -> str:
#         if not s:
#             return ""
#         repl = {
#             '\\': r'\textbackslash{}',
#             '&': r'\&',
#             '%': r'\%',
#             '$': r'\$',
#             '#': r'\#',
#             '_': r'\_',
#             '{': r'\{',
#             '}': r'\}',
#             '~': r'\textasciitilde{}',
#             '^': r'\textasciicircum{}',
#         }
#         out = []
#         for ch in str(s):
#             out.append(repl.get(ch, ch))
#         return "".join(out)

#     sp = request.user.studentprofile

#     if request.method == 'POST':
#         form = ResumeForm(request.POST, user=request.user)
#         if form.is_valid():
#             edu_ids = [int(i) for i in form.cleaned_data.get('education_ids', [])]
#             exp_ids = [int(i) for i in form.cleaned_data.get('experience_ids', [])]

#             # Pull selected profile items (truncate to 2 for safety)
#             educations = list(getattr(sp, 'educations').filter(id__in=edu_ids)[:2]) if hasattr(sp, 'educations') else []
#             experiences = list(getattr(sp, 'experiences').filter(id__in=exp_ids)[:2]) if hasattr(sp, 'experiences') else []

#             # Parse skills into list
#             skills_lines = [s.strip() for s in form.cleaned_data['skills'].splitlines() if s.strip()]

#             # Theme
#             theme = form.cleaned_data.get('theme', 'ats')
#             accent_rgb = "0,0,0" if theme == 'ats' else "67,97,238"  # ATS=black; Modern=your primary blue

#             # Prepare LaTeX document
#             first = latex_escape(form.cleaned_data['first_name'])
#             last = latex_escape(form.cleaned_data['last_name'])
#             email = latex_escape(form.cleaned_data['email'])
#             phone = latex_escape(form.cleaned_data['phone'])
#             address = latex_escape(form.cleaned_data['address'])
#             addl = latex_escape(form.cleaned_data['additional_info']).replace('\n', r'\\')

#             def edu_block():
#                 lines = []
#                 for e in educations:
#                     degree = latex_escape(getattr(e, 'get_degree_display')() if callable(getattr(e, 'get_degree_display', None)) else getattr(e, 'degree', ''))
#                     fos = latex_escape(getattr(e, 'field_of_study', ''))
#                     inst = latex_escape(getattr(e, 'institution', ''))
#                     sy = latex_escape(getattr(e, 'start_year', ''))
#                     ey = "Present" if getattr(e, 'currently_studying', False) else latex_escape(getattr(e, 'end_year', ''))
#                     desc = latex_escape(getattr(e, 'description', '')).replace('\n', r'\\')
#                     line = rf"""\textbf{{{degree}}} in {fos} --- {inst} \hfill {sy}--{ey}\\
# \small {desc}"""
#                     lines.append(line)
#                 return r"\par ".join(lines) if lines else r"\emph{None selected}"

#             def exp_block():
#                 lines = []
#                 for x in experiences:
#                     title = latex_escape(getattr(x, 'title', ''))
#                     company = latex_escape(getattr(x, 'company', ''))
#                     sd = getattr(x, 'start_date', None)
#                     ed = getattr(x, 'end_date', None)
#                     date_str = ""
#                     try:
#                         sd_str = sd.strftime('%b %Y') if sd else ''
#                         ed_str = 'Present' if getattr(x, 'is_current', False) else (ed.strftime('%b %Y') if ed else '')
#                         date_str = f"{sd_str}--{ed_str}"
#                     except Exception:
#                         pass
#                     desc = latex_escape(getattr(x, 'description', '')).replace('\n', r'\\')
#                     line = rf"""\textbf{{{title}}} --- {company} \hfill {date_str}\\
# \small {desc}"""
#                     lines.append(line)
#                 return r"\par ".join(lines) if lines else r"\emph{None selected}"

#             # Build skills itemize
#             skill_items = "".join([rf"\item {latex_escape(s)}\n" for s in skills_lines])

#             latex_content = rf"""
# \documentclass[a4paper,10pt]{{article}}
# \usepackage[utf8]{{inputenc}}
# \usepackage[T1]{{fontenc}}
# \usepackage[margin=1in]{{geometry}}
# \usepackage[hidelinks]{{hyperref}}
# \usepackage{{titlesec}}
# \usepackage{{enumitem}}
# \usepackage{{xcolor}}
# \usepackage{{helvet}}
# \renewcommand\familydefault{{\sfdefault}}

# % Colors
# \definecolor{{Accent}}{{RGB}}{{{accent_rgb}}}

# % Section style
# \titleformat{{\section}}{{\large\bfseries\color{{Accent}}}}{{--}}{{0em}}{{}}[\titlerule]
# \titlespacing*{{\section}}{{0pt}}{{6pt}}{{6pt}}
# \setlist[itemize]{{leftmargin=*, itemsep=2pt, topsep=2pt}}
# \setlength{{\parindent}}{{0pt}}
# \setlength{{\parskip}}{{4pt}}

# \begin{{document}}
# \begin{{center}}
#     {{\LARGE\bfseries {first} {last}}}\\[0.2cm]
#     \href{{mailto:{email}}}{{{email}}} \textbullet\ {phone} \textbullet\ {address}
# \end{{center}}

# \section*{{Education}}
# {edu_block()}

# \section*{{Experience}}
# {exp_block()}

# \section*{{Skills}}
# \begin{{itemize}}
# {skill_items}
# \end{{itemize}}

# {"\\section*{Additional Information}\n" + addl if form.cleaned_data.get('additional_info') else ""}

# \end{{document}}
# """

#             # Compile with pdflatex
#             with tempfile.TemporaryDirectory() as tmpdirname:
#                 tex_path = os.path.join(tmpdirname, 'resume.tex')
#                 pdf_path = os.path.join(tmpdirname, 'resume.pdf')
#                 with open(tex_path, 'w', encoding='utf-8') as f:
#                     f.write(latex_content)
#                 try:
#                     for _ in range(2):
#                         subprocess.run(
#                             ['pdflatex', '-interaction=nonstopmode', 'resume.tex'],
#                             cwd=tmpdirname,
#                             check=True,
#                             stdout=subprocess.PIPE,
#                             stderr=subprocess.PIPE,
#                             text=True
#                         )
#                     with open(pdf_path, 'rb') as f:
#                         resp = HttpResponse(f.read(), content_type='application/pdf')
#                         resp['Content-Disposition'] = 'attachment; filename="resume.pdf"'
#                         return resp
#                 except subprocess.CalledProcessError as e:
#                     messages.error(request, "Failed to generate resume PDF. Please try again.")
#                     print("LaTeX error output:", e.stderr)
#                     return render(request, 'jobs/resume_builder.html', {'form': form})
#         else:
#             messages.error(request, "Please correct the errors in the form.")
#     else:
#         form = ResumeForm(user=request.user)

#     return render(request, 'jobs/resume_builder.html', {'form': form})

@csrf_protect
@login_required
def resume_builder(request):
    if not hasattr(request.user, 'studentprofile'):
        messages.error(request, "Only students can access the resume builder.")
        return redirect('jobs:job_list')

    sp = request.user.studentprofile

    def latex_escape(s: str) -> str:
        if not s:
            return ""
        repl = {
            '\\': r'\textbackslash{}',
            '&': r'\&',
            '%': r'\%',
            '$': r'\$',
            '#': r'\#',
            '_': r'\_',
            '{': r'\{',
            '}': r'\}',
            '~': r'\textasciitilde{}',
            '^': r'\textasciicircum{}',
        }
        out = []
        for ch in str(s):
            out.append(repl.get(ch, ch))
        return "".join(out)

    def fmt_month(d):
        try:
            return d.strftime('%b %Y') if d else ''
        except Exception:
            return ''

    # Build LaTeX (two themes; a minimal fallback avoids titlesec/titlerule)
    def build_latex(form, educations, experiences, theme='ats', minimal=False):
        first = latex_escape(form.cleaned_data['first_name'])
        last  = latex_escape(form.cleaned_data['last_name'])
        email = latex_escape(form.cleaned_data['email'])
        phone = latex_escape(form.cleaned_data['phone'])
        addr  = latex_escape(form.cleaned_data['address'])
        addl  = latex_escape(form.cleaned_data.get('additional_info', '')).replace('\n', r'\\')
        skills_lines = [s.strip() for s in form.cleaned_data['skills'].splitlines() if s.strip()]
        # skill_items = "".join([rf"\item {latex_escape(s)}\n" for s in skills_lines])
        skill_items = "\n".join([r"\item " + latex_escape(s) for s in skills_lines])

        def edu_block():
            lines = []
            for e in educations:
                try:
                    degree = e.get_degree_display()
                except Exception:
                    degree = getattr(e, 'degree', '') or ''
                fos  = latex_escape(getattr(e, 'field_of_study', '') or '')
                inst = latex_escape(getattr(e, 'institution', '') or '')
                sy   = latex_escape(getattr(e, 'start_year', '') or '')
                ey   = "Present" if getattr(e, 'currently_studying', False) else latex_escape(getattr(e, 'end_year', '') or '')
                line = rf"\textbf{{{latex_escape(degree)}}} in {fos} --- {inst} \hfill {sy}--{ey}"
                lines.append(line)
            return r"\par ".join(lines) if lines else r"\emph{None selected}"

        def exp_block():
            lines = []
            for x in experiences:
                title   = latex_escape(getattr(x, 'title', '') or '')
                company = latex_escape(getattr(x, 'company', '') or '')
                sd      = fmt_month(getattr(x, 'start_date', None))
                ed      = 'Present' if getattr(x, 'currently_working', False) else fmt_month(getattr(x, 'end_date', None))
                desc    = latex_escape(getattr(x, 'description', '') or '').replace('\n', r'\\')
                line = rf"\textbf{{{title}}} --- {company} \hfill {sd}--{ed}\\\small {desc}"
                lines.append(line)
            return r"\par ".join(lines) if lines else r"\emph{None selected}"

        accent_rgb = "0,0,0" if theme == 'ats' else "67,97,238"

        if minimal:
            # No titlesec, no titlerule — maximally compatible
            return rf"""
\documentclass[a4paper,10pt]{{article}}
\usepackage[utf8]{{inputenc}}
\usepackage[T1]{{fontenc}}
\usepackage[margin=1in]{{geometry}}
\usepackage[hidelinks]{{hyperref}}
\usepackage{{enumitem}}
\usepackage{{xcolor}}
\usepackage{{helvet}}
\renewcommand\familydefault{{\sfdefault}}
\definecolor{{Accent}}{{RGB}}{{{accent_rgb}}}
\setlength{{\parindent}}{{0pt}}
\setlength{{\parskip}}{{4pt}}

\begin{{document}}
\begin{{center}}
    {{\LARGE\bfseries {first} {last}}}\\[0.2cm]
    \href{{mailto:{email}}}{{{email}}} \textbullet\ {phone} \textbullet\ {addr}
\end{{center}}

{{\large\bfseries Education}}\par
{edu_block()}

{{\large\bfseries Experience}}\par
{exp_block()}

{{\large\bfseries Skills}}\par
\begin{{itemize}}
{skill_items}
\end{{itemize}}

{("\\n{\\large\\bfseries Additional Information}\\par\\n" + addl) if form.cleaned_data.get('additional_info') else ""}

\end{{document}}
"""
        else:
            # Pretty (uses titlesec + titlerule)
            return rf"""
\documentclass[a4paper,10pt]{{article}}
\usepackage[utf8]{{inputenc}}
\usepackage[T1]{{fontenc}}
\usepackage[margin=1in]{{geometry}}
\usepackage[hidelinks]{{hyperref}}
\usepackage{{titlesec}}
\usepackage{{enumitem}}
\usepackage{{xcolor}}
\usepackage{{helvet}}
\renewcommand\familydefault{{\sfdefault}}
\definecolor{{Accent}}{{RGB}}{{{accent_rgb}}}
\titleformat{{\section}}{{\large\bfseries\color{{Accent}}}}{{--}}{{0em}}{{}}[\titlerule]
\titlespacing*{{\section}}{{0pt}}{{6pt}}{{6pt}}
\setlist[itemize]{{leftmargin=*, itemsep=2pt, topsep=2pt}}
\setlength{{\parindent}}{{0pt}}
\setlength{{\parskip}}{{4pt}}

\begin{{document}}
\begin{{center}}
    {{\LARGE\bfseries {first} {last}}}\\[0.2cm]
    \href{{mailto:{email}}}{{{email}}} \textbullet\ {phone} \textbullet\ {addr}
\end{{center}}

\section*{{Education}}
{edu_block()}

\section*{{Experience}}
{exp_block()}

\section*{{Skills}}
\begin{{itemize}}
{skill_items}
\end{{itemize}}

{("\\n\\section*{Additional Information}\\n" + addl) if form.cleaned_data.get('additional_info') else ""}

\end{{document}}
"""

    if request.method == 'POST':
        form = ResumeForm(request.POST, user=request.user)
        if form.is_valid():
            # Fetch selected Education/Experience (limit to 2 server-side)
            edu_ids = [int(i) for i in form.cleaned_data.get('education_ids', [])][:2]
            exp_ids = [int(i) for i in form.cleaned_data.get('experience_ids', [])][:2]
            educations  = list(sp.educations.filter(id__in=edu_ids)) if hasattr(sp, 'educations') else []
            experiences = list(sp.experiences.filter(id__in=exp_ids)) if hasattr(sp, 'experiences') else []

            theme = form.cleaned_data.get('theme', 'ats')

            def compile_and_send(latex_content):
                with tempfile.TemporaryDirectory() as tmpdirname:
                    tex_path = os.path.join(tmpdirname, 'resume.tex')
                    pdf_path = os.path.join(tmpdirname, 'resume.pdf')
                    with open(tex_path, 'w', encoding='utf-8') as f:
                        f.write(latex_content)
                    try:
                        for _ in range(2):
                            subprocess.run(
                                ['pdflatex', '-interaction=nonstopmode', 'resume.tex'],
                                cwd=tmpdirname,
                                check=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True
                            )
                        with open(pdf_path, 'rb') as f:
                            resp = HttpResponse(f.read(), content_type='application/pdf')
                            resp['Content-Disposition'] = 'attachment; filename="resume.pdf"'
                            return resp, None
                    except subprocess.CalledProcessError as e:
                        log = (e.stdout or '') + '\n' + (e.stderr or '')
                        return None, log

            # Try pretty template first
            latex_pretty = build_latex(form, educations, experiences, theme=theme, minimal=False)
            resp, log = compile_and_send(latex_pretty)
            if resp:
                return resp

            # If titlesec/titlerule missing, fall back to minimal
            if log and ('titlesec.sty' in log or 'Undefined control sequence' in log):
                latex_min = build_latex(form, educations, experiences, theme=theme, minimal=True)
                resp2, log2 = compile_and_send(latex_min)
                if resp2:
                    return resp2
                else:
                    messages.error(request, "Failed to generate resume PDF. Please see LaTeX errors below.")
                    return render(request, 'jobs/resume_builder.html', {'form': form, 'latex_error': (log2 or log)[:8000]})

            # Otherwise show the actual error log
            messages.error(request, "Failed to generate resume PDF. Please see LaTeX errors below.")
            return render(request, 'jobs/resume_builder.html', {'form': form, 'latex_error': (log or '')[:8000]})
        else:
            messages.error(request, "Please correct the errors in the form.")
            return render(request, 'jobs/resume_builder.html', {'form': form})

    else:
        form = ResumeForm(user=request.user)
        return render(request, 'jobs/resume_builder.html', {'form': form})




