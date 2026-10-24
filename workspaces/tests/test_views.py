"""Workspace create / detail / add-member view tests (spec 02).

Users: Alice (owner), Bob (member), Carol (signed-in non-member), Dave
(inactive). Case-insensitivity tests use ASCII names only (plan 01, D-3).
"""
import re
from unittest import mock

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from workspaces.forms import AddMemberForm
from workspaces.models import Membership, Workspace

PASSWORD = 'Str0ng-Passw0rd!x'
NOT_FOUND = 'No user with that username was found.'

User = get_user_model()


def find_input(html, name):
    """Return the <input ...> tag with the given name, or None."""
    match = re.search(r'<input[^>]*\bname="%s"[^>]*>' % re.escape(name), html)
    return match.group(0) if match else None


def message_texts(response):
    return [str(m) for m in messages.get_messages(response.wsgi_request)]


def member_rows(response):
    """Member list rows as (username-as-html, label) pairs, in page order.

    A row is any <li> whose visible text ends with 'Owner' or 'Member'.
    Usernames stay HTML-escaped, exactly as they appear in the page.
    """
    rows = []
    for li in re.findall(r'<li\b[^>]*>(.*?)</li>', response.content.decode(), re.S):
        text = ' '.join(re.sub(r'<[^>]+>', ' ', li).split())
        match = re.fullmatch(r'(.+) (Owner|Member)', text)
        if match:
            rows.append((match.group(1), match.group(2)))
    return rows


def add_member_form_tag(html, workspace):
    action = re.escape(reverse('workspaces:add_member', args=[workspace.pk]))
    match = re.search(r'<form[^>]*action="%s"[^>]*>' % action, html)
    return match.group(0) if match else None


class WorkspaceTestData(TestCase):
    """Shared users and one workspace: Alice owns Apollo, Bob is a member."""

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
        cls.dave = User.objects.create_user(
            username='Dave', email='dave@example.com', password=PASSWORD,
            is_active=False,
        )
        cls.ws = Workspace.objects.create_with_owner('Apollo Secret', cls.alice)
        cls.ws.add_member(cls.bob)

    def detail_url(self, ws=None):
        return reverse('workspaces:detail', args=[(ws or self.ws).pk])

    def add_url(self, ws=None):
        return reverse('workspaces:add_member', args=[(ws or self.ws).pk])

    def missing_pk(self):
        return (Workspace.objects.order_by('-pk').values_list('pk', flat=True).first() or 0) + 1000


# --------------------------------------------------------------------------
# Creating a workspace
# --------------------------------------------------------------------------
class CreateWorkspaceTests(WorkspaceTestData):
    def test_create_page_shows_name_form(self):
        """spec 02 AC-1: logged-in GET shows a form with a name field."""
        self.client.force_login(self.carol)
        response = self.client.get(reverse('workspaces:create'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'workspaces/workspace_form.html')
        self.assertIn('name', response.context['form'].fields)
        self.assertIsNotNone(find_input(response.content.decode(), 'name'))

    def test_valid_post_creates_workspace_owner_and_membership(self):
        """spec 02 AC-2: valid name → workspace, owner, membership, redirect, message."""
        self.client.force_login(self.carol)
        before = Workspace.objects.count()
        response = self.client.post(reverse('workspaces:create'), {'name': 'Apollo'})
        self.assertEqual(Workspace.objects.count(), before + 1)
        ws = Workspace.objects.get(name='Apollo')
        self.assertEqual(ws.owner, self.carol)
        self.assertEqual(
            list(ws.memberships.values_list('user', flat=True)), [self.carol.pk]
        )
        self.assertRedirects(response, self.detail_url(ws), fetch_redirect_response=False)
        page = self.client.get(self.detail_url(ws))
        self.assertContains(page, 'Workspace &quot;Apollo&quot; was created.')
        self.assertContains(page, 'Apollo')
        self.assertEqual(member_rows(page), [('Carol', 'Owner')])

    def test_empty_or_blank_name_rejected(self):
        """spec 02 AC-3: '' and '   ' → name error, no workspace created."""
        self.client.force_login(self.carol)
        before = Workspace.objects.count()
        for value in ('', '   '):
            with self.subTest(value=repr(value)):
                response = self.client.post(reverse('workspaces:create'), {'name': value})
                self.assertEqual(response.status_code, 200)
                self.assertIn('name', response.context['form'].errors)
                self.assertEqual(Workspace.objects.count(), before)

    def test_name_is_trimmed_before_saving(self):
        """spec 02 AC-3: '  Apollo  ' is stored as 'Apollo'."""
        self.client.force_login(self.carol)
        self.client.post(reverse('workspaces:create'), {'name': '  Trimmed  '})
        ws = Workspace.objects.get(owner=self.carol)
        self.assertEqual(ws.name, 'Trimmed')

    def test_name_too_long_rejected_and_kept(self):
        """spec 02 AC-4: 101 chars → error stating 100, nothing created, value kept."""
        self.client.force_login(self.carol)
        before = Workspace.objects.count()
        long_name = 'x' * 101
        response = self.client.post(reverse('workspaces:create'), {'name': long_name})
        self.assertEqual(response.status_code, 200)
        errors = response.context['form'].errors['name']
        self.assertIn('100', ' '.join(errors))
        self.assertEqual(Workspace.objects.count(), before)
        tag = find_input(response.content.decode(), 'name')
        self.assertIsNotNone(tag)
        self.assertIn('value="%s"' % long_name, tag)

    def test_name_of_100_accepted(self):
        """spec 02 AC-4: exactly 100 characters is accepted."""
        self.client.force_login(self.carol)
        name = 'y' * 100
        self.client.post(reverse('workspaces:create'), {'name': name})
        self.assertTrue(Workspace.objects.filter(name=name, owner=self.carol).exists())

    def test_duplicate_names_create_separate_workspaces(self):
        """spec 02 AC-5: same name twice by Alice and once by Bob → 3 workspaces."""
        url = reverse('workspaces:create')
        self.client.force_login(self.alice)
        self.client.post(url, {'name': 'Apollo'})
        self.client.post(url, {'name': 'Apollo'})
        self.client.force_login(self.bob)
        self.client.post(url, {'name': 'Apollo'})
        created = Workspace.objects.filter(name='Apollo')
        self.assertEqual(created.count(), 3)
        self.assertEqual(created.filter(owner=self.alice).count(), 2)
        self.assertEqual(created.filter(owner=self.bob).count(), 1)
        for ws in created:
            with self.subTest(pk=ws.pk):
                self.assertTrue(ws.memberships.filter(user=ws.owner).exists())
                self.assertEqual(ws.memberships.count(), 1)

    def test_get_with_query_creates_nothing(self):
        """spec 02 AC-25: GET create?name=X only shows the form."""
        self.client.force_login(self.carol)
        before = Workspace.objects.count()
        response = self.client.get(reverse('workspaces:create') + '?name=Sneaky')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'workspaces/workspace_form.html')
        self.assertEqual(Workspace.objects.count(), before)
        self.assertFalse(Workspace.objects.filter(name='Sneaky').exists())


# --------------------------------------------------------------------------
# Viewing a workspace
# --------------------------------------------------------------------------
class DetailViewTests(WorkspaceTestData):
    def test_owner_and_member_see_name_and_members(self):
        """spec 02 AC-6: owner and member both see the name and every member."""
        for user in (self.alice, self.bob):
            with self.subTest(user=user.username):
                self.client.force_login(user)
                response = self.client.get(self.detail_url())
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, 'workspaces/workspace_detail.html')
                self.assertContains(response, 'Apollo Secret')
                names = [name for name, _ in member_rows(response)]
                self.assertEqual(names, ['Alice', 'Bob'])

    def test_member_shown_with_registered_casing(self):
        """spec 02 AC-6: 'Bob' is shown as 'Bob', not 'bob' or 'BOB'."""
        self.client.force_login(self.alice)
        response = self.client.get(self.detail_url())
        names = [name for name, _ in member_rows(response)]
        self.assertIn('Bob', names)
        self.assertNotIn('bob', names)
        self.assertNotIn('BOB', names)

    def test_owner_label_and_member_label(self):
        """spec 02 AC-7: owner labelled Owner, others labelled Member."""
        self.client.force_login(self.bob)
        response = self.client.get(self.detail_url())
        self.assertEqual(member_rows(response), [('Alice', 'Owner'), ('Bob', 'Member')])

    def test_member_with_html_username_is_escaped(self):
        """spec 02 AC-8: a username containing HTML is escaped in the member list."""
        # Deliberately bypasses the registration form's username rules: test data only.
        evil = User.objects.create_user(username='<b>x</b>', password=PASSWORD)
        self.ws.add_member(evil)
        self.client.force_login(self.alice)
        response = self.client.get(self.detail_url())
        self.assertContains(response, '&lt;b&gt;x&lt;/b&gt;')
        self.assertNotContains(response, '<b>x</b>')
        self.assertIn(('&lt;b&gt;x&lt;/b&gt;', 'Member'), member_rows(response))

    def test_workspace_name_with_script_is_escaped(self):
        """spec 02 AC-8: a script-like workspace name is shown as plain text."""
        ws = Workspace.objects.create_with_owner('<script>alert(1)</script>', self.carol)
        self.client.force_login(self.carol)
        response = self.client.get(self.detail_url(ws))
        self.assertContains(response, '&lt;script&gt;alert(1)&lt;/script&gt;')
        self.assertNotContains(response, '<script>alert(1)</script>')

    def test_created_message_with_script_name_is_escaped(self):
        """spec 02 AC-8: the 'created' confirmation escapes a script-like name."""
        self.client.force_login(self.carol)
        response = self.client.post(
            reverse('workspaces:create'),
            {'name': '<script>alert(1)</script>'},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '<script>alert(1)</script>')
        html = response.content.decode()
        # Escaped in both the <h1> and the success message.
        self.assertGreaterEqual(html.count('&lt;script&gt;alert(1)&lt;/script&gt;'), 2)

    def test_owner_sees_add_member_form(self):
        """spec 02 AC-12: the owner's page has a form posting to add_member with username."""
        self.client.force_login(self.alice)
        response = self.client.get(self.detail_url())
        html = response.content.decode()
        tag = add_member_form_tag(html, self.ws)
        self.assertIsNotNone(tag)
        self.assertIn('method="post"', tag.lower())
        self.assertIsNotNone(find_input(html, 'username'))
        self.assertIn('csrfmiddlewaretoken', html)

    def test_member_sees_no_add_member_form(self):
        """spec 02 AC-19: a non-owner member sees name and members but no add form."""
        self.client.force_login(self.bob)
        response = self.client.get(self.detail_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Apollo Secret')
        self.assertEqual(len(member_rows(response)), 2)
        html = response.content.decode()
        self.assertNotIn(self.add_url(), html)
        self.assertIsNone(find_input(html, 'username'))
        self.assertNotIn('add_member_form', response.context)

    def test_non_member_gets_404_without_leaking(self):
        """spec 02 AC-21: non-member detail → 404 with no name or members in it."""
        self.client.force_login(self.carol)
        response = self.client.get(self.detail_url())
        self.assertEqual(response.status_code, 404)
        self.assertNotContains(response, 'Apollo Secret', status_code=404)
        self.assertNotContains(response, 'Alice', status_code=404)
        self.assertNotContains(response, 'Bob', status_code=404)

    def test_missing_id_gives_same_404(self):
        """spec 02 AC-21: a missing workspace ID gives 404 for a non-member and an owner."""
        url = reverse('workspaces:detail', args=[self.missing_pk()])
        for user in (self.carol, self.alice):
            with self.subTest(user=user.username):
                self.client.force_login(user)
                self.assertEqual(self.client.get(url).status_code, 404)

    def test_owner_of_other_workspace_gets_404(self):
        """spec 02 AC-21: owning another workspace gives no access to this one."""
        Workspace.objects.create_with_owner('Carol HQ', self.carol)
        self.client.force_login(self.carol)
        self.assertEqual(self.client.get(self.detail_url()).status_code, 404)


# --------------------------------------------------------------------------
# Adding members
# --------------------------------------------------------------------------
class AddMemberViewTests(WorkspaceTestData):
    def member_count(self):
        return Membership.objects.filter(workspace=self.ws).count()

    def test_owner_adds_member(self):
        """spec 02 AC-13: owner adds Carol → membership, redirect, message, listed as Member."""
        self.client.force_login(self.alice)
        response = self.client.post(self.add_url(), {'username': 'Carol'})
        self.assertRedirects(response, self.detail_url(), fetch_redirect_response=False)
        self.assertTrue(self.ws.memberships.filter(user=self.carol).exists())
        page = self.client.get(self.detail_url())
        self.assertContains(page, 'Carol was added to the workspace.')
        self.assertIn(('Carol', 'Member'), member_rows(page))

    def test_username_case_ignored(self):
        """spec 02 AC-14: 'CAROL' adds 'Carol', and the list shows 'Carol'."""
        self.client.force_login(self.alice)
        response = self.client.post(self.add_url(), {'username': 'CAROL'}, follow=True)
        self.assertTrue(self.ws.memberships.filter(user=self.carol).exists())
        names = [name for name, _ in member_rows(response)]
        self.assertIn('Carol', names)
        self.assertNotIn('CAROL', names)

    def test_existing_member_or_owner_not_duplicated(self):
        """spec 02 AC-15: existing member / owner's own name → 'already a member', no change."""
        self.client.force_login(self.alice)
        before = self.member_count()
        cases = [('Bob', 'Bob'), ('bob', 'Bob'), ('alice', 'Alice'), ('Alice', 'Alice')]
        for typed, stored in cases:
            with self.subTest(typed=typed):
                response = self.client.post(self.add_url(), {'username': typed})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    response.context['add_member_form'].errors['username'],
                    ['%s is already a member of this workspace.' % stored],
                )
                self.assertContains(
                    response, '%s is already a member of this workspace.' % stored
                )
                self.assertEqual(self.member_count(), before)
                self.assertEqual(
                    member_rows(response), [('Alice', 'Owner'), ('Bob', 'Member')]
                )

    def test_unknown_or_inactive_user_not_found(self):
        """spec 02 AC-16: unknown 'nobody' and inactive 'Dave' → not-found error, value kept."""
        self.client.force_login(self.alice)
        before = self.member_count()
        for typed in ('nobody', 'Dave'):
            with self.subTest(typed=typed):
                response = self.client.post(self.add_url(), {'username': typed})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    response.context['add_member_form'].errors['username'], [NOT_FOUND]
                )
                self.assertContains(response, NOT_FOUND)
                tag = find_input(response.content.decode(), 'username')
                self.assertIsNotNone(tag)
                self.assertIn('value="%s"' % typed, tag)
                self.assertEqual(self.member_count(), before)
        self.assertFalse(self.ws.memberships.filter(user=self.dave).exists())

    def test_empty_username_rejected(self):
        """spec 02 AC-17: empty username → field error, nobody added."""
        self.client.force_login(self.alice)
        before = self.member_count()
        response = self.client.post(self.add_url(), {'username': ''})
        self.assertEqual(response.status_code, 200)
        self.assertIn('username', response.context['add_member_form'].errors)
        self.assertEqual(self.member_count(), before)

    def test_added_user_sees_workspace_as_member(self):
        """spec 02 AC-18: after being added, Carol can open the page and is a Member."""
        self.client.force_login(self.alice)
        self.client.post(self.add_url(), {'username': 'Carol'})
        self.client.force_login(self.carol)
        response = self.client.get(self.detail_url())
        self.assertEqual(response.status_code, 200)
        self.assertIn(('Carol', 'Member'), member_rows(response))
        self.assertIsNone(add_member_form_tag(response.content.decode(), self.ws))

    def test_html_username_escaped_in_success_message(self):
        """spec 02 AC-8: adding '<b>x</b>' → escaped in the message and the list."""
        # Deliberately bypasses the registration form's username rules: test data only.
        evil = User.objects.create_user(username='<b>x</b>', password=PASSWORD)
        self.client.force_login(self.alice)
        response = self.client.post(
            self.add_url(), {'username': '<b>x</b>'}, follow=True
        )
        self.assertTrue(self.ws.memberships.filter(user=evil).exists())
        self.assertContains(response, '&lt;b&gt;x&lt;/b&gt; was added to the workspace.')
        self.assertNotContains(response, '<b>x</b>')
        self.assertIn(('&lt;b&gt;x&lt;/b&gt;', 'Member'), member_rows(response))

    def test_member_cannot_add(self):
        """spec 02 AC-20: non-owner member POST → 403, Carol not added."""
        self.client.force_login(self.bob)
        before = self.member_count()
        response = self.client.post(self.add_url(), {'username': 'Carol'})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.member_count(), before)
        self.assertFalse(self.ws.memberships.filter(user=self.carol).exists())

    def test_non_member_gets_404_not_403(self):
        """spec 02 AC-21: non-member add_member POST → 404 (not 403), no change."""
        self.client.force_login(self.carol)
        before = self.member_count()
        response = self.client.post(self.add_url(), {'username': 'Carol'})
        self.assertEqual(response.status_code, 404)
        self.assertNotContains(response, 'Apollo Secret', status_code=404)
        self.assertEqual(self.member_count(), before)
        self.assertFalse(self.ws.memberships.filter(user=self.carol).exists())

    def test_missing_id_gives_404(self):
        """spec 02 AC-21: add_member POST to a missing ID → 404 for non-member and other owner."""
        url = reverse('workspaces:add_member', args=[self.missing_pk()])
        Workspace.objects.create_with_owner('Carol HQ', self.carol)
        before = Membership.objects.count()
        for user in (self.carol, self.alice):
            with self.subTest(user=user.username):
                self.client.force_login(user)
                response = self.client.post(url, {'username': 'Bob'})
                self.assertEqual(response.status_code, 404)
        self.assertEqual(Membership.objects.count(), before)

    def test_get_is_rejected(self):
        """spec 02 AC-25: GET add_member?username=Carol → 405, nobody added."""
        self.client.force_login(self.alice)
        before = self.member_count()
        response = self.client.get(self.add_url() + '?username=Carol')
        self.assertEqual(response.status_code, 405)
        self.assertEqual(self.member_count(), before)
        self.assertFalse(self.ws.memberships.filter(user=self.carol).exists())

    def test_race_already_member_gives_field_error(self):
        """spec 02 AC-26: membership created between form check and save → field error, not 500."""

        def clean_without_member_check(form):
            # Simulate a second request winning the race: the form check
            # passes even though Bob is (now) already a member.
            form.user = User.objects.get(username__iexact=form.cleaned_data['username'])
            return form.cleaned_data['username']

        self.client.force_login(self.alice)
        before = self.member_count()
        with mock.patch.object(
            AddMemberForm, 'clean_username', clean_without_member_check
        ):
            response = self.client.post(self.add_url(), {'username': 'Bob'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context['add_member_form'].errors['username'],
            ['Bob is already a member of this workspace.'],
        )
        self.assertEqual(self.member_count(), before)
        self.assertEqual(
            Membership.objects.filter(workspace=self.ws, user=self.bob).count(), 1
        )
        self.assertEqual(message_texts(response), [])


# --------------------------------------------------------------------------
# Anonymous visitors
# --------------------------------------------------------------------------
class AnonymousAccessTests(WorkspaceTestData):
    def login_redirect(self, path):
        return '%s?next=%s' % (reverse('accounts:login'), path)

    def test_anonymous_get_redirects_with_next(self):
        """spec 02 AC-22: anonymous GET of create/detail → login?next=<path>."""
        for url in (reverse('workspaces:create'), self.detail_url()):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertRedirects(
                    response, self.login_redirect(url), fetch_redirect_response=False
                )

    def test_login_with_next_lands_on_detail_for_member(self):
        """spec 02 AC-22: Alice logs in with next=detail → lands on the workspace (200)."""
        before = Workspace.objects.count()
        response = self.client.post(
            self.login_redirect(self.detail_url()),
            {'username': 'Alice', 'password': PASSWORD},
        )
        self.assertRedirects(response, self.detail_url())
        self.assertEqual(Workspace.objects.count(), before)

    def test_login_with_next_still_404_for_non_member(self):
        """spec 02 AC-22 / AC-21: Carol logs in with next=detail → still 404 there."""
        response = self.client.post(
            self.login_redirect(self.detail_url()),
            {'username': 'Carol', 'password': PASSWORD},
        )
        self.assertRedirects(
            response, self.detail_url(), target_status_code=404
        )

    def test_login_with_next_lands_on_create(self):
        """spec 02 AC-22: login with next=create lands on the create form, nothing created."""
        url = reverse('workspaces:create')
        before = Workspace.objects.count()
        response = self.client.post(
            self.login_redirect(url), {'username': 'Carol', 'password': PASSWORD}
        )
        self.assertRedirects(response, url)
        self.assertEqual(Workspace.objects.count(), before)

    def test_anonymous_create_post_not_replayed(self):
        """spec 02 AC-23: anonymous create POST → plain login, nothing created, login → dashboard."""
        ws_before = Workspace.objects.count()
        m_before = Membership.objects.count()
        response = self.client.post(reverse('workspaces:create'), {'name': 'Ghost'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], reverse('accounts:login'))
        self.assertEqual(Workspace.objects.count(), ws_before)

        response = self.client.post(
            reverse('accounts:login'), {'username': 'Carol', 'password': PASSWORD}
        )
        self.assertRedirects(response, reverse('core:dashboard'))
        self.assertEqual(Workspace.objects.count(), ws_before)
        self.assertEqual(Membership.objects.count(), m_before)
        self.assertFalse(Workspace.objects.filter(name='Ghost').exists())

    def test_anonymous_add_member_post_not_replayed(self):
        """spec 02 AC-23: anonymous add_member POST → plain login, no change, login → dashboard."""
        ws_before = Workspace.objects.count()
        m_before = Membership.objects.count()
        response = self.client.post(self.add_url(), {'username': 'Carol'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], reverse('accounts:login'))
        self.assertEqual(Membership.objects.count(), m_before)

        response = self.client.post(
            reverse('accounts:login'), {'username': 'Alice', 'password': PASSWORD}
        )
        self.assertRedirects(response, reverse('core:dashboard'))
        self.assertEqual(Workspace.objects.count(), ws_before)
        self.assertEqual(Membership.objects.count(), m_before)
        self.assertFalse(self.ws.memberships.filter(user=self.carol).exists())


# --------------------------------------------------------------------------
# CSRF
# --------------------------------------------------------------------------
class CsrfTests(WorkspaceTestData):
    def test_create_without_token_rejected(self):
        """spec 02 AC-24: create POST without CSRF token → 403, nothing created."""
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.carol)
        before = Workspace.objects.count()
        response = client.post(reverse('workspaces:create'), {'name': 'Forged'})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Workspace.objects.count(), before)

    def test_add_member_without_token_rejected(self):
        """spec 02 AC-24: add_member POST without CSRF token → 403, nobody added."""
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.alice)
        before = Membership.objects.count()
        response = client.post(self.add_url(), {'username': 'Carol'})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Membership.objects.count(), before)
        self.assertFalse(self.ws.memberships.filter(user=self.carol).exists())
