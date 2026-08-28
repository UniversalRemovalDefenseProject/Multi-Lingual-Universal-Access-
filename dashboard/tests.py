from django.contrib.auth.models import Group, User
from django.db import connection
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from dashboard.models import StaffNote
from intake.models import IntakeSubmission


def make_submission(**overrides):
    values = {
        'full_name': 'Maria Example',
        'country_of_origin': 'Venezuela',
        'preferred_language': 'Spanish',
        'fear_of_return_summary': 'Original response in the applicant language.',
    }
    values.update(overrides)
    return IntakeSubmission.objects.create(**values)


def make_full_submission(**overrides):
    """Every field populated, so a render test can prove nothing was skipped."""
    values = {
        'full_name': 'Maria Example',
        'date_of_birth': '1990-01-01',
        'country_of_origin': 'Venezuela',
        'preferred_language': 'Spanish',
        'language_preference': 'es',
        'phone': '+1-555-0100',
        'email': 'maria@example.test',
        'current_location': 'Houston',
        'detained': True,
        'immigration_court': 'Houston Immigration Court',
        'a_number': 'A-000-000-000',
        'next_hearing_date': '2026-09-01',
        'fear_of_return_summary': 'Original fear narrative.',
        'past_harm_summary': 'Original past harm narrative.',
        'countries_traveled_asylum_summary': 'Original travel narrative.',
        'family_members_included': True,
        'consent_acknowledged': True,
        'status': 'legal_review',
    }
    values.update(overrides)
    return IntakeSubmission.objects.create(**values)


def make_case_manager(username='manager', password='not-a-real-password'):
    user = User.objects.create_user(username=username, password=password)
    user.groups.add(Group.objects.get(name='Case Manager'))
    return user


class DashboardAccessTests(TestCase):
    def test_anonymous_is_redirected_to_login(self):
        response = self.client.get(reverse('dashboard:queue'))

        self.assertRedirects(
            response,
            f'{reverse("dashboard:login")}?next={reverse("dashboard:queue")}',
        )

    def test_login_without_next_lands_on_the_queue(self):
        user = User.objects.create_user(username='manager', password='not-a-real-password')
        user.groups.add(Group.objects.get(name='Case Manager'))

        response = self.client.post(
            reverse('dashboard:login'),
            {'username': 'manager', 'password': 'not-a-real-password'},
        )

        self.assertRedirects(response, reverse('dashboard:queue'))

    def test_logout_returns_to_the_dashboard_login(self):
        User.objects.create_user(username='clerk', password='not-a-real-password')
        self.client.login(username='clerk', password='not-a-real-password')

        response = self.client.post(reverse('dashboard:logout'))

        self.assertRedirects(response, reverse('dashboard:login'))

    def test_authenticated_without_permission_gets_403(self):
        User.objects.create_user(username='clerk', password='not-a-real-password')
        self.client.login(username='clerk', password='not-a-real-password')

        response = self.client.get(reverse('dashboard:queue'))

        self.assertEqual(response.status_code, 403)

    def test_case_manager_group_member_gets_200(self):
        # Also asserts the data migration created the group with the permission attached.
        user = User.objects.create_user(username='manager', password='not-a-real-password')
        user.groups.add(Group.objects.get(name='Case Manager'))
        self.client.login(username='manager', password='not-a-real-password')

        response = self.client.get(reverse('dashboard:queue'))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(user.has_perm('intake.access_dashboard'))


class CaseQueueTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(username='manager', password='not-a-real-password')
        user.groups.add(Group.objects.get(name='Case Manager'))
        self.client.login(username='manager', password='not-a-real-password')

    def test_queue_lists_newest_submission_first(self):
        make_submission(full_name='Older Applicant')
        make_submission(full_name='Newer Applicant')

        content = self.client.get(reverse('dashboard:queue')).content.decode()

        self.assertLess(content.index('Newer Applicant'), content.index('Older Applicant'))

    def test_valid_status_filters_the_queue(self):
        make_submission(full_name='Accepted Applicant', status='accepted')
        make_submission(full_name='New Applicant', status='new')

        response = self.client.get(reverse('dashboard:queue'), {'status': 'accepted'})

        self.assertContains(response, 'Accepted Applicant')
        self.assertNotContains(response, 'New Applicant')
        self.assertContains(
            response, '<option value="accepted" selected>Accepted</option>', html=True
        )

    def test_unrecognized_status_falls_back_to_unfiltered(self):
        make_submission(full_name='Accepted Applicant', status='accepted')
        make_submission(full_name='New Applicant', status='new')

        response = self.client.get(reverse('dashboard:queue'), {'status': "evil'--"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Accepted Applicant')
        self.assertContains(response, 'New Applicant')
        # "All" is selected and the rejected value is never echoed back into the page.
        self.assertContains(response, '<option value="" selected>All statuses</option>', html=True)
        self.assertNotContains(response, 'evil')

    def test_queue_shows_a_number_or_placeholder(self):
        make_submission(full_name='With Number', a_number='A-123-456-789')
        make_submission(full_name='Without Number', a_number='')

        response = self.client.get(reverse('dashboard:queue'))

        self.assertContains(response, '<th scope="col">A-number</th>', html=True)
        self.assertContains(response, 'A-123-456-789')
        self.assertContains(response, '&mdash;')

    def test_arabic_applicant_text_renders_isolated_and_intact(self):
        arabic_name = 'محمد الأحمد'
        make_submission(full_name=arabic_name, country_of_origin='سوريا')

        response = self.client.get(reverse('dashboard:queue'))

        # Name appears on the page inside a dir="auto" cell.
        self.assertContains(response, arabic_name)
        self.assertContains(response, 'dir="auto"')
        self.assertContains(response, '<html lang="en" dir="ltr">')


class CaseQueueAssigneeTests(TestCase):
    def setUp(self):
        self.manager = make_case_manager()
        self.client.login(username='manager', password='not-a-real-password')

    def test_unassigned_submission_shows_unassigned_badge(self):
        make_submission(full_name='Unowned Case')

        response = self.client.get(reverse('dashboard:queue'))

        self.assertContains(response, 'badge--unassigned')
        self.assertContains(response, 'Unassigned')

    def test_assigned_submission_shows_assignee_name(self):
        make_submission(full_name='Owned Case', assigned_to=self.manager)

        response = self.client.get(reverse('dashboard:queue'))

        self.assertContains(response, self.manager.username)
        # The unassigned badge element must not appear — the CSS class definition in
        # <style> uses ".badge--unassigned" (with a dot), so checking the attribute
        # value without a dot correctly targets only rendered elements.
        self.assertNotContains(response, 'class="badge badge--unassigned"')

    def test_filter_by_unassigned_returns_only_unassigned(self):
        make_submission(full_name='Unowned', assigned_to=None)
        make_submission(full_name='Owned', assigned_to=self.manager)

        response = self.client.get(reverse('dashboard:queue'), {'assigned_to': 'unassigned'})

        self.assertContains(response, 'Unowned')
        self.assertNotContains(response, 'Owned')

    def test_filter_by_user_id_returns_only_that_assignee(self):
        other = make_case_manager(username='other')
        make_submission(full_name='Manager Case', assigned_to=self.manager)
        make_submission(full_name='Other Case', assigned_to=other)

        response = self.client.get(
            reverse('dashboard:queue'), {'assigned_to': str(self.manager.pk)}
        )

        self.assertContains(response, 'Manager Case')
        self.assertNotContains(response, 'Other Case')

    def test_unrecognized_assignee_falls_back_to_unfiltered(self):
        make_submission(full_name='Case One')
        make_submission(full_name='Case Two')

        response = self.client.get(reverse('dashboard:queue'), {'assigned_to': 'not-valid'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Case One')
        self.assertContains(response, 'Case Two')

    def test_non_case_manager_user_id_falls_back_to_unfiltered(self):
        # User exists but is not a Case Manager — should not be usable as a filter.
        outsider = User.objects.create_user(username='outsider')
        make_submission(full_name='Case Alpha')

        response = self.client.get(reverse('dashboard:queue'), {'assigned_to': str(outsider.pk)})

        self.assertContains(response, 'Case Alpha')

    def test_deactivated_case_manager_listed_in_assignee_filter(self):
        # A deactivated Case Manager still holds cases, so the filter must reach
        # their caseload. Listed, but labelled so nobody mistakes them for active.
        inactive = make_case_manager(username='inactive_mgr')
        inactive.is_active = False
        inactive.save()

        response = self.client.get(reverse('dashboard:queue'))

        self.assertContains(response, 'inactive_mgr (deactivated)')
        self.assertContains(response, self.manager.username)

    def test_queue_can_be_filtered_to_a_deactivated_managers_caseload(self):
        inactive = make_case_manager(username='inactive_mgr')
        inactive.is_active = False
        inactive.save()
        make_submission(full_name='Orphaned Case', assigned_to=inactive)
        make_submission(full_name='Other Case')

        response = self.client.get(reverse('dashboard:queue'), {'assigned_to': str(inactive.pk)})

        self.assertContains(response, 'Orphaned Case')
        self.assertNotContains(response, 'Other Case')

    def test_queue_rows_link_to_detail_view(self):
        sub = make_submission()

        response = self.client.get(reverse('dashboard:queue'))

        self.assertContains(response, reverse('dashboard:detail', args=[sub.pk]))


class CaseQueueDetainedTests(TestCase):
    def setUp(self):
        self.manager = make_case_manager()
        self.client.login(username='manager', password='not-a-real-password')

    def test_detained_case_sorts_above_newer_non_detained_case(self):
        make_submission(full_name='Detained Applicant', detained=True)
        make_submission(full_name='Free Applicant')

        content = self.client.get(reverse('dashboard:queue')).content.decode()

        self.assertLess(content.index('Detained Applicant'), content.index('Free Applicant'))

    def test_detained_row_renders_the_detained_badge(self):
        make_submission(full_name='Detained Applicant', detained=True)

        response = self.client.get(reverse('dashboard:queue'))

        self.assertContains(response, 'class="badge badge--detained"')

    def test_queue_without_detained_rows_renders_no_detained_badge(self):
        make_submission(full_name='Free Applicant')

        response = self.client.get(reverse('dashboard:queue'))

        # The CSS class definition in <style> uses ".badge--detained" (with a dot),
        # so checking the attribute value targets only rendered elements.
        self.assertNotContains(response, 'class="badge badge--detained"')

    def test_filter_detained_yes_returns_only_detained(self):
        make_submission(full_name='Detained Applicant', detained=True)
        make_submission(full_name='Free Applicant')

        response = self.client.get(reverse('dashboard:queue'), {'detained': 'yes'})

        self.assertContains(response, 'Detained Applicant')
        self.assertNotContains(response, 'Free Applicant')

    def test_filter_detained_no_returns_only_non_detained(self):
        make_submission(full_name='Detained Applicant', detained=True)
        make_submission(full_name='Free Applicant')

        response = self.client.get(reverse('dashboard:queue'), {'detained': 'no'})

        self.assertContains(response, 'Free Applicant')
        self.assertNotContains(response, 'Detained Applicant')

    def test_unrecognized_detained_falls_back_to_unfiltered(self):
        make_submission(full_name='Detained Applicant', detained=True)
        make_submission(full_name='Free Applicant')

        response = self.client.get(reverse('dashboard:queue'), {'detained': "evil'--"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Detained Applicant')
        self.assertContains(response, 'Free Applicant')
        # "All" is selected and the rejected value is never echoed back into the page.
        self.assertContains(response, '<option value="" selected>All cases</option>', html=True)
        self.assertNotContains(response, 'evil')

    def test_detained_composes_with_status_and_assignee(self):
        make_submission(
            full_name='Full Match', detained=True, status='accepted', assigned_to=self.manager
        )
        make_submission(full_name='Wrong Detained', status='accepted', assigned_to=self.manager)
        make_submission(
            full_name='Wrong Status', detained=True, status='new', assigned_to=self.manager
        )
        make_submission(full_name='Wrong Assignee', detained=True, status='accepted')

        response = self.client.get(
            reverse('dashboard:queue'),
            {
                'status': 'accepted',
                'assigned_to': str(self.manager.pk),
                'detained': 'yes',
            },
        )

        self.assertContains(response, 'Full Match')
        self.assertNotContains(response, 'Wrong Detained')
        self.assertNotContains(response, 'Wrong Status')
        self.assertNotContains(response, 'Wrong Assignee')

    def test_detained_composes_with_search_and_pagination(self):
        for i in range(26):
            make_submission(full_name=f'Match {i:02d}', detained=True)
        make_submission(full_name='Match Free')
        make_submission(full_name='Other Detained', detained=True)

        self.client.post(reverse('dashboard:search'), {'q': 'Match'})
        response = self.client.get(
            reverse('dashboard:queue'),
            {'detained': 'yes', 'page': 2},
        )

        # 26 detained matches -> page 2 holds the oldest one; the non-detained match
        # and the non-matching detained case are excluded by filter and search.
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Match 00')
        self.assertNotContains(response, 'Match Free')
        self.assertNotContains(response, 'Other Detained')


class CaseDetailAccessTests(TestCase):
    def setUp(self):
        self.submission = make_submission()

    def test_anonymous_redirected_to_login(self):
        url = reverse('dashboard:detail', args=[self.submission.pk])

        response = self.client.get(url)

        self.assertRedirects(response, f'{reverse("dashboard:login")}?next={url}')

    def test_user_without_permission_gets_403(self):
        User.objects.create_user(username='clerk', password='pass')
        self.client.login(username='clerk', password='pass')

        response = self.client.get(reverse('dashboard:detail', args=[self.submission.pk]))

        self.assertEqual(response.status_code, 403)

    def test_case_manager_gets_200(self):
        make_case_manager()
        self.client.login(username='manager', password='not-a-real-password')

        response = self.client.get(reverse('dashboard:detail', args=[self.submission.pk]))

        self.assertEqual(response.status_code, 200)

    def test_nonexistent_case_returns_404(self):
        make_case_manager()
        self.client.login(username='manager', password='not-a-real-password')

        response = self.client.get(reverse('dashboard:detail', args=[99999]))

        self.assertEqual(response.status_code, 404)

    def test_permissionless_post_is_rejected_and_changes_nothing(self):
        # The mixins cover this, but nothing pinned it: a POST must be gated by the
        # same permission as the GET, not merely hidden from the UI.
        User.objects.create_user(username='clerk', password='not-a-real-password')
        self.client.login(username='clerk', password='not-a-real-password')

        response = self.client.post(
            reverse('dashboard:detail', args=[self.submission.pk]),
            {'assigned_to': '', 'body': 'Should never be written.'},
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(StaffNote.objects.count(), 0)

    def test_detail_is_not_reachable_from_intake_urls(self):
        # The intake app's URL conf must not expose the detail view.
        from django.urls import Resolver404, resolve

        try:
            resolve(f'/asylum-intake/{self.submission.pk}/')
            self.fail('Intake URL space should not resolve to a case detail view')
        except Resolver404:
            pass


class CaseAssignmentTests(TestCase):
    def setUp(self):
        self.manager = make_case_manager()
        self.submission = make_submission()
        self.client.login(username='manager', password='not-a-real-password')
        self.url = reverse('dashboard:detail', args=[self.submission.pk])

    def test_detail_shows_assign_form(self):
        response = self.client.get(self.url)

        self.assertContains(response, 'name="assigned_to"')

    def test_assign_sets_assigned_to(self):
        self.client.post(self.url, {'assigned_to': self.manager.pk, 'save_assignment': '1'})

        self.submission.refresh_from_db()
        self.assertEqual(self.submission.assigned_to, self.manager)

    def test_reassign_to_different_manager(self):
        other = make_case_manager(username='other')
        self.submission.assigned_to = self.manager
        self.submission.save()

        self.client.post(self.url, {'assigned_to': other.pk, 'save_assignment': '1'})

        self.submission.refresh_from_db()
        self.assertEqual(self.submission.assigned_to, other)

    def test_unassign_clears_assigned_to(self):
        self.submission.assigned_to = self.manager
        self.submission.save()

        self.client.post(self.url, {'assigned_to': '', 'save_assignment': '1'})

        self.submission.refresh_from_db()
        self.assertIsNone(self.submission.assigned_to)

    def test_deleting_user_sets_assigned_to_null(self):
        self.submission.assigned_to = self.manager
        self.submission.save()

        self.manager.delete()

        self.submission.refresh_from_db()
        self.assertIsNone(self.submission.assigned_to)

    def test_assign_redirects_to_detail_on_success(self):
        response = self.client.post(
            self.url, {'assigned_to': self.manager.pk, 'save_assignment': '1'}
        )

        self.assertRedirects(response, self.url)

    def test_only_case_managers_appear_in_dropdown(self):
        User.objects.create_user(username='outsider')

        response = self.client.get(self.url)

        self.assertContains(response, self.manager.username)
        self.assertNotContains(response, 'outsider')

    def test_deactivated_case_manager_excluded_from_assign_dropdown(self):
        # Not assignable to a case they don't already hold. The case in this class's
        # setUp is unassigned, so the widening in AssignForm does not apply.
        inactive = make_case_manager(username='inactive_mgr')
        inactive.is_active = False
        inactive.save()

        response = self.client.get(self.url)

        self.assertNotContains(response, 'inactive_mgr')
        self.assertContains(response, self.manager.username)

    def test_deactivated_holder_stays_selectable_on_the_case_they_hold(self):
        inactive = make_case_manager(username='inactive_mgr')
        inactive.is_active = False
        inactive.save()
        self.submission.assigned_to = inactive
        self.submission.save()

        response = self.client.get(self.url)

        self.assertContains(response, 'inactive_mgr (deactivated)')
        self.assertContains(
            response,
            f'<option value="{inactive.pk}" selected>inactive_mgr (deactivated)</option>',
            html=True,
        )

    def test_resaving_a_case_held_by_a_deactivated_manager_keeps_the_assignment(self):
        # The bug: the holder was missing from the queryset, so an untouched re-save
        # posted the rendered '— Unassigned —' and silently stripped the assignment.
        inactive = make_case_manager(username='inactive_mgr')
        inactive.is_active = False
        inactive.save()
        self.submission.assigned_to = inactive
        self.submission.save()

        response = self.client.post(
            self.url, {'assigned_to': str(inactive.pk), 'save_assignment': '1'}
        )

        self.assertRedirects(response, self.url)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.assigned_to, inactive)

    def test_non_case_manager_pk_is_rejected_by_the_form(self):
        # The dropdown hides them; this proves the queryset also rejects a posted pk.
        outsider = User.objects.create_user(username='outsider')

        response = self.client.post(self.url, {'assigned_to': outsider.pk, 'save_assignment': '1'})

        self.assertEqual(response.status_code, 200)  # re-render, not a redirect
        self.submission.refresh_from_db()
        self.assertIsNone(self.submission.assigned_to)


class StaffNoteTests(TestCase):
    def setUp(self):
        self.manager = make_case_manager()
        self.submission = make_submission()
        self.client.login(username='manager', password='not-a-real-password')
        self.url = reverse('dashboard:detail', args=[self.submission.pk])

    def test_add_note_creates_note_with_request_user_as_author(self):
        self.client.post(self.url, {'body': 'First observation.', 'save_note': '1'})

        note = StaffNote.objects.get(intake=self.submission)
        self.assertEqual(note.author, self.manager)
        self.assertEqual(note.body, 'First observation.')

    def test_author_cannot_be_injected_via_form(self):
        other = User.objects.create_user(username='other')

        self.client.post(
            self.url,
            {'body': 'Injected note.', 'save_note': '1', 'author': other.pk},
        )

        note = StaffNote.objects.get(intake=self.submission)
        self.assertEqual(note.author, self.manager)

    def test_multiple_notes_display_newest_first(self):
        StaffNote.objects.create(intake=self.submission, author=self.manager, body='Older note')
        StaffNote.objects.create(intake=self.submission, author=self.manager, body='Newer note')

        content = self.client.get(self.url).content.decode()

        self.assertLess(content.index('Newer note'), content.index('Older note'))

    def test_empty_body_does_not_create_note(self):
        # Empty body means "no note this submit" — not a validation error, just skipped.
        self.client.post(self.url, {'body': '', 'save_note': '1'})

        self.assertEqual(StaffNote.objects.filter(intake=self.submission).count(), 0)

    def test_add_note_redirects_to_detail_on_success(self):
        response = self.client.post(self.url, {'body': 'A note.', 'save_note': '1'})

        self.assertRedirects(response, self.url)

    def test_notes_for_different_intakes_do_not_bleed_through(self):
        other_submission = make_submission(full_name='Other Person')
        StaffNote.objects.create(intake=other_submission, author=self.manager, body='Other note')

        response = self.client.get(self.url)

        self.assertNotContains(response, 'Other note')

    def test_deleting_user_who_authored_notes_is_blocked(self):
        StaffNote.objects.create(intake=self.submission, author=self.manager, body='Note')

        with self.assertRaises(ProtectedError):
            self.manager.delete()

    def test_no_note_update_url_exists(self):
        from django.urls import Resolver404, resolve

        try:
            resolve('/dashboard/notes/1/edit/')
            self.fail('No update route should exist for StaffNote')
        except Resolver404:
            pass

    def test_no_note_delete_url_exists(self):
        from django.urls import Resolver404, resolve

        try:
            resolve('/dashboard/notes/1/delete/')
            self.fail('No delete route should exist for StaffNote')
        except Resolver404:
            pass

    # The staging behaviour itself is client-side and Django's test client runs no JS,
    # so these pin only that the markup the script depends on is present. The real
    # guarantee is that every note test above still passes unmodified — the POST
    # contract did not change.
    def test_add_note_button_is_rendered_disabled(self):
        response = self.client.get(self.url)

        self.assertContains(response, 'id="note-add"')
        self.assertContains(response, 'id="note-pending"')

    def test_discard_control_and_dialog_are_rendered(self):
        response = self.client.get(self.url)

        self.assertContains(response, 'id="discard-open"')
        self.assertContains(response, '<dialog id="discard-confirm"')
        self.assertContains(response, 'id="discard-confirm-btn"')

    def test_pending_note_container_carries_the_author_name(self):
        # The script reads the username from this attribute rather than from an
        # inline script literal, so it must survive on a case with no notes yet.
        StaffNote.objects.filter(intake=self.submission).delete()

        response = self.client.get(self.url)

        self.assertContains(response, f'data-author="{self.manager.username}"')


class CaseDetailContentTests(TestCase):
    def setUp(self):
        self.manager = make_case_manager()
        self.client.login(username='manager', password='not-a-real-password')

    def _get(self, submission, **params):
        return self.client.get(reverse('dashboard:detail', args=[submission.pk]), params)

    def _back_href(self, query=''):
        return f'href="{reverse("dashboard:queue")}{query}"'

    def test_all_field_cards_render_every_value(self):
        submission = make_full_submission()

        response = self._get(submission)

        for heading in (
            'Identity',
            'Contact',
            'Case and court',
            'Submission details',
            'Narrative responses',
        ):
            self.assertContains(response, heading)
        for value in (
            'Maria Example',
            '1990-01-01',
            'Venezuela',
            'Spanish',  # identity
            '+1-555-0100',
            'maria@example.test',
            'Houston',  # contact
            'Houston Immigration Court',
            'A-000-000-000',
            '2026-09-01',  # case and court
            'Needs Legal Review',  # submission details
            'Original fear narrative.',
            'Original past harm narrative.',
            'Original travel narrative.',  # narratives
        ):
            self.assertContains(response, value)

    def test_empty_optional_renders_a_directionless_placeholder(self):
        submission = make_submission(phone='', a_number='')

        response = self._get(submission)

        # The em-dash must not sit inside an applicant-text/dir element.
        self.assertContains(response, '<p class="empty">&mdash;</p>', html=True)

    def test_arabic_narrative_renders_intact_with_direction(self):
        arabic = 'أخشى العودة إلى بلدي بسبب الاضطهاد'
        submission = make_submission(fear_of_return_summary=arabic)

        response = self._get(submission)

        self.assertContains(
            response,
            f'<p class="applicant-text narrative-text" dir="auto">{arabic}</p>',
            html=True,
        )
        self.assertContains(response, '<html lang="en" dir="ltr">')

    def test_populated_translation_is_labeled_with_its_language(self):
        # translated_response_language is the language the translation is written in.
        submission = make_submission(
            fear_of_return_summary='النص الأصلي',
            fear_of_return_summary_translated='Staff-entered English translation.',
            translated_response_language='en',
        )

        response = self._get(submission)

        self.assertContains(response, 'Staff translation (English)')
        self.assertContains(response, 'Staff-entered English translation.')
        content = response.content.decode()
        self.assertLess(
            content.index('النص الأصلي'),
            content.index('Staff-entered English translation.'),
        )

    def test_translation_without_a_language_has_no_empty_parentheses(self):
        submission = make_submission(
            fear_of_return_summary_translated='Translation with no language recorded.',
            translated_response_language='',
        )

        response = self._get(submission)

        self.assertContains(response, 'Staff translation')
        self.assertNotContains(response, 'Staff translation (')

    def test_absent_translation_renders_no_label_at_all(self):
        submission = make_submission(fear_of_return_summary='Only the original exists.')

        response = self._get(submission)

        self.assertContains(response, 'Only the original exists.')
        self.assertNotContains(response, 'Staff translation')

    def test_title_omits_the_applicant_name(self):
        submission = make_submission(full_name='Distinctive Applicant Name')

        response = self._get(submission)

        self.assertContains(
            response,
            '<title>Case detail | Case Manager Dashboard</title>',
            html=True,
        )
        self.assertContains(response, 'Distinctive Applicant Name')  # still in the body

    def test_back_link_preserves_status_alone(self):
        submission = make_submission(status='accepted')

        response = self._get(submission, status='accepted')

        self.assertContains(response, self._back_href('?status=accepted'))

    def test_back_link_preserves_assignee_alone(self):
        submission = make_submission(assigned_to=self.manager)

        response = self._get(submission, assigned_to=str(self.manager.pk))

        self.assertContains(response, self._back_href(f'?assigned_to={self.manager.pk}'))

    def test_back_link_preserves_both_filters(self):
        submission = make_submission(status='accepted', assigned_to=self.manager)

        response = self._get(submission, status='accepted', assigned_to=str(self.manager.pk))

        self.assertContains(
            response,
            self._back_href(f'?status=accepted&amp;assigned_to={self.manager.pk}'),
        )

    def test_back_link_preserves_the_unassigned_sentinel(self):
        submission = make_submission()

        response = self._get(submission, assigned_to='unassigned')

        self.assertContains(response, self._back_href('?assigned_to=unassigned'))

    def test_back_link_preserves_the_detained_filter(self):
        submission = make_submission(detained=True)

        response = self._get(submission, detained='yes')

        self.assertContains(response, self._back_href('?detained=yes'))

    def test_detail_status_form_carries_the_detained_filter(self):
        submission = make_submission()

        response = self._get(submission, detained='yes')

        self.assertContains(
            response,
            '<input type="hidden" name="detained" value="yes" />',
            html=True,
        )

    def test_back_link_drops_unrecognized_filters(self):
        submission = make_submission()

        response = self._get(submission, status="evil'--", assigned_to='99999')

        self.assertContains(response, self._back_href())
        self.assertNotContains(response, 'evil')

    def test_attribution_placeholders_before_any_status_change(self):
        submission = make_submission()

        response = self._get(submission)

        self.assertContains(response, 'Status last changed')
        self.assertContains(response, '<p class="empty">Never changed</p>', html=True)
        self.assertContains(response, '<p class="empty">Not recorded</p>', html=True)

    def test_attribution_renders_after_a_status_change(self):
        submission = make_submission()
        self.client.post(
            reverse('dashboard:status', args=[submission.pk]),
            {'new_status': 'accepted'},
        )

        response = self._get(submission)

        self.assertNotContains(response, 'Never changed')
        self.assertContains(response, self.manager.username)


class QueryCountTests(TestCase):
    """Row and note counts must not change the number of queries issued."""

    def setUp(self):
        self.manager = make_case_manager()
        self.client.login(username='manager', password='not-a-real-password')

    def _queue_queries(self, rows):
        IntakeSubmission.objects.all().delete()
        for i in range(rows):
            make_submission(full_name=f'Case {i}', assigned_to=self.manager)
        with CaptureQueriesContext(connection) as captured:
            self.client.get(reverse('dashboard:queue'))
        return len(captured)

    def _detail_queries(self, notes):
        submission = make_submission()
        for i in range(notes):
            StaffNote.objects.create(intake=submission, author=self.manager, body=f'Note {i}')
        with CaptureQueriesContext(connection) as captured:
            self.client.get(reverse('dashboard:detail', args=[submission.pk]))
        return len(captured)

    def test_queue_issues_no_query_per_row(self):
        self.assertEqual(self._queue_queries(2), self._queue_queries(10))

    def test_detail_issues_no_query_per_note(self):
        self.assertEqual(self._detail_queries(2), self._detail_queries(10))


class CaseSearchTests(TestCase):
    def setUp(self):
        self.manager = make_case_manager()
        self.client.login(username='manager', password='not-a-real-password')

    def _search(self, q, **extra):
        return self.client.post(reverse('dashboard:search'), {'q': q, **extra})

    def test_search_matches_on_name(self):
        make_submission(full_name='Maria Example')
        make_submission(full_name='Someone Else')

        self._search('Maria')
        response = self.client.get(reverse('dashboard:queue'))

        self.assertContains(response, 'Maria Example')
        self.assertNotContains(response, 'Someone Else')

    def test_search_matches_on_country(self):
        make_submission(full_name='Case A', country_of_origin='Venezuela')
        make_submission(full_name='Case B', country_of_origin='Elsewhere')

        self._search('venezu')
        response = self.client.get(reverse('dashboard:queue'))

        self.assertContains(response, 'Case A')
        self.assertNotContains(response, 'Case B')

    def test_search_matches_on_a_number(self):
        make_submission(full_name='Case A', a_number='A-123-456-789')
        make_submission(full_name='Case B', a_number='A-999-000-111')

        self._search('123-456')
        response = self.client.get(reverse('dashboard:queue'))

        self.assertContains(response, 'Case A')
        self.assertNotContains(response, 'Case B')

    def test_arabic_query_matches_and_renders_intact(self):
        arabic_name = 'محمد الأحمد'
        make_submission(full_name=arabic_name)
        make_submission(full_name='Latin Name')

        self._search('محمد')
        response = self.client.get(reverse('dashboard:queue'))

        self.assertContains(response, arabic_name)
        self.assertNotContains(response, 'Latin Name')

    def test_query_never_appears_in_any_url(self):
        make_submission(full_name='Maria Example')

        response = self._search('Maria', status='accepted')

        self.assertNotIn('Maria', response['Location'])
        self.assertNotIn('q=', response['Location'])

    def test_search_redirect_keeps_both_filters_and_resets_page(self):
        response = self._search('Maria', status='accepted', assigned_to='unassigned')

        self.assertEqual(
            response['Location'],
            f'{reverse("dashboard:queue")}?status=accepted&assigned_to=unassigned',
        )

    def test_search_redirect_keeps_the_detained_filter(self):
        # Param order is fixed by _queue_params: status, assigned_to, detained, page.
        response = self._search('Maria', status='accepted', detained='yes')

        self.assertEqual(
            response['Location'],
            f'{reverse("dashboard:queue")}?status=accepted&detained=yes',
        )

    def test_search_composes_with_filter_and_pagination(self):
        for i in range(26):
            make_submission(full_name=f'Match {i:02d}', status='accepted')
        make_submission(full_name='Match New', status='new')
        make_submission(full_name='Other Accepted', status='accepted')

        self._search('Match')
        response = self.client.get(
            reverse('dashboard:queue'),
            {'status': 'accepted', 'page': 2},
        )

        # 26 accepted matches -> page 2 holds the oldest one; the 'new' match and the
        # non-matching accepted case are excluded by filter and search respectively.
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Match 00')
        self.assertNotContains(response, 'Match New')
        self.assertNotContains(response, 'Other Accepted')

    def test_clear_button_empties_the_search(self):
        make_submission(full_name='Maria Example')
        make_submission(full_name='Someone Else')
        self._search('Maria')

        self._search('Maria', clear='1')
        response = self.client.get(reverse('dashboard:queue'))

        self.assertNotIn('dashboard_search', self.client.session)
        self.assertContains(response, 'Someone Else')

    def test_whitespace_query_clears_rather_than_storing(self):
        self._search('Maria')

        self._search('   ')

        self.assertNotIn('dashboard_search', self.client.session)

    def test_query_is_stripped_and_capped_at_100(self):
        self._search('  ' + 'x' * 150 + '  ')

        self.assertEqual(len(self.client.session['dashboard_search']), 100)

    def test_anonymous_is_redirected_to_login(self):
        self.client.logout()

        response = self.client.post(reverse('dashboard:search'), {'q': 'Maria'})

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('dashboard:login'), response['Location'])

    def test_user_without_permission_gets_403(self):
        User.objects.create_user(username='clerk', password='not-a-real-password')
        self.client.login(username='clerk', password='not-a-real-password')

        response = self.client.post(reverse('dashboard:search'), {'q': 'Maria'})

        self.assertEqual(response.status_code, 403)

    def test_get_is_rejected_while_authenticated(self):
        # Authenticated on purpose: the login check runs before the method check.
        self.assertEqual(self.client.get(reverse('dashboard:search')).status_code, 405)


def make_read_only_reviewer(username='reviewer', password='not-a-real-password'):
    """access_dashboard directly, no group: can read and leave notes, cannot write."""
    from django.contrib.auth.models import Permission

    user = User.objects.create_user(username=username, password=password)
    user.user_permissions.add(Permission.objects.get(codename='access_dashboard'))
    return user


class CaseStatusUpdateTests(TestCase):
    def setUp(self):
        self.manager = make_case_manager()
        self.submission = make_submission()
        self.client.login(username='manager', password='not-a-real-password')
        self.url = reverse('dashboard:status', args=[self.submission.pk])

    def test_status_change_updates_record_and_attribution(self):
        self.client.post(self.url, {'new_status': 'accepted'})

        self.submission.refresh_from_db()
        self.assertEqual(self.submission.status, 'accepted')
        self.assertIsNotNone(self.submission.status_changed_at)
        self.assertEqual(self.submission.status_changed_by, self.manager)

    def test_redirect_preserves_filters_and_page(self):
        for _ in range(30):
            make_submission(status='new')

        response = self.client.post(
            self.url,
            {
                'new_status': 'conflict_check',
                'status': 'new',
                'assigned_to': 'unassigned',
                'page': '2',
            },
        )

        self.assertEqual(
            response['Location'],
            f'{reverse("dashboard:queue")}?status=new&assigned_to=unassigned&page=2',
        )

    def test_redirect_preserves_the_detained_filter(self):
        response = self.client.post(
            self.url,
            {
                'new_status': 'accepted',
                'detained': 'yes',
            },
        )

        self.assertEqual(
            response['Location'],
            f'{reverse("dashboard:queue")}?detained=yes',
        )

    def test_page_clamps_when_the_change_empties_it(self):
        # 26 'new' cases -> 2 pages. Moving the page-2 case out of 'new' leaves 25 ->
        # one page; returning to page 2 would 404.
        for i in range(25):
            make_submission(full_name=f'Filler {i}', status='new')
        # self.submission is the oldest 'new' case, i.e. the lone page-2 row.

        response = self.client.post(
            self.url,
            {
                'new_status': 'accepted',
                'status': 'new',
                'page': '2',
            },
        )

        self.assertEqual(response['Location'], f'{reverse("dashboard:queue")}?status=new')
        self.assertEqual(self.client.get(response['Location']).status_code, 200)

    def test_noop_submit_leaves_attribution_untouched(self):
        self.client.post(self.url, {'new_status': 'accepted'})
        self.submission.refresh_from_db()
        first_at, first_by = self.submission.status_changed_at, self.submission.status_changed_by

        make_case_manager(username='other')
        self.client.login(username='other', password='not-a-real-password')
        self.client.post(self.url, {'new_status': 'accepted'})

        self.submission.refresh_from_db()
        self.assertEqual(self.submission.status_changed_at, first_at)
        self.assertEqual(self.submission.status_changed_by, first_by)

    def test_invalid_status_returns_400_and_changes_nothing(self):
        response = self.client.post(self.url, {'new_status': "evil'--"})

        self.assertEqual(response.status_code, 400)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.status, 'new')
        self.assertIsNone(self.submission.status_changed_at)

    def test_get_is_rejected_while_authenticated(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_anonymous_is_redirected_to_login(self):
        self.client.logout()

        response = self.client.post(self.url, {'new_status': 'accepted'})

        self.assertIn(reverse('dashboard:login'), response['Location'])

    def test_access_only_user_gets_403(self):
        make_read_only_reviewer()
        self.client.login(username='reviewer', password='not-a-real-password')

        response = self.client.post(self.url, {'new_status': 'accepted'})

        self.assertEqual(response.status_code, 403)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.status, 'new')


class ReadOnlyReviewerTests(TestCase):
    """access_dashboard alone: full read and notes, no write controls anywhere."""

    def setUp(self):
        self.reviewer = make_read_only_reviewer()
        self.submission = make_submission()
        self.client.login(username='reviewer', password='not-a-real-password')
        self.detail_url = reverse('dashboard:detail', args=[self.submission.pk])

    def test_queue_shows_no_status_column(self):
        response = self.client.get(reverse('dashboard:queue'))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Change status')
        self.assertNotContains(response, 'name="new_status"')

    def test_detail_shows_notes_but_no_write_controls(self):
        response = self.client.get(self.detail_url)

        self.assertContains(response, 'id="notes-form"')
        self.assertNotContains(response, 'Update case')
        # The control itself, not the attribute text — the JS contains a
        # querySelector('[name="assigned_to"]') literal even when the form is gated.
        self.assertNotContains(response, '<select name="assigned_to"')
        self.assertNotContains(response, 'id="assign-form"')
        self.assertNotContains(response, 'name="new_status"')

    def test_reviewer_can_still_add_a_note(self):
        self.client.post(self.detail_url, {'body': 'Reviewer note.', 'save_note': '1'})

        note = StaffNote.objects.get(intake=self.submission)
        self.assertEqual(note.author, self.reviewer)

    def test_reviewer_assignment_post_gets_403_and_changes_nothing(self):
        response = self.client.post(
            self.detail_url,
            {'assigned_to': str(self.reviewer.pk), 'save_assignment': '1'},
        )

        self.assertEqual(response.status_code, 403)
        self.submission.refresh_from_db()
        self.assertIsNone(self.submission.assigned_to)


class DetailFormSplitTests(TestCase):
    def setUp(self):
        self.manager = make_case_manager()
        self.submission = make_submission()
        self.client.login(username='manager', password='not-a-real-password')
        self.url = reverse('dashboard:detail', args=[self.submission.pk])

    def test_note_submit_ignores_a_forged_assignment(self):
        # The whole point of the split: a stale or forged assigned_to in a note POST
        # must never touch the assignment.
        self.submission.assigned_to = self.manager
        self.submission.save()
        other = make_case_manager(username='other')

        self.client.post(
            self.url,
            {
                'body': 'A note.',
                'save_note': '1',
                'assigned_to': str(other.pk),
            },
        )

        self.submission.refresh_from_db()
        self.assertEqual(self.submission.assigned_to, self.manager)
        self.assertEqual(StaffNote.objects.count(), 1)

    def test_post_without_a_named_button_returns_400(self):
        response = self.client.post(self.url, {'assigned_to': '', 'body': 'x'})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(StaffNote.objects.count(), 0)

    def test_detail_status_form_renders_for_manager(self):
        response = self.client.get(self.url)

        self.assertContains(response, 'name="new_status"')
        self.assertContains(response, 'Change status')
