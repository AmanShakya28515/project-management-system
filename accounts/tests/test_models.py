"""Model-level tests for accounts.User and its manager (spec 01).

Case-insensitivity tests use ASCII names only (plan 01, D-3).
"""
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

PASSWORD = 'Str0ng-Passw0rd!x'

User = get_user_model()


class UsernameConstraintTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user(
            username='Alice', email='alice@example.com', password=PASSWORD
        )

    def test_db_rejects_username_differing_only_in_case(self):
        """AC-3: the database rejects 'alice' when 'Alice' exists."""
        for variant in ('alice', 'ALICE', 'aLiCe'):
            with self.subTest(variant=variant):
                with self.assertRaises(IntegrityError):
                    with transaction.atomic():
                        User.objects.create_user(
                            username=variant,
                            email=f'{variant}-other@example.com',
                            password=PASSWORD,
                        )
        self.assertEqual(User.objects.count(), 1)

    def test_db_allows_distinct_username(self):
        """AC-3: a genuinely different username is still accepted."""
        User.objects.create_user(
            username='Bob', email='bob@example.com', password=PASSWORD
        )
        self.assertEqual(User.objects.count(), 2)


class EmailConstraintTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user(
            username='Alice', email='a@x.com', password=PASSWORD
        )

    def test_db_rejects_email_differing_only_in_case(self):
        """AC-4: the database rejects 'A@X.com' when 'a@x.com' exists."""
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.create_user(
                    username='Bob', email='A@X.com', password=PASSWORD
                )
        self.assertEqual(User.objects.count(), 1)

    def test_db_rejects_exact_duplicate_email(self):
        """AC-4: the database rejects an exact duplicate email."""
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.create_user(
                    username='Bob', email='a@x.com', password=PASSWORD
                )

    def test_two_blank_emails_are_allowed(self):
        """AC-4: blank emails (e.g. createsuperuser) do not collide."""
        User.objects.create_user(username='Bob', email='', password=PASSWORD)
        User.objects.create_user(username='Carol', email='', password=PASSWORD)
        self.assertEqual(User.objects.filter(email='').count(), 2)


class ManagerNaturalKeyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user(
            username='Alice', email='alice@example.com', password=PASSWORD
        )

    def test_get_by_natural_key_ignores_case(self):
        """AC-9: get_by_natural_key matches the username ignoring case."""
        for variant in ('Alice', 'alice', 'ALICE', 'aLiCe'):
            with self.subTest(variant=variant):
                self.assertEqual(
                    User.objects.get_by_natural_key(variant), self.alice
                )

    def test_get_by_natural_key_unknown_raises(self):
        """AC-9: an unknown username is not matched."""
        with self.assertRaises(User.DoesNotExist):
            User.objects.get_by_natural_key('nobody')

    def test_stored_username_keeps_original_casing(self):
        """AC-9: the stored username keeps the casing chosen at creation."""
        self.alice.refresh_from_db()
        self.assertEqual(self.alice.username, 'Alice')


class PasswordStorageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user(
            username='Alice', email='alice@example.com', password=PASSWORD
        )

    def test_password_is_not_stored_in_plain_text(self):
        """AC-22: the stored password is a hash, not the raw value."""
        self.alice.refresh_from_db()
        self.assertNotEqual(self.alice.password, PASSWORD)
        self.assertNotIn(PASSWORD, self.alice.password)
        self.assertTrue(self.alice.has_usable_password())

    def test_original_password_still_verifies(self):
        """AC-22: the original password checks out against the stored hash."""
        self.alice.refresh_from_db()
        self.assertTrue(self.alice.check_password(PASSWORD))
        self.assertFalse(self.alice.check_password('wrong-' + PASSWORD))
