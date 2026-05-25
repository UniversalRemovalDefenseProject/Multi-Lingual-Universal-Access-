from django.test import TestCase
from django.urls import reverse

from .models import IntakeSubmission


class IntakeLanguageWorkflowTests(TestCase):
    def _valid_submission(self, **overrides):
        values = {
            'language': 'es',
            'full_name': 'Maria Example',
            'date_of_birth': '1990-01-01',
            'country_of_origin': 'Venezuela',
            'preferred_language': 'Spanish',
            'phone': '',
            'email': '',
            'current_location': '',
            'immigration_court': '',
            'a_number': '',
            'next_hearing_date': '',
            'fear_of_return_summary': 'Original response in the applicant language.',
            'past_harm_summary': '',
            'countries_traveled_asylum_summary': 'Mexico',
            'consent_acknowledged': 'on',
        }
        values.update(overrides)
        return values

    def test_language_change_preserves_draft_values_and_sets_cookie(self):
        response = self.client.post(
            reverse('intake_form'),
            {
                'language': 'ar',
                'form_action': 'change_language',
                'full_name': 'Draft Applicant',
                'fear_of_return_summary': 'Draft narrative',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="Draft Applicant"')
        self.assertContains(response, 'dir="rtl"')
        self.assertEqual(response.cookies['urdp_language'].value, 'ar')
        self.assertEqual(IntakeSubmission.objects.count(), 0)

    def test_submission_stores_interface_language_and_original_responses(self):
        response = self.client.post(reverse('intake_form'), self._valid_submission())

        self.assertRedirects(response, reverse('intake_success'))
        submission = IntakeSubmission.objects.get()
        self.assertEqual(submission.language_preference, 'es')
        self.assertEqual(
            submission.fear_of_return_summary,
            'Original response in the applicant language.',
        )
        self.assertEqual(submission.fear_of_return_summary_translated, '')
        self.assertEqual(response.cookies['urdp_language'].value, 'es')

    def test_invalid_language_falls_back_to_supported_default(self):
        response = self.client.post(
            reverse('intake_form'),
            self._valid_submission(language='unsupported'),
        )

        self.assertRedirects(response, reverse('intake_success'))
        self.assertEqual(IntakeSubmission.objects.get().language_preference, 'en')
