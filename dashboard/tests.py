from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

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

        # The value itself must survive, inside an element carrying its own direction.
        self.assertContains(
            response,
            f'<td class="applicant-text" dir="auto">{arabic_name}</td>',
            html=True,
        )
        self.assertContains(response, '<html lang="en" dir="ltr">')
