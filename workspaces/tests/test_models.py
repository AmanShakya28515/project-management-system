"""Workspace and Membership model tests (spec 02).

Case-insensitivity tests use ASCII names only (plan 01, D-3).
"""
from unittest import mock

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase

from workspaces.models import Membership, Workspace

PASSWORD = 'Str0ng-Passw0rd!x'

User = get_user_model()


class CreateWithOwnerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user(username='Alice', password=PASSWORD)

    def test_create_with_owner_sets_owner_and_membership(self):
        """spec 02 AC-2 / AC-27: the creator is the owner and also a member."""
        ws = Workspace.objects.create_with_owner('Apollo', self.alice)
        ws.refresh_from_db()
        self.assertEqual(ws.name, 'Apollo')
        self.assertEqual(ws.owner, self.alice)
        self.assertTrue(ws.is_owner(self.alice))
        self.assertEqual(
            list(Membership.objects.filter(workspace=ws).values_list('user', flat=True)),
            [self.alice.pk],
        )

    def test_owner_cannot_be_null(self):
        """spec 02 AC-27: a workspace must have an owner (database refuses NULL)."""
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Workspace.objects.create(name='Orphan', owner=None)
        self.assertFalse(Workspace.objects.filter(name='Orphan').exists())

    def test_create_with_owner_is_atomic(self):
        """spec 02 AC-27: if the owner's membership fails, no workspace row remains."""
        before = Workspace.objects.count()
        with mock.patch.object(
            Membership.objects, 'create', side_effect=IntegrityError('boom')
        ):
            with self.assertRaises(IntegrityError):
                Workspace.objects.create_with_owner('Broken', self.alice)
        self.assertEqual(Workspace.objects.count(), before)
        self.assertFalse(Workspace.objects.filter(name='Broken').exists())
        self.assertFalse(Membership.objects.exists())

    def test_deleting_owner_is_protected(self):
        """spec 02 AC-27 (plan D-1): an owner can't be deleted out from under a workspace."""
        bob = User.objects.create_user(username='Bob', password=PASSWORD)
        ws = Workspace.objects.create_with_owner('Apollo', bob)
        with self.assertRaises(ProtectedError):
            bob.delete()
        ws.refresh_from_db()
        self.assertEqual(ws.owner_id, bob.pk)

    def test_names_are_not_unique(self):
        """spec 02 AC-5: the same name can be used for separate workspaces."""
        w1 = Workspace.objects.create_with_owner('Apollo', self.alice)
        w2 = Workspace.objects.create_with_owner('Apollo', self.alice)
        self.assertNotEqual(w1.pk, w2.pk)


class ForUserTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user(username='Alice', password=PASSWORD)
        cls.bob = User.objects.create_user(username='Bob', password=PASSWORD)
        cls.carol = User.objects.create_user(username='Carol', password=PASSWORD)
        # Bob owns W1, is a member of W2, and isn't in W3.
        cls.w1 = Workspace.objects.create_with_owner('W1', cls.bob)
        cls.w2 = Workspace.objects.create_with_owner('W2', cls.alice)
        cls.w2.add_member(cls.bob)
        cls.w3 = Workspace.objects.create_with_owner('W3', cls.carol)

    def test_for_user_returns_owned_and_joined_only(self):
        """spec 02 AC-11: for_user(bob) is exactly the owned and joined workspaces."""
        result = list(Workspace.objects.for_user(self.bob))
        self.assertEqual(len(result), 2)  # no duplicates
        self.assertEqual({w.pk for w in result}, {self.w1.pk, self.w2.pk})

    def test_for_user_excludes_non_member_workspace(self):
        """spec 02 AC-21: a non-member's scoped queryset doesn't include the workspace."""
        self.assertFalse(
            Workspace.objects.for_user(self.carol).filter(pk=self.w2.pk).exists()
        )

    def test_for_user_anonymous_is_empty(self):
        """spec 02 AC-21: an anonymous user sees no workspaces."""
        from django.contrib.auth.models import AnonymousUser

        self.assertEqual(Workspace.objects.for_user(AnonymousUser()).count(), 0)


class AddMemberModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user(username='Alice', password=PASSWORD)
        cls.bob = User.objects.create_user(username='Bob', password=PASSWORD)
        cls.ws = Workspace.objects.create_with_owner('Apollo', cls.alice)

    def test_add_member_creates_membership(self):
        """spec 02 AC-13: add_member adds a new member."""
        membership, created = self.ws.add_member(self.bob)
        self.assertTrue(created)
        self.assertEqual(membership.user, self.bob)
        self.assertEqual(membership.workspace, self.ws)

    def test_add_member_twice_is_idempotent(self):
        """spec 02 AC-15 / AC-26: a second add returns created=False and keeps 1 row."""
        self.ws.add_member(self.bob)
        _, created = self.ws.add_member(self.bob)
        self.assertFalse(created)
        self.assertEqual(
            Membership.objects.filter(workspace=self.ws, user=self.bob).count(), 1
        )

    def test_add_owner_again_is_idempotent(self):
        """spec 02 AC-15 / AC-27: adding the owner does not create a second row."""
        _, created = self.ws.add_member(self.alice)
        self.assertFalse(created)
        self.assertEqual(
            Membership.objects.filter(workspace=self.ws, user=self.alice).count(), 1
        )

    def test_duplicate_membership_rejected_by_database(self):
        """spec 02 AC-26: the unique constraint refuses a duplicate membership row."""
        Membership.objects.create(workspace=self.ws, user=self.bob)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Membership.objects.create(workspace=self.ws, user=self.bob)
        self.assertEqual(
            Membership.objects.filter(workspace=self.ws, user=self.bob).count(), 1
        )


class MemberListTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.zed = User.objects.create_user(username='Zed', password=PASSWORD)
        cls.carol = User.objects.create_user(username='carol', password=PASSWORD)
        cls.bob = User.objects.create_user(username='Bob', password=PASSWORD)
        cls.alice = User.objects.create_user(username='alice', password=PASSWORD)
        cls.ws = Workspace.objects.create_with_owner('Apollo', cls.zed)
        for user in (cls.carol, cls.bob, cls.alice):
            cls.ws.add_member(user)

    def test_owner_first_then_case_insensitive_alphabetical(self):
        """spec 02 AC-7: owner first, then members by username ignoring case."""
        names = [m.user.username for m in self.ws.member_list()]
        self.assertEqual(names, ['Zed', 'alice', 'Bob', 'carol'])

    def test_each_user_listed_once(self):
        """spec 02 AC-26: every member appears exactly once in the list."""
        self.ws.add_member(self.bob)
        names = [m.user.username for m in self.ws.member_list()]
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(len(names), 4)

    def test_is_owner(self):
        """spec 02 AC-7 / AC-27: only the owner is the owner."""
        self.assertTrue(self.ws.is_owner(self.zed))
        for user in (self.alice, self.bob, self.carol):
            with self.subTest(user=user.username):
                self.assertFalse(self.ws.is_owner(user))
