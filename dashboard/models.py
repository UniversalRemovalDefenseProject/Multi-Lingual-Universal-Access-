from django.conf import settings
from django.db import models

from intake.models import IntakeSubmission


class StaffNote(models.Model):
    intake = models.ForeignKey(
        IntakeSubmission,
        on_delete=models.CASCADE,
        related_name='staff_notes',
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
    )
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
