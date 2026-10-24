"""WorkspaceForm and AddMemberForm tests (spec 02).

Case-insensitivity tests use ASCII names only (plan 01, D-3).
"""
from django.contrib.auth import get_user_model
from django.test import TestCase

from workspaces.forms import AddMemberForm, WorkspaceForm
from workspaces.models import Workspace

PASSWORD = 'Str0ng-Passw0rd!x'
NOT_FOUND = 'No user with that username was found.'

User = get_user_model()


class WorkspaceFormTests(TestCase):
    def test_empty_and_blank_names_rejected(self):
        """spec 02 AC-3: '' and '   ' give an error on name."""
        for value in ('', '   '):
            with self.subTest(value=repr(value)):
                form = WorkspaceForm(data={'name': value})
                self.assertFalse(form.is_valid())
                self.assertIn('name', form.errors)

    def test_name_is_trimmed(self):
        """spec 02 AC-3: spaces at the start and end are removed."""
        form = WorkspaceForm(data={'name': '  Apollo  '})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['name'], 'Apollo')

    def test_name_over_100_rejected_with_limit(self):
        """spec 02 AC-4: 101 characters → name error stating the limit of 100."""
        form = WorkspaceForm(data={'name': 'a' * 101})
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
        self.assertIn('100', ' '.join(form.errors['name']))

    def test_name_of_100_accepted(self):
        """spec 02 AC-4: exactly 100 characters is accepted."""
        form = WorkspaceForm(data={'name': 'a' * 100})
        self.assertTrue(form.is_valid(), form.errors)


class AddMemberFormTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user(username='Alice', password=PASSWORD)
        cls.bob = User.objects.create_user(username='Bob', password=PASSWORD)
        cls.carol = User.objects.create_user(username='Carol', password=PASSWORD)
        cls.dave = User.objects.create_user(
            username='Dave', password=PASSWORD, is_active=False
        )
        cls.ws = Workspace.objects.create_with_owner('Apollo', cls.alice)
        cls.ws.add_member(cls.bob)

    def form(self, username):
        return AddMemberForm(data={'username': username}, workspace=self.ws)

    def test_exact_username_valid(self):
        """spec 02 AC-13: an active non-member's username is valid and resolves the user."""
        form = self.form('Carol')
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.user, self.carol)

    def test_username_case_ignored(self):
        """spec 02 AC-14: 'CAROL' finds 'Carol'."""
        form = self.form('CAROL')
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.user, self.carol)
        self.assertEqual(form.user.username, 'Carol')

    def test_existing_member_rejected(self):
        """spec 02 AC-15: an existing member gives an 'already a member' field error."""
        for value in ('Bob', 'BOB'):
            with self.subTest(value=value):
                form = self.form(value)
                self.assertFalse(form.is_valid())
                self.assertEqual(
                    form.errors['username'],
                    ['Bob is already a member of this workspace.'],
                )

    def test_owner_own_name_rejected(self):
        """spec 02 AC-15: the owner's own username (any case) → already a member."""
        form = self.form('alice')
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors['username'],
            ['Alice is already a member of this workspace.'],
        )

    def test_unknown_and_inactive_same_error(self):
        """spec 02 AC-16: unknown and deactivated users get the same not-found error."""
        for value in ('nobody', 'Dave', 'dave'):
            with self.subTest(value=value):
                form = self.form(value)
                self.assertFalse(form.is_valid())
                self.assertEqual(form.errors['username'], [NOT_FOUND])

    def test_empty_username_rejected(self):
        """spec 02 AC-17: empty username → error on username."""
        for value in ('', '   '):
            with self.subTest(value=repr(value)):
                form = self.form(value)
                self.assertFalse(form.is_valid())
                self.assertIn('username', form.errors)
