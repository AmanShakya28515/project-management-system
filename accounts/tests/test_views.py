"""Register / login / logout view tests (spec 01).

Case-insensitivity tests use ASCII names only (plan 01, D-3).
"""
import re

from django.contrib import messages
from django.contrib.auth import get_user, get_user_model
from django.test import Client, TestCase
from django.urls import reverse

PASSWORD = 'Str0ng-Passw0rd!x'

User = get_user_model()


def find_input(html, name):
    """Return the <input ...> tag with the given name, or None."""
    match = re.search(r'<input[^>]*\bname="%s"[^>]*>' % re.escape(name), html)
    return match.group(0) if match else None


def message_texts(response):
    return [str(m) for m in messages.get_messages(response.wsgi_request)]


class RegisterPageTests(TestCase):
    def test_anonymous_sees_registration_form(self):
        """AC-1: anonymous GET shows username, email, password, confirmation."""
        response = self.client.get(reverse('accounts:register'))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        for name in ('username', 'email', 'password1', 'password2'):
            with self.subTest(field=name):
                self.assertIsNotNone(find_input(html, name))
        self.assertEqual(
            set(response.context['form'].fields),
            {'username', 'email', 'password1', 'password2'},
        )


class RegisterSubmitTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.existing = User.objects.create_user(
            username='Alice', email='a@x.com', password=PASSWORD
        )

    def valid_data(self, **overrides):
        data = {
            'username': 'Bob',
            'email': 'bob@example.com',
            'password1': PASSWORD,
            'password2': PASSWORD,
        }
        data.update(overrides)
        return data

    def test_valid_registration_creates_user_logs_in_and_redirects(self):
        """AC-2: valid POST creates one user, logs in, lands on dashboard."""
        response = self.client.post(reverse('accounts:register'), self.valid_data())
        self.assertRedirects(response, reverse('core:dashboard'))
        self.assertEqual(User.objects.count(), 2)
        user = User.objects.get(username='Bob')
        self.assertEqual(get_user(self.client).pk, user.pk)
        self.assertTrue(get_user(self.client).is_authenticated)

    def test_valid_registration_shows_confirmation_message(self):
        """AC-2: a confirmation message is shown on the dashboard."""
        response = self.client.post(
            reverse('accounts:register'), self.valid_data(), follow=True
        )
        self.assertEqual(response.redirect_chain[-1][0], reverse('core:dashboard'))
        msgs = list(response.context['messages'])
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0].level, messages.SUCCESS)
        self.assertIn('created', str(msgs[0]))
        self.assertContains(response, str(msgs[0]))

    def test_unicode_username_registers(self):
        """AC-2: registering the Unicode username 'José' succeeds (D-3)."""
        response = self.client.post(
            reverse('accounts:register'),
            self.valid_data(username='José', email='jose@example.com'),
        )
        self.assertRedirects(response, reverse('core:dashboard'))
        user = User.objects.get(username='José')
        self.assertEqual(get_user(self.client).pk, user.pk)

    def test_duplicate_username_any_case_rejected(self):
        """AC-3: 'alice' rejected with username error when 'Alice' exists."""
        response = self.client.post(
            reverse('accounts:register'),
            self.valid_data(username='alice', email='new@example.com'),
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('username', response.context['form'].errors)
        self.assertEqual(User.objects.count(), 1)
        self.assertFalse(get_user(self.client).is_authenticated)

    def test_duplicate_email_any_case_rejected(self):
        """AC-4: 'A@X.com' rejected with email error when 'a@x.com' exists."""
        response = self.client.post(
            reverse('accounts:register'),
            self.valid_data(username='carol', email='A@X.com'),
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('email', response.context['form'].errors)
        self.assertEqual(User.objects.count(), 1)

    def test_field_errors_rendered_next_to_fields(self):
        """AC-5: missing/invalid/mismatched input shown per field, no user."""
        response = self.client.post(
            reverse('accounts:register'),
            {'username': '', 'email': 'not-an-email',
             'password1': PASSWORD, 'password2': PASSWORD + 'x'},
        )
        self.assertEqual(response.status_code, 200)
        errors = response.context['form'].errors
        for field in ('username', 'email', 'password2'):
            with self.subTest(field=field):
                self.assertIn(field, errors)
                for msg in errors[field]:
                    self.assertContains(response, msg, html=False)
        self.assertEqual(User.objects.count(), 1)

    def test_weak_password_reason_shown(self):
        """AC-6: a weak password is rejected and the reason is displayed."""
        response = self.client.post(
            reverse('accounts:register'),
            self.valid_data(password1='84739201657', password2='84739201657'),
        )
        self.assertEqual(response.status_code, 200)
        errors = response.context['form'].errors
        self.assertIn('password2', errors)
        self.assertContains(response, 'entirely numeric')
        self.assertEqual(User.objects.count(), 1)

    def test_failed_submission_keeps_username_email_clears_passwords(self):
        """AC-7: after a failure, username/email kept and passwords blank."""
        response = self.client.post(
            reverse('accounts:register'),
            self.valid_data(
                username='Dave', email='dave@example.com',
                password2=PASSWORD + 'mismatch',
            ),
        )
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn('value="Dave"', find_input(html, 'username'))
        self.assertIn('value="dave@example.com"', find_input(html, 'email'))
        for name in ('password1', 'password2'):
            with self.subTest(field=name):
                tag = find_input(html, name)
                self.assertIsNotNone(tag)
                self.assertNotIn('value=', tag)
        self.assertNotIn(PASSWORD, html)

    def test_logged_in_user_redirected_from_register(self):
        """AC-18: a logged-in user opening register goes to the dashboard."""
        self.client.force_login(self.existing)
        response = self.client.get(reverse('accounts:register'))
        self.assertRedirects(response, reverse('core:dashboard'))


class LoginTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user(
            username='Alice', email='alice@example.com', password=PASSWORD
        )
        cls.inactive = User.objects.create_user(
            username='Ivan', email='ivan@example.com', password=PASSWORD,
            is_active=False,
        )

    def login(self, username, password=PASSWORD, **extra):
        data = {'username': username, 'password': password}
        data.update(extra)
        return self.client.post(reverse('accounts:login'), data)

    def test_login_page_shows_form_and_register_link(self):
        """AC-8: anonymous GET login shows username/password and register link."""
        response = self.client.get(reverse('accounts:login'))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIsNotNone(find_input(html, 'username'))
        self.assertIsNotNone(find_input(html, 'password'))
        self.assertEqual(
            set(response.context['form'].fields), {'username', 'password'}
        )
        # A register link inside the page body (not only the nav).
        main = html.split('</nav>', 1)[1]
        self.assertIn('href="%s"' % reverse('accounts:register'), main)

    def test_login_username_case_insensitive(self):
        """AC-9: 'Alice' logs in as alice/ALICE/Alice and lands on dashboard."""
        for variant in ('alice', 'ALICE', 'Alice'):
            with self.subTest(variant=variant):
                self.client.logout()
                response = self.login(variant)
                self.assertRedirects(response, reverse('core:dashboard'))
                self.assertEqual(get_user(self.client).pk, self.alice.pk)

    def test_login_does_not_change_stored_casing(self):
        """AC-9: logging in as 'alice' keeps the stored username 'Alice'."""
        self.login('alice')
        self.alice.refresh_from_db()
        self.assertEqual(self.alice.username, 'Alice')

    def test_password_is_case_sensitive(self):
        """AC-9: the password must match case exactly."""
        response = self.login('Alice', PASSWORD.upper())
        self.assertEqual(response.status_code, 200)
        self.assertFalse(get_user(self.client).is_authenticated)
        response = self.login('Alice', PASSWORD.lower())
        self.assertFalse(get_user(self.client).is_authenticated)

    def test_wrong_password_and_unknown_user_give_same_generic_error(self):
        """AC-10: same non-field error for wrong password and unknown user."""
        wrong_pw = self.login('Alice', 'Wr0ng-Passw0rd!x')
        unknown = self.login('NoSuchUser', PASSWORD)
        for response in (wrong_pw, unknown):
            self.assertEqual(response.status_code, 200)
            self.assertFalse(get_user(self.client).is_authenticated)
            form = response.context['form']
            self.assertEqual(list(form.errors), ['__all__'])
            self.assertEqual(len(form.non_field_errors()), 1)
        self.assertEqual(
            list(wrong_pw.context['form'].non_field_errors()),
            list(unknown.context['form'].non_field_errors()),
        )
        for msg in wrong_pw.context['form'].non_field_errors():
            self.assertContains(wrong_pw, msg)
            self.assertContains(unknown, msg)

    def test_failed_login_keeps_typed_username(self):
        """AC-10: the typed username is kept after a failed login."""
        response = self.login('NoSuchUser', 'whatever')
        tag = find_input(response.content.decode(), 'username')
        self.assertIn('value="NoSuchUser"', tag)
        tag = find_input(response.content.decode(), 'password')
        self.assertNotIn('value=', tag)

    def test_inactive_user_cannot_log_in(self):
        """AC-11: a deactivated account with correct credentials stays out."""
        response = self.login('Ivan')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(get_user(self.client).is_authenticated)
        self.assertTrue(response.context['form'].errors)

    def test_login_page_carries_next_in_hidden_input(self):
        """AC-16: the login page preserves ?next= in a hidden input."""
        target = reverse('core:dashboard') + '?from=link'
        response = self.client.get(reverse('accounts:login'), {'next': target})
        tag = find_input(response.content.decode(), 'next')
        self.assertIsNotNone(tag)
        self.assertIn('type="hidden"', tag)
        self.assertIn('value="/dashboard/?from=link"', tag.replace('&amp;', '&'))

    def test_login_redirects_to_next(self):
        """AC-16: a successful login returns to the originally requested page."""
        target = reverse('core:dashboard') + '?from=link'
        response = self.login('Alice', next=target)
        self.assertRedirects(response, target, fetch_redirect_response=False)
        self.assertTrue(get_user(self.client).is_authenticated)

    def test_full_flow_protected_page_then_login_returns_there(self):
        """AC-15, AC-16: redirected to login from a protected page, then back."""
        target = reverse('core:dashboard') + '?from=flow'
        response = self.client.get(target)
        self.assertEqual(response.status_code, 302)
        login_url = response['Location']
        self.assertTrue(login_url.startswith(reverse('accounts:login')))
        page = self.client.get(login_url)
        next_value = page.context['next']
        self.assertEqual(next_value, target)
        response = self.login('alice', next=next_value)
        self.assertRedirects(response, target, fetch_redirect_response=False)

    def test_external_next_is_ignored(self):
        """AC-17: an off-site next sends the user to the dashboard instead."""
        for evil in ('https://evil.example.com/', '//evil.example.com/',
                     'http://evil.example.com/dashboard/'):
            with self.subTest(next=evil):
                self.client.logout()
                response = self.login('Alice', next=evil)
                self.assertRedirects(response, reverse('core:dashboard'))
                self.assertNotIn('evil.example.com', response['Location'])

    def test_logged_in_user_redirected_from_login(self):
        """AC-18: a logged-in user opening login goes to the dashboard."""
        self.client.force_login(self.alice)
        response = self.client.get(reverse('accounts:login'))
        self.assertRedirects(response, reverse('core:dashboard'))

    def test_raw_password_never_in_login_responses(self):
        """AC-22: the raw password is never echoed back in a response."""
        failed = self.login('Alice', PASSWORD + 'x')
        self.assertNotContains(failed, PASSWORD)
        ok = self.client.post(
            reverse('accounts:login'),
            {'username': 'Alice', 'password': PASSWORD}, follow=True,
        )
        self.assertNotContains(ok, PASSWORD)


class LogoutTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user(
            username='Alice', email='alice@example.com', password=PASSWORD
        )

    def setUp(self):
        self.client.force_login(self.alice)

    def test_post_logout_logs_out_and_redirects_to_login(self):
        """AC-12: POST logout logs out and lands on the login page."""
        response = self.client.post(reverse('accounts:logout'))
        self.assertRedirects(response, reverse('accounts:login'))
        self.assertFalse(get_user(self.client).is_authenticated)
        dash = self.client.get(reverse('core:dashboard'))
        self.assertEqual(dash.status_code, 302)

    def test_post_logout_shows_confirmation_message(self):
        """AC-12: the 'logged out' message appears on the login page."""
        response = self.client.post(reverse('accounts:logout'), follow=True)
        self.assertEqual(response.redirect_chain[-1][0], reverse('accounts:login'))
        texts = [str(m) for m in response.context['messages']]
        self.assertIn('You have been logged out.', texts)
        self.assertContains(response, 'You have been logged out.')

    def test_get_logout_does_not_log_out(self):
        """AC-13: GET logout is rejected (405) and the user stays logged in."""
        response = self.client.get(reverse('accounts:logout'))
        self.assertEqual(response.status_code, 405)
        self.assertTrue(get_user(self.client).is_authenticated)
        dash = self.client.get(reverse('core:dashboard'))
        self.assertEqual(dash.status_code, 200)


class CsrfTests(TestCase):
    """AC-23: forms posted without the anti-forgery token are rejected."""

    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user(
            username='Alice', email='alice@example.com', password=PASSWORD
        )

    def setUp(self):
        self.csrf_client = Client(enforce_csrf_checks=True)

    def test_register_without_token_rejected(self):
        """AC-23: register POST without a token → 403, no user created."""
        response = self.csrf_client.post(reverse('accounts:register'), {
            'username': 'Mallory', 'email': 'mallory@example.com',
            'password1': PASSWORD, 'password2': PASSWORD,
        })
        self.assertEqual(response.status_code, 403)
        self.assertFalse(User.objects.filter(username__iexact='Mallory').exists())
        self.assertFalse(get_user(self.csrf_client).is_authenticated)

    def test_login_without_token_rejected(self):
        """AC-23: login POST without a token → 403, not logged in."""
        response = self.csrf_client.post(
            reverse('accounts:login'),
            {'username': 'Alice', 'password': PASSWORD},
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(get_user(self.csrf_client).is_authenticated)

    def test_logout_without_token_rejected(self):
        """AC-23: logout POST without a token → 403, still logged in."""
        self.csrf_client.force_login(self.alice)
        response = self.csrf_client.post(reverse('accounts:logout'))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(get_user(self.csrf_client).is_authenticated)
        dash = self.csrf_client.get(reverse('core:dashboard'))
        self.assertEqual(dash.status_code, 200)

    def test_login_with_token_succeeds(self):
        """AC-23 (control): the same login with a valid token works."""
        self.csrf_client.get(reverse('accounts:login'))
        token = self.csrf_client.cookies['csrftoken'].value
        response = self.csrf_client.post(reverse('accounts:login'), {
            'username': 'Alice', 'password': PASSWORD,
            'csrfmiddlewaretoken': token,
        })
        self.assertRedirects(response, reverse('core:dashboard'))
        self.assertTrue(get_user(self.csrf_client).is_authenticated)
