from django.db import models

# Create your models here.
from django.db import models

class IntakeSubmission(models.Model):
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
    family_members_included = models.BooleanField(default=False)
    consent_acknowledged = models.BooleanField(default=False)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='new')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_name
