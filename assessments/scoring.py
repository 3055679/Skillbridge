import logging
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from .models import Assessment, Response, Report, Question

logger = logging.getLogger(__name__)

def score_and_generate_report(assessment: Assessment) -> Report:
    responses = assessment.responses.filter(ref_type="q")
    logger.debug("Found %d responses for assessment %s", responses.count(), assessment.id)
    
    total = 0.0
    per_skill = {}
    per_section = {"technical": 0.0, "hr": 0.0, "aptitude": 0.0}  # Initialize sections
    
    if not responses.exists():
        summary = "No responses submitted."
        per_skill = {"No skills": 0.0}
    else:
        q_map = {q.id: q for q in Question.objects.filter(id__in=[r.ref_id for r in responses], active=True)}
        logger.debug("Questions mapped: %s", list(q_map.keys()))

        for r in responses:
            q = q_map.get(r.ref_id)
            if not q:
                logger.warning("No question found for response %s (ref_id=%s)", r.id, r.ref_id)
                continue
            if q.qtype == "mcq":
                # Robust comparison: case-insensitive, trimmed
                submitted_answer = str(r.answer).strip().lower()
                correct_answer = str(q.answer_key).strip().lower()
                r.is_correct = submitted_answer == correct_answer
                r.score = 10.0 if r.is_correct else 0.0
                r.save()
                total += r.score
                per_section[q.section] = per_section.get(q.section, 0.0) + r.score
                for s in q.skills.all():
                    per_skill[s.name] = per_skill.get(s.name, 0.0) + r.score
                logger.debug("Scored MCQ response %s: answer='%s', correct='%s', is_correct=%s, score=%s", 
                            r.id, submitted_answer, correct_answer, r.is_correct, r.score)
            elif q.qtype == "short":
                # Placeholder: Assign a temporary score for testing
                r.score = 5.0  # Temporary score to avoid 0.0; replace with manual/AI scoring
                r.save()
                total += r.score
                per_section[q.section] = per_section.get(q.section, 0.0) + r.score
                for s in q.skills.all():
                    per_skill[s.name] = per_skill.get(s.name, 0.0) + r.score
                logger.debug("Scored short answer response %s: score=%s (placeholder)", r.id, r.score)
            elif q.qtype == "code":
                # Placeholder: Assign a temporary score for testing
                r.score = 5.0  # Temporary score to avoid 0.0; replace with code evaluation
                r.save()
                total += r.score
                per_section[q.section] = per_section.get(q.section, 0.0) + r.score
                for s in q.skills.all():
                    per_skill[s.name] = per_skill.get(s.name, 0.0) + r.score
                logger.debug("Scored code response %s: score=%s (placeholder)", r.id, r.score)

    # Score tasks (placeholder for testing)
    task_responses = assessment.responses.filter(ref_type="t")
    if task_responses.exists():
        for r in task_responses:
            r.score = 5.0  # Temporary score to avoid 0.0; replace with rubric-based scoring
            r.save()
            total += r.score
            per_section["tasks"] = per_section.get("tasks", 0.0) + r.score
            logger.debug("Scored task response %s: score=%s (placeholder)", r.id, r.score)

    max_score = (len(responses.filter(ref_type="q")) * 10.0) + (len(task_responses) * 5.0)
    summary = f"Score: {total:.1f} out of {max_score:.1f}."

    report = Report.objects.create(
        assessment=assessment,
        total_score=total,
        per_skill=per_skill if per_skill else {"No skills": 0.0},
        per_section=per_section,
        summary=summary
    )
    logger.debug("Report created: ID=%s, score=%s, per_skill=%s, per_section=%s", 
                 report.id, report.total_score, report.per_skill, report.per_section)

    # Email report to student
    ctx = {"assessment": assessment, "report": report}
    html = render_to_string("assessments/report_email.html", ctx)
    msg = EmailMultiAlternatives(
        subject="Your Assessment Report",
        body=summary,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@skillbridge.com"),
        to=[assessment.application.student.user.email],
    )
    msg.attach_alternative(html, "text/html")
    msg.send(fail_silently=True)
    logger.debug("Sent report email to %s", assessment.application.student.user.email)

    # Notify employer
    msg_employer = EmailMultiAlternatives(
        subject="New Assessment Report",
        body=f"Assessment report for {assessment.application.student.user.username} on {assessment.application.job.title}.",
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@skillbridge.com"),
        to=[assessment.application.job.employer.user.email],
    )
    msg_employer.send(fail_silently=True)
    logger.debug("Sent employer notification to %s", assessment.application.job.employer.user.email)

    return report