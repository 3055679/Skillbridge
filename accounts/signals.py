# accounts/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import StudentProfile

@receiver(post_save, sender=StudentProfile)
def activate_user_when_verified(sender, instance, **kwargs):
    # If verified and user still inactive, activate them
    if instance.student_id_verified and not instance.user.is_active:
        u = instance.user
        u.is_active = True
        u.is_verified = True
        u.save()
