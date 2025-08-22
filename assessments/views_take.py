import logging
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from django.contrib import messages
from django.views.decorators.csrf import csrf_protect
from django.http import JsonResponse
from django.urls import reverse
from .models import Assessment, Response
from .scoring import score_and_generate_report

# Set up logging
logger = logging.getLogger(__name__)

@csrf_protect
def assessment_take(request, token):
    assessment = get_object_or_404(Assessment, token=token)
    if assessment.status == "submitted":
        messages.error(request, "You have already completed this assessment.")
        return redirect("jobs:my_applications")
    
    if assessment.status == "invited":
        assessment.status = "started"
        assessment.started_at = timezone.now()
        assessment.save()
        logger.debug("Assessment %s started at %s for user %s", 
                     assessment.id, assessment.started_at, 
                     request.user if request.user.is_authenticated else "anonymous")

    # Check responses for enabling submit button
    if request.GET.get('check_responses'):
        response_count = assessment.responses.count()
        logger.debug("Checked responses for assessment %s: %s", assessment.id, response_count)
        return JsonResponse({'response_count': response_count})

    if request.method == "POST":
        logger.debug("POST data: %s, user: %s", 
                     dict(request.POST), 
                     request.user if request.user.is_authenticated else "anonymous")
        response_count = 0
        expected_questions = len(assessment.questions or [])
        expected_tasks = len(assessment.tasks or [])
        
        # Save question responses
        for q in (assessment.questions or []):
            field = f"q_{q['id']}"
            if field in request.POST:
                ans = request.POST.get(field).strip()
                if ans:  # Only save non-empty answers
                    Response.objects.update_or_create(
                        assessment=assessment,
                        ref_type="q",
                        ref_id=q["id"],
                        defaults={"answer": ans}
                    )
                    response_count += 1
                    logger.debug("Saved response for question %s: %s", q["id"], ans)
                else:
                    logger.debug("Empty answer for question %s", q["id"])
            else:
                logger.debug("No field %s in POST data", field)
        
        # Save task responses
        for t in (assessment.tasks or []):
            field = f"t_{t['id']}"
            if field in request.POST:
                ans = request.POST.get(field).strip()
                if ans:
                    Response.objects.update_or_create(
                        assessment=assessment,
                        ref_type="t",
                        ref_id=t["id"],
                        defaults={"answer": ans}
                    )
                    response_count += 1
                    logger.debug("Saved response for task %s: %s", t["id"], ans)
                else:
                    logger.debug("Empty answer for task %s", t["id"])
            else:
                logger.debug("No field %s in POST data", field)

        if response_count > 0:
            messages.success(request, f"Saved {response_count} answers out of {expected_questions + expected_tasks} questions/tasks.")
        else:
            messages.warning(request, "No answers were saved. Please provide at least one answer.")
            logger.warning("No responses saved for assessment %s", assessment.id)
        
        return redirect("assessments:assessment_take", token=token)

    # Load existing responses for form repopulation
    responses = assessment.responses.all()
    logger.debug("Loaded %s responses for assessment %s, user: %s", 
                 responses.count(), assessment.id, 
                 request.user if request.user.is_authenticated else "anonymous")
    return render(request, "assessments/take.html", {"assessment": assessment, "responses": responses})

@csrf_protect
def assessment_submit(request, token):
    assessment = get_object_or_404(Assessment, token=token)
    
    logger.debug("Submitting assessment %s, user: %s", 
                 assessment.id, 
                 request.user if request.user.is_authenticated else "anonymous")
    
    if assessment.status == "submitted":
        messages.error(request, "You have already completed this assessment.")
        return redirect("jobs:my_applications")
    
    responses = assessment.responses.all()
    if not responses.exists():
        messages.error(request, "Cannot submit: No answers provided. Please save at least one answer.")
        logger.warning("Assessment %s submission attempted with no responses", assessment.id)
        return redirect("assessments:assessment_take", token=token)
    
    assessment.status = "submitted"
    assessment.submitted_at = timezone.now()
    assessment.save()
    logger.debug("Assessment %s submitted at %s", assessment.id, assessment.submitted_at)

    try:
        report = score_and_generate_report(assessment)
        logger.debug("Report generated for assessment %s: score=%s", assessment.id, report.total_score)
    except Exception as e:
        logger.error("Error generating report for assessment %s: %s", assessment.id, str(e))
        messages.error(request, "Error generating report. Please contact support.")
        return redirect("jobs:my_applications")

    messages.success(request, "Submitted successfully. Your report has been emailed.")
    
    # Ensure redirect to my_applications with authentication check
    if not request.user.is_authenticated:
        logger.warning("User not authenticated during submission of assessment %s", assessment.id)
        return redirect(f"{reverse('accounts:login')}?next={reverse('jobs:my_applications')}")
    
    return redirect("jobs:my_applications")