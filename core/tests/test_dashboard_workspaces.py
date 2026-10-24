"""Dashboard workspace-list tests (spec 02).

These cover the spec 02 acceptance criteria that concern the dashboard. Tags
read "spec 02 AC-n" so they are not confused with spec 01's numbering, which
core/tests/test_views.py uses.
"""
import re

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from workspaces.models import Workspace

PASSWORD = 'Str0ng-Passw0rd!x'

User = get_user_model()


class DashboardWorkspaceListTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user(
            username='Alice', email='alice@example.com', password=PASSWORD
        )
        cls.bob = User.objects.create_user(
            username='Bob', email='bob@example.com', password=PASSWORD
        )
        cls.carol = User.objects.create_user(
            username='Carol', email='carol@example.com', password=PASSWORD
        )
        # Bob owns W1, is a member of W2, and isn't in W3.
        cls.w1 = Workspace.objects.create_with_owner('Bob Owned', cls.bob)
        cls.w2 = Workspace.objects.create_with_owner('Alice Shared', cls.alice)
        cls.w2.add_member(cls.bob)
        cls.w3 = Workspace.objects.create_with_owner('Carol Private', cls.carol)

    def detail_href(self, ws):
        return 'href="%s"' % reverse('workspaces:detail', args=[ws.pk])

    def test_lists_links_to_own_workspaces_and_create_link(self):
        """spec 02 AC-9: dashboard links to each of the user's workspaces and to create."""
        self.client.force_login(self.alice)
        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn(self.detail_href(self.w2), html)
        self.assertContains(response, 'Alice Shared')
        self.assertIn('href="%s"' % reverse('workspaces:create'), html)

    def test_empty_state(self):
        """spec 02 AC-10: no workspaces → empty message and the create link."""
        dave = User.objects.create_user(username='Dave', password=PASSWORD)
        self.client.force_login(dave)
        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "You don't belong to any workspaces yet.")
        self.assertContains(response, 'href="%s"' % reverse('workspaces:create'))
        self.assertEqual(list(response.context['workspaces']), [])

    def test_owned_and_joined_listed_others_hidden(self):
        """spec 02 AC-11: Bob sees W1 (owned) and W2 (joined) but never W3; each opens."""
        self.client.force_login(self.bob)
        response = self.client.get(reverse('core:dashboard'))
        html = response.content.decode()
        self.assertIn(self.detail_href(self.w1), html)
        self.assertIn(self.detail_href(self.w2), html)
        self.assertNotIn(self.detail_href(self.w3), html)
        self.assertContains(response, 'Bob Owned')
        self.assertContains(response, 'Alice Shared')
        self.assertNotContains(response, 'Carol Private')
        self.assertEqual(
            {w.pk for w in response.context['workspaces']},
            {self.w1.pk, self.w2.pk},
        )
        for ws in (self.w1, self.w2):
            with self.subTest(ws=ws.name):
                detail = self.client.get(reverse('workspaces:detail', args=[ws.pk]))
                self.assertEqual(detail.status_code, 200)

    def test_newly_added_member_sees_workspace(self):
        """spec 02 AC-18: after Carol adds Alice, Alice's dashboard lists the workspace."""
        self.client.force_login(self.alice)
        before = self.client.get(reverse('core:dashboard'))
        self.assertNotContains(before, 'Carol Private')

        self.client.force_login(self.carol)
        self.client.post(
            reverse('workspaces:add_member', args=[self.w3.pk]),
            {'username': 'alice'},
        )

        self.client.force_login(self.alice)
        response = self.client.get(reverse('core:dashboard'))
        self.assertContains(response, 'Carol Private')
        self.assertIn(self.detail_href(self.w3), response.content.decode())
        detail = self.client.get(reverse('workspaces:detail', args=[self.w3.pk]))
        self.assertEqual(detail.status_code, 200)
        self.assertIsNone(
            re.search(
                r'<form[^>]*action="%s"'
                % re.escape(reverse('workspaces:add_member', args=[self.w3.pk])),
                detail.content.decode(),
            )
        )

    def test_script_workspace_name_escaped(self):
        """spec 02 AC-8: a script-like workspace name is escaped on the dashboard."""
        Workspace.objects.create_with_owner('<script>alert(1)</script>', self.alice)
        self.client.force_login(self.alice)
        response = self.client.get(reverse('core:dashboard'))
        self.assertContains(response, '&lt;script&gt;alert(1)&lt;/script&gt;')
        self.assertNotContains(response, '<script>alert(1)</script>')
