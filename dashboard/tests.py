from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from intake.models import IntakeSubmission
from dashboard.models import StaffNote


def make_submission(**overrides):
    values = {
        'full_name': 'Maria Example',
        'country_of_origin': 'Venezuela',
        'preferred_language': 'Spanish',
        'fear_of_return_summary': 'Original response in the applicant language.',
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
            f"{reverse('dashboard:login')}?next={reverse('dashboard:queue')}",
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
        self.assertContains(response, '<option value="accepted" selected>Accepted</option>', html=True)

    def test_unrecognized_status_falls_back_to_unfiltered(self):
        make_submission(full_name='Accepted Applicant', status='accepted')
        make_submission(full_name='New Applicant', status='new')

        response = self.client.get(reverse('dashboard:queue'), {'status': "evil'--"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Accepted Applicant')
        self.assertContains(response, 'New Applicant')
        # "All" is selected and the rejected value is never echoed back into the page.
        self.assertContains(response, '<option value="" selected>All</option>', html=True)
        self.assertNotContains(response, 'evil')

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

        response = self.client.get(reverse('dashboard:queue'), {'assigned_to': str(self.manager.pk)})

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

    def test_queue_rows_link_to_detail_view(self):
        sub = make_submission()

        response = self.client.get(reverse('dashboard:queue'))

        self.assertContains(response, reverse('dashboard:detail', args=[sub.pk]))


class CaseDetailAccessTests(TestCase):
    def setUp(self):
        self.submission = make_submission()

    def test_anonymous_redirected_to_login(self):
        url = reverse('dashboard:detail', args=[self.submission.pk])

        response = self.client.get(url)

        self.assertRedirects(response, f"{reverse('dashboard:login')}?next={url}")

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

    def test_detail_is_not_reachable_from_intake_urls(self):
        # The intake app's URL conf must not expose the detail view.
        from django.urls import resolve, Resolver404
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
        self.client.post(self.url, {'assigned_to': self.manager.pk, 'body': ''})

        self.submission.refresh_from_db()
        self.assertEqual(self.submission.assigned_to, self.manager)

    def test_reassign_to_different_manager(self):
        other = make_case_manager(username='other')
        self.submission.assigned_to = self.manager
        self.submission.save()

        self.client.post(self.url, {'assigned_to': other.pk, 'body': ''})

        self.submission.refresh_from_db()
        self.assertEqual(self.submission.assigned_to, other)

    def test_unassign_clears_assigned_to(self):
        self.submission.assigned_to = self.manager
        self.submission.save()

        self.client.post(self.url, {'assigned_to': '', 'body': ''})

        self.submission.refresh_from_db()
        self.assertIsNone(self.submission.assigned_to)

    def test_deleting_user_sets_assigned_to_null(self):
        self.submission.assigned_to = self.manager
        self.submission.save()

        self.manager.delete()

        self.submission.refresh_from_db()
        self.assertIsNone(self.submission.assigned_to)

    def test_assign_redirects_to_detail_on_success(self):
        response = self.client.post(self.url, {'assigned_to': self.manager.pk, 'body': ''})

        self.assertRedirects(response, self.url)

    def test_only_case_managers_appear_in_dropdown(self):
        User.objects.create_user(username='outsider')

        response = self.client.get(self.url)

        self.assertContains(response, self.manager.username)
        self.assertNotContains(response, 'outsider')


class StaffNoteTests(TestCase):
    def setUp(self):
        self.manager = make_case_manager()
        self.submission = make_submission()
        self.client.login(username='manager', password='not-a-real-password')
        self.url = reverse('dashboard:detail', args=[self.submission.pk])

    def test_add_note_creates_note_with_request_user_as_author(self):
        self.client.post(self.url, {'assigned_to': '', 'body': 'First observation.'})

        note = StaffNote.objects.get(intake=self.submission)
        self.assertEqual(note.author, self.manager)
        self.assertEqual(note.body, 'First observation.')

    def test_author_cannot_be_injected_via_form(self):
        other = User.objects.create_user(username='other')

        self.client.post(
            self.url,
            {'assigned_to': '', 'body': 'Injected note.', 'author': other.pk},
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
        self.client.post(self.url, {'assigned_to': '', 'body': ''})

        self.assertEqual(StaffNote.objects.filter(intake=self.submission).count(), 0)

    def test_add_note_redirects_to_detail_on_success(self):
        response = self.client.post(self.url, {'assigned_to': '', 'body': 'A note.'})

        self.assertRedirects(response, self.url)

    def test_notes_for_different_intakes_do_not_bleed_through(self):
        other_submission = make_submission(full_name='Other Person')
        StaffNote.objects.create(intake=other_submission, author=self.manager, body='Other note')

        response = self.client.get(self.url)

        self.assertNotContains(response, 'Other note')

    def test_deleting_user_who_authored_notes_is_blocked(self):
        StaffNote.objects.create(intake=self.submission, author=self.manager, body='Note')

        from django.db import IntegrityError
        with self.assertRaises(Exception):
            self.manager.delete()

    def test_no_note_update_url_exists(self):
        from django.urls import resolve, Resolver404
        try:
            resolve('/dashboard/notes/1/edit/')
            self.fail('No update route should exist for StaffNote')
        except Resolver404:
            pass

    def test_no_note_delete_url_exists(self):
        from django.urls import resolve, Resolver404
        try:
            resolve('/dashboard/notes/1/delete/')
            self.fail('No delete route should exist for StaffNote')
        except Resolver404:
            pass
