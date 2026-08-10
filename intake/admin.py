from django.contrib import admin

from .models import IntakeSubmission


@admin.register(IntakeSubmission)
class IntakeSubmissionAdmin(admin.ModelAdmin):
    list_display = (
        'full_name',
        'language_preference',
        'preferred_language',
        'country_of_origin',
        'detained',
        'status',
        'assigned_to',
        'created_at',
    )
    list_filter = ('language_preference', 'preferred_language', 'detained', 'status', 'created_at')
    search_fields = ('full_name', 'country_of_origin', 'a_number', 'email', 'phone')
    fieldsets = (
        (
            'Submission',
            {
                'fields': (
                    'full_name',
                    'date_of_birth',
                    'country_of_origin',
                    'preferred_language',
                    'language_preference',
                    'phone',
                    'email',
                    'current_location',
                    'detained',
                    'immigration_court',
                    'a_number',
                    'next_hearing_date',
                    'family_members_included',
                    'consent_acknowledged',
                    'status',
                    'assigned_to',
                )
            },
        ),
        (
            'Original narrative responses',
            {
                'fields': (
                    'fear_of_return_summary',
                    'past_harm_summary',
                    'countries_traveled_asylum_summary',
                )
            },
        ),
        (
            'Staff translations',
            {
                'fields': (
                    'translated_response_language',
                    'fear_of_return_summary_translated',
                    'past_harm_summary_translated',
                    'countries_traveled_asylum_summary_translated',
                ),
                'description': 'Enter translations here without replacing the applicant original wording.',
            },
        ),
    )
