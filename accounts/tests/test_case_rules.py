"""Case-insensitive matching uses the uniqueness rule (spec 09, AC-11).

'I' and 'ı' (dotless i) are distinct under LOWER(), which the unique
constraints use, but equal under UPPER(), which __iexact uses on
PostgreSQL. Before the S-1 fix, PostgreSQL saw two matches here: login
raised a server error and the other checks gave wrong answers. These tests
run on SQLite and PostgreSQL alike.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.forms import RegistrationForm
from workspaces.models import Workspace

PASSWORD = 'Str0ng-Passw0rd!x'

User = get_user_model()


def registration_data(**overrides):
    data = {
        'username': 'newuser',
        'email': 'newuser@example.com',
        'password1': PASSWORD,
        'password2': PASSWORD,
    }
    data.update(overrides)
    return data


class CaseRuleTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.dotted = User.objects.create_user(
            username='I', email='dotted@example.com', password=PASSWORD
        )
        cls.dotless = User.objects.create_user(
            username='ı', email='dotless@example.com', password=PASSWORD
        )

    def login(self, username):
        return self.client.post(
            reverse('accounts:login'),
            {'username': username, 'password': PASSWORD},
        )

    def test_login_with_each_username_signs_in_that_user(self):
        """AC-11: each of 'I' and 'ı' logs in its own account, no error."""
        for username, user in (('I', self.dotted), ('ı', self.dotless)):
            with self.subTest(username=username):
                response = self.login(username)
                self.assertRedirects(
                    response, reverse('core:dashboard'),
                    fetch_redirect_response=False,
                )
                self.assertEqual(
                    int(self.client.session['_auth_user_id']), user.pk
                )
                self.client.logout()

    def test_login_ignores_letter_case_by_the_uniqueness_rule(self):
        """AC-11: lowercase 'i' still logs in 'I' (LOWER('I') = 'i')."""
        response = self.login('i')
        self.assertRedirects(
            response, reverse('core:dashboard'), fetch_redirect_response=False
        )
        self.assertEqual(
            int(self.client.session['_auth_user_id']), self.dotted.pk
        )

    def test_natural_key_lookup_finds_exactly_one_user(self):
        """AC-11: the login lookup returns exactly the matching user."""
        self.assertEqual(User.objects.get_by_natural_key('ı'), self.dotless)
        self.assertEqual(User.objects.get_by_natural_key('I'), self.dotted)


class RegistrationCaseRuleTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User.objects.create_user(
            username='I', email='a@i.com', password=PASSWORD
        )

    def test_username_distinct_under_uniqueness_rule_is_allowed(self):
        """AC-11: 'ı' may register while 'I' exists (distinct under LOWER)."""
        form = RegistrationForm(data=registration_data(username='ı'))
        self.assertTrue(form.is_valid(), form.errors)

    def test_username_case_variant_is_still_refused(self):
        """AC-11: 'i' is refused while 'I' exists (equal under LOWER)."""
        form = RegistrationForm(data=registration_data(username='i'))
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)

    def test_email_distinct_under_uniqueness_rule_is_allowed(self):
        """AC-11: 'a@ı.com' may register while 'a@i.com' exists."""
        form = RegistrationForm(data=registration_data(email='a@ı.com'))
        self.assertTrue(form.is_valid(), form.errors)

    def test_email_case_variant_is_still_refused(self):
        """AC-11: 'A@I.COM' is refused while 'a@i.com' exists."""
        form = RegistrationForm(data=registration_data(email='A@I.COM'))
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)


class AddMemberCaseRuleTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(
            username='Owner', email='owner@example.com', password=PASSWORD
        )
        cls.dotted = User.objects.create_user(
            username='I', email='dotted@example.com', password=PASSWORD
        )
        cls.dotless = User.objects.create_user(
            username='ı', email='dotless@example.com', password=PASSWORD
        )
        cls.ws = Workspace.objects.create_with_owner('Apollo', cls.owner)

    def test_add_member_finds_the_matching_user(self):
        """AC-11: adding 'ı' adds that user only, not 'I'."""
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse('workspaces:add_member', args=[self.ws.pk]),
            {'username': 'ı'},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.ws.memberships.filter(user=self.dotless).exists())
        self.assertFalse(self.ws.memberships.filter(user=self.dotted).exists())
