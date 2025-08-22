from django.core.management.base import BaseCommand
from assessments.models import AssessmentSkill

SKILLS = [
    "Algorithms",
    "CSS",
    "Django",
    "JavaScript",
    "Python",
    "React",
]

class Command(BaseCommand):
    help = "Seed assessment-only skills list (alphabetical)"

    def handle(self, *args, **kwargs):
        for name in sorted(SKILLS):
            AssessmentSkill.objects.get_or_create(name=name)
        self.stdout.write(self.style.SUCCESS("Seeded assessment skills."))
