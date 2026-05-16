from django import forms
from .models import IntakeSubmission

class IntakeSubmissionForm(forms.ModelForm):
    class Meta:
        model = IntakeSubmission
        fields = [
            'full_name',
            'date_of_birth',
            'country_of_origin',
            'preferred_language',
            'phone',
            'email',
            'current_location',
            'detained',
            'immigration_court',
            'a_number',
            'next_hearing_date',
            'fear_of_return_summary',
            'past_harm_summary',
            'family_members_included',
            'consent_acknowledged',
        ]