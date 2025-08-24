from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse
from .models import Job, StudentNotification
from accounts.models import StudentProfile
from jobs.models import UserSettings  # wherever your UserSettings lives

# @receiver(post_save, sender=Job)
# def notify_students_on_new_job(sender, instance: Job, created, **kwargs):
#     if not created:
#         return  # only on new job posts

#     # Only notify for active jobs (optional safety)
#     if not getattr(instance, 'is_active', True):
#         return

#     # Students who opted in
#     qs = StudentProfile.objects.select_related('user').filter(
#         usersettings__notify_job_updates=True
#     )

#     # Build message + URL to job detail
#     from django.urls import reverse
#     url = reverse('jobs:job_detail', args=[instance.pk])
#     msg = f"New job posted: {instance.title} at {instance.employer.company_name}"

#     batch = [
#         StudentNotification(student=sp, message=msg, url=url)
#         for sp in qs
#     ]
#     if batch:
#         StudentNotification.objects.bulk_create(batch, ignore_conflicts=True)

@receiver(post_save, sender=Job)
def notify_students_on_job_post(sender, instance: Job, created, **kwargs):
    if not created:
        return

    #  use the correct reverse name: 'settings'
    students = (StudentProfile.objects
                .select_related('user', 'settings')
                .filter(settings__notify_job_updates=True))

    # build notifications (bulk)
    notes = [
        StudentNotification(
            student=s,
            job=instance,
            message=f"New {instance.get_job_type_display()} posted: {instance.title} at {instance.employer.company_name}",
            url=reverse('jobs:job_detail', args=[instance.pk])
        )
        for s in students
    ]
    StudentNotification.objects.bulk_create(notes, ignore_conflicts=True)
