from django.db import models
from django.utils.translation import gettext_lazy as _


class IntakeSubmission(models.Model):
    LANGUAGE_CHOICES = [
        ('en', _('English')),
        ('es', _('Spanish')),
        ('fr', _('French')),
        ('ar', _('Arabic')),
        ('ht', _('Haitian Creole')),
        ('ru', _('Russian')),
        ('hi', _('Hindi')),
        ('pa', _('Punjabi')),
        ('pt', _('Portuguese')),
        ('zh-hans', _('Chinese (Simplified)')),
    ]

    STATUS_CHOICES = [
        ('new', 'New'),
        ('conflict_check', 'Needs Conflict Check'),
        ('translation_review', 'Needs Translation Review'),
        ('legal_review', 'Needs Legal Review'),
        ('accepted', 'Accepted'),
        ('referred', 'Referred'),
        ('closed', 'Closed'),
    ]

    full_name = models.CharField(max_length=255)
    date_of_birth = models.CharField(max_length=100,blank=True)
    country_of_origin = models.CharField(max_length=255)
    preferred_language = models.CharField(max_length=100)
    language_preference = models.CharField(
        max_length=10,
        choices=LANGUAGE_CHOICES,
        default='en',
        help_text=_('Language used while completing the intake form.'),
    )
    phone = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    current_location = models.CharField(max_length=255, blank=True)
    detained = models.BooleanField(default=False)
    immigration_court = models.CharField(max_length=255, blank=True)
    a_number = models.CharField(max_length=50, blank=True)
    next_hearing_date = models.CharField(max_length=100, blank=True)
    fear_of_return_summary = models.TextField()
    past_harm_summary = models.TextField(blank=True)
    countries_traveled_asylum_summary = models.TextField(blank=True)
    # Staff translations are stored separately so the applicant's wording is preserved.
    fear_of_return_summary_translated = models.TextField(
        blank=True,
        help_text=_('Staff translation only. The original response is preserved separately.'),
    )
    past_harm_summary_translated = models.TextField(
        blank=True,
        help_text=_('Staff translation only. The original response is preserved separately.'),
    )
    countries_traveled_asylum_summary_translated = models.TextField(
        blank=True,
        help_text=_('Staff translation only. The original response is preserved separately.'),
    )
    translated_response_language = models.CharField(
        max_length=10,
        blank=True,
        choices=LANGUAGE_CHOICES,
        help_text=_('Language of any staff-entered translated responses.'),
    )
    family_members_included = models.BooleanField(default=False)
    consent_acknowledged = models.BooleanField(default=False)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='new')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_name
