from datetime import date

from django.test import TestCase
from django.urls import reverse

from .dates import parse_date_string
from .models import IntakeSubmission


def valid_submission(**overrides):
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


class IntakeLanguageWorkflowTests(TestCase):
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
        response = self.client.post(reverse('intake_form'), valid_submission())

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
            valid_submission(language='unsupported'),
        )

        self.assertRedirects(response, reverse('intake_success'))
        self.assertEqual(IntakeSubmission.objects.get().language_preference, 'en')


class LegacyDateParsingTests(TestCase):
    """Covers the parse helper the 0011 data migration uses."""

    def test_iso_values_parse(self):
        self.assertEqual(parse_date_string('1990-01-01'), date(1990, 1, 1))

    def test_us_slash_format_parses(self):
        self.assertEqual(parse_date_string('03/04/1990'), date(1990, 3, 4))

    def test_day_first_slash_format_parses_when_day_exceeds_twelve(self):
        self.assertEqual(parse_date_string('25/12/1990'), date(1990, 12, 25))

    def test_surrounding_whitespace_is_tolerated(self):
        self.assertEqual(parse_date_string('  1990-01-01  '), date(1990, 1, 1))

    def test_empty_and_unparseable_values_return_none(self):
        for raw in ('', '   ', None, 'not-a-date', '1990-13-45'):
            self.assertIsNone(parse_date_string(raw), raw)


class IntakeDateFieldTests(TestCase):
    def test_valid_dates_are_stored_as_date_objects(self):
        response = self.client.post(
            reverse('intake_form'),
            valid_submission(next_hearing_date='2026-09-15'),
        )

        self.assertRedirects(response, reverse('intake_success'))
        submission = IntakeSubmission.objects.get()
        self.assertEqual(submission.date_of_birth, date(1990, 1, 1))
        self.assertEqual(submission.next_hearing_date, date(2026, 9, 15))

    def test_blank_hearing_date_is_stored_as_null(self):
        self.client.post(reverse('intake_form'), valid_submission())

        self.assertIsNone(IntakeSubmission.objects.get().next_hearing_date)

    def test_invalid_date_is_rejected_without_creating_a_row(self):
        response = self.client.post(
            reverse('intake_form'),
            valid_submission(language='en', date_of_birth='not-a-date'),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Enter a valid date.')
        self.assertEqual(IntakeSubmission.objects.count(), 0)

    def test_invalid_date_error_is_translated(self):
        # Fails if the .mo catalogs were never compiled.
        response = self.client.post(
            reverse('intake_form'),
            valid_submission(language='ht', date_of_birth='not-a-date'),
        )

        self.assertContains(response, 'Antre yon dat valab.')
        self.assertEqual(IntakeSubmission.objects.count(), 0)


class RootRedirectTests(TestCase):
    def test_root_redirects_to_intake_form(self):
        response = self.client.get('/')
        self.assertRedirects(response, reverse('intake_form'))


class IntakeTranslationRenderingTests(TestCase):
    def test_spanish_locale_renders_translated_form(self):
        # Fails if the .mo catalogs were never compiled — the heading falls back to English.
        response = self.client.get(reverse('intake_form'), headers={'Accept-Language': 'es'})

        self.assertContains(response, 'Información personal')
