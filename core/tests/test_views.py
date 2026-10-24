"""Dashboard, root redirect and navigation tests (spec 01)."""
import re

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

PASSWORD = 'Str0ng-Passw0rd!x'

User = get_user_model()


def nav_html(response):
    """Return just the <nav>...</nav> part of the page."""
    match = re.search(r'<nav\b.*?</nav>', response.content.decode(), re.S)
    assert match, 'page has no <nav>'
    return match.group(0)


class DashboardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user(
            username='Alice', email='alice@example.com', password=PASSWORD
        )

    def test_anonymous_redirected_to_login_with_next(self):
        """AC-15: anonymous dashboard → login, remembering the page."""
        response = self.client.get(reverse('core:dashboard'))
        expected = '%s?next=%s' % (
            reverse('accounts:login'), reverse('core:dashboard')
        )
        self.assertRedirects(response, expected)

    def test_logged_in_user_sees_dashboard(self):
        """AC-14: a logged-in user gets the dashboard (200)."""
        self.client.force_login(self.alice)
        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/dashboard.html')

    def test_greeting_uses_registered_casing(self):
        """AC-14: logged in as 'alice', the greeting still says 'Alice'."""
        response = self.client.post(
            reverse('accounts:login'),
            {'username': 'alice', 'password': PASSWORD},
        )
        self.assertRedirects(response, reverse('core:dashboard'))
        response = self.client.get(reverse('core:dashboard'))
        self.assertContains(response, 'Welcome, Alice')
        self.assertNotContains(response, 'Welcome, alice')

    def test_dashboard_does_not_display_password(self):
        """AC-22: the raw password is not displayed on the dashboard."""
        self.client.force_login(self.alice)
        response = self.client.get(reverse('core:dashboard'))
        self.assertNotContains(response, PASSWORD)


class RootRedirectTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user(
            username='Alice', email='alice@example.com', password=PASSWORD
        )

    def test_anonymous_root_goes_to_login(self):
        """AC-19: anonymous visitor at / lands on the login page."""
        response = self.client.get(reverse('core:home'))
        self.assertRedirects(response, reverse('accounts:login'))

    def test_logged_in_root_goes_to_dashboard(self):
        """AC-19: logged-in user at / lands on the dashboard."""
        self.client.force_login(self.alice)
        response = self.client.get(reverse('core:home'))
        self.assertRedirects(response, reverse('core:dashboard'))


class NavigationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user(
            username='Alice', email='alice@example.com', password=PASSWORD
        )

    def test_anonymous_nav(self):
        """AC-20: anonymous nav shows Log in/Register, not Dashboard/Log out."""
        for url_name in ('accounts:login', 'accounts:register'):
            with self.subTest(page=url_name):
                response = self.client.get(reverse(url_name))
                self.assertEqual(response.status_code, 200)
                nav = nav_html(response)
                self.assertIn('Log in', nav)
                self.assertIn('Register', nav)
                self.assertIn('href="%s"' % reverse('accounts:login'), nav)
                self.assertIn('href="%s"' % reverse('accounts:register'), nav)
                self.assertNotIn('Log out', nav)
                self.assertNotIn('Dashboard', nav)
                self.assertNotIn(reverse('accounts:logout'), nav)

    def test_logged_in_nav(self):
        """AC-21: logged-in nav shows username, Dashboard, Log out form only."""
        self.client.post(
            reverse('accounts:login'),
            {'username': 'ALICE', 'password': PASSWORD},
        )
        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 200)
        nav = nav_html(response)
        self.assertIn('Alice', nav)
        self.assertNotIn('ALICE', nav)
        self.assertIn('Dashboard', nav)
        self.assertIn('href="%s"' % reverse('core:dashboard'), nav)
        self.assertIn('Log out', nav)
        form = re.search(
            r'<form[^>]*action="%s"[^>]*>' % re.escape(reverse('accounts:logout')),
            nav,
        )
        self.assertIsNotNone(form, 'logout must be a form')
        self.assertIn('method="post"', form.group(0).lower())
        self.assertIn('csrfmiddlewaretoken', nav)
        self.assertNotIn('Log in', nav)
        self.assertNotIn('Register', nav)
        self.assertNotIn('href="%s"' % reverse('accounts:login'), nav)
        self.assertNotIn('href="%s"' % reverse('accounts:register'), nav)
