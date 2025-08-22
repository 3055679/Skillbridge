import random
from django.db.models import Q
from django.conf import settings
from urllib.parse import urljoin
from django.urls import reverse
from django.core.mail import send_mail
from django.core.signing import TimestampSigner

from .models import (
    Assessment,
    AssessmentBlueprint,
    Question,
    Task,
    ApplicantChosenSkill,   # ✅ NEW
)
from accounts.models import Skill  # main Skill model used on Question.skills


def freeze_question(q: Question):
    return {
        "id": q.id,
        "qtype": q.qtype,
        "text": q.text,
        "choices": q.choices,
        "language": q.language,
        "starter": q.starter_code,
        "tests": q.tests,
        "section": q.section,
    }


def freeze_task(t: Task):
    return {
        "id": t.id,
        "ttype": t.ttype,
        "title": t.title,
        "instructions": t.instructions,
        "artifact_type": t.artifact_type,
        "rubric": t.rubric,
        "max_score": t.max_score,
    }


def pick_for_internship(skills_qs, blueprint: AssessmentBlueprint):
    # e.g. {"mcq": 12, "short": 2, "code":{"enabled":true,"languages":["python","js"]}}
    rules = blueprint.rules
    chosen = []

    # MCQ by skill, backfill with fundamentals (no skill)
    mcq_total = rules.get("mcq", 12)
    q_mcq = Question.objects.filter(active=True, qtype="mcq", skills__in=skills_qs).distinct()
    if q_mcq.count() < mcq_total:
        backfill = Question.objects.filter(active=True, qtype="mcq", skills__isnull=True)
        pool = list(q_mcq) + list(backfill)
    else:
        pool = list(q_mcq)
    random.shuffle(pool)
    chosen += [freeze_question(q) for q in pool[:mcq_total]]

    # Short
    short_total = rules.get("short", 2)
    q_short = list(Question.objects.filter(active=True, qtype="short").order_by("?")[:short_total])
    chosen += [freeze_question(q) for q in q_short]

    # Code (optional)
    code_cfg = rules.get("code", {"enabled": False})
    if code_cfg.get("enabled"):
        langs = code_cfg.get("languages", [])
        q_code = Question.objects.filter(active=True, qtype="code")
        if langs:
            q_code = q_code.filter(language__in=langs)
        q_code = list(q_code.order_by("?")[:1])
        chosen += [freeze_question(q) for q in q_code]

    return chosen


def pick_for_gig(skills_qs, blueprint: AssessmentBlueprint):
    rules = blueprint.rules  # has sections
    frozen_tasks, frozen_questions = [], []

    for sec in rules.get("sections", []):
        typ = sec["type"]
        count = sec.get("count", 1)

        if typ in ["upload", "critique"]:
            qs = Task.objects.filter(active=True, ttype=typ)
            if blueprint.role_id:
                qs = qs.filter(role_id=blueprint.role_id)
            if hasattr(skills_qs, "exists") and skills_qs.exists():
                qs = qs.filter(Q(skills__in=skills_qs) | Q(skills__isnull=True)).distinct()
            pool = list(qs.order_by("?")[:count])
            frozen_tasks += [freeze_task(t) for t in pool]

        elif typ in ["mcq", "short", "code"]:
            q = Question.objects.filter(active=True, qtype=typ)
            if typ == "mcq" and sec.get("skills"):
                q = q.filter(skills__name__in=sec["skills"]).distinct()
            if typ == "code" and sec.get("constraints", {}).get("language_opts"):
                q = q.filter(language__in=sec["constraints"]["language_opts"])
            pool = list(q.order_by("?")[:count])
            frozen_questions += [freeze_question(x) for x in pool]

    return frozen_questions, frozen_tasks


def _absolute_url(path: str) -> str:
    base = getattr(settings, "BASE_URL", "http://localhost:8000")
    return urljoin(base, path)


def create_assessment_for_application(application, blueprint: AssessmentBlueprint) -> Assessment:
    """
    Skill source priority:
      1) ApplicantChosenSkill for this application (new dropdown)
      2) Fallback to StudentProfile.skills
    """

    # ✅ 1) Try the new assessment-only picks first (ApplicantChosenSkill)
    chosen = ApplicantChosenSkill.objects.filter(application=application).select_related("skill")
    if chosen.exists():
        chosen_names = [c.skill.name for c in chosen]
        # Map to main Skill model used by Question.skills
        skills_qs = Skill.objects.filter(name__in=chosen_names)
    else:
        # ✅ 2) Fallback to StudentProfile.skills
        profile = application.student  # adjust if your field name differs
        skills_qs = profile.skills.all()

    # Build assessment payload
    if blueprint.kind == "internship":
        questions = pick_for_internship(skills_qs, blueprint)
        tasks = None
    else:
        questions, tasks = pick_for_gig(skills_qs, blueprint)

    # Token & record
    signer = TimestampSigner()
    # Be robust: if student_id attr not present, fallback to pk
    sid = getattr(application, "student_id", None) or application.student.pk
    token = signer.sign(f"{application.id}:{sid}")

    assessment = Assessment.objects.create(
        application=application,
        blueprint=blueprint,
        questions=questions,
        tasks=tasks,
        token=token,
        duration_minutes=blueprint.duration_minutes,
        status="invited",
    )

    # Email invite
    link = _absolute_url(reverse("assessments:assessment_take", args=[assessment.token]))
    send_mail(
        subject="Your assessment invitation",
        message=f"Start your assessment here: {link}\nDuration: {assessment.duration_minutes} minutes.",
        from_email="noreply@your.site",
        recipient_list=[application.student.user.email],
    )

    return assessment
