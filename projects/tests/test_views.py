"""View tests for spec 04 (projects): create and detail flows, the workspace
page's projects section, access rules, the duplicate race, CSRF and escaping.

Every AC reference here is to spec 04 unless it says "spec 05". Spec 04
AC-22 (existing behaviour unchanged) has no single test: it is met by the
full suite passing. Spec 05 AC-22 changed two pinned wordings, updated
below: the empty-state action is "New project" and the project page's back
link reads "Back to <workspace name>".
"""
import re
from unittest import mock

from django.contrib.messages import get_messages
from django.test import Client
from django.urls import reverse

from projects.forms import ProjectForm
from projects.models import DUPLICATE_NAME_MESSAGE, Project
from workspaces.models import Workspace

from .data import PASSWORD, ProjectTestData


def hrefs(response):
    return re.findall(r'href="([^"]*)"', response.content.decode())


def message_texts(response):
    return [str(m) for m in get_messages(response.wsgi_request)]


# --------------------------------------------------------------------------
# spec 04 AC-1 … AC-6: creating a project
# --------------------------------------------------------------------------
class CreateProjectPageTests(ProjectTestData):
    def test_owner_and_member_see_create_form(self):
        """spec 04 AC-1: Alice (owner) and Bob (member) both get the create
        form with name and description fields, naming Apollo, with Cancel
        back to Apollo's page."""
        url = self.create_url(self.apollo)
        for user in (self.alice, self.bob):
            with self.subTest(user=user.username):
                response = self.client_for(user).get(url)
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, 'projects/project_form.html')
                form = response.context['form']
                self.assertIsInstance(form, ProjectForm)
                self.assertFalse(form.is_bound)
                self.assertEqual(list(form.fields), ['name', 'description'])
                self.assertEqual(response.context['workspace'], self.apollo)
                self.assertContains(response, 'name="name"')
                self.assertContains(response, '<textarea')
                self.assertContains(response, 'name="description"')
                self.assertContains(response, 'Apollo')
                self.assertContains(response, 'New project')
                self.assertIn(self.workspace_url(self.apollo), hrefs(response))
                self.assertContains(response, 'Cancel')

    def test_workspace_page_links_to_create(self):
        """spec 04 AC-1 / AC-7: Apollo's page offers the create action to
        every member."""
        for user in (self.alice, self.bob):
            with self.subTest(user=user.username):
                response = self.client_for(user).get(self.workspace_url(self.apollo))
                self.assertIn(self.create_url(self.apollo), hrefs(response))


class CreateProjectSubmitTests(ProjectTestData):
    def post(self, user, data, workspace=None):
        return self.client_for(user).post(
            self.create_url(workspace or self.apollo), data
        )

    def test_member_creates_project_in_that_workspace_only(self):
        """spec 04 AC-2: Bob's valid submission creates exactly one project,
        in Apollo only, redirects to its page and shows a confirmation."""
        before_total = Project.objects.count()
        before_hermes = self.hermes.projects.count()
        client = self.client_for(self.bob)
        response = client.post(
            self.create_url(self.apollo),
            {'name': 'Launch', 'description': 'Go live.'},
        )
        self.assertEqual(Project.objects.count(), before_total + 1)
        project = Project.objects.get(name='Launch')
        self.assertEqual(project.workspace, self.apollo)
        self.assertEqual(project.description, 'Go live.')
        self.assertEqual(self.hermes.projects.count(), before_hermes)
        self.assertRedirects(
            response,
            self.detail_url(self.apollo, project),
            fetch_redirect_response=False,
        )

        page = client.get(response['Location'])
        self.assertContains(page, 'Project &quot;Launch&quot; was created.')

    def test_message_on_redirect_target(self):
        """spec 04 AC-2: following the redirect shows the success message
        containing the project name."""
        response = self.client_for(self.alice).post(
            self.create_url(self.apollo), {'name': 'Launch'}, follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/project_detail.html')
        self.assertEqual(message_texts(response), ['Project "Launch" was created.'])

    def test_create_without_description(self):
        """spec 04 AC-2: a name alone (no description key) creates the project."""
        response = self.post(self.alice, {'name': 'Launch'})
        project = Project.objects.get(name='Launch')
        self.assertEqual(project.workspace, self.apollo)
        self.assertEqual(project.description, '')
        self.assertRedirects(response, self.detail_url(self.apollo, project))

    def test_empty_or_blank_name_creates_nothing(self):
        """spec 04 AC-3: "" or "   " → form shown again with a name error,
        nothing created."""
        before = Project.objects.count()
        for name in ('', '   '):
            with self.subTest(name=repr(name)):
                response = self.post(self.bob, {'name': name, 'description': 'x'})
                self.assertEqual(response.status_code, 200)
                self.assertIn('name', response.context['form'].errors)
                self.assertEqual(Project.objects.count(), before)

    def test_name_trimmed_before_saving(self):
        """spec 04 AC-3: "  Launch  " is saved as "Launch"."""
        self.post(self.bob, {'name': '  Launch  '})
        self.assertTrue(
            Project.objects.filter(workspace=self.apollo, name='Launch').exists()
        )
        self.assertFalse(Project.objects.filter(name__startswith=' ').exists())

    def test_too_long_name_rejected_and_kept(self):
        """spec 04 AC-4: a 101-character name → name error stating the
        limit, nothing created, typed value shown again."""
        before = Project.objects.count()
        long_name = 'n' * 101
        response = self.post(self.bob, {'name': long_name, 'description': 'kept'})
        self.assertEqual(response.status_code, 200)
        errors = response.context['form'].errors['name']
        self.assertEqual(len(errors), 1)
        self.assertIn('100', errors[0])
        self.assertContains(response, 'value="%s"' % long_name)
        self.assertContains(response, 'kept</textarea>')
        self.assertEqual(Project.objects.count(), before)

    def test_too_long_description_rejected_and_kept(self):
        """spec 04 AC-4: a 2001-character description → description error
        stating the limit, nothing created, typed values shown again."""
        before = Project.objects.count()
        long_text = 'd' * 2001
        response = self.post(self.bob, {'name': 'Launch', 'description': long_text})
        self.assertEqual(response.status_code, 200)
        errors = response.context['form'].errors['description']
        self.assertEqual(len(errors), 1)
        self.assertIn('2000', errors[0].replace(',', ''))
        self.assertContains(response, long_text + '</textarea>')
        self.assertContains(response, 'value="Launch"')
        self.assertEqual(Project.objects.count(), before)

    def test_exact_limits_accepted(self):
        """spec 04 AC-4: exactly 100 and 2000 characters are accepted."""
        response = self.post(self.bob, {'name': 'n' * 100, 'description': 'd' * 2000})
        project = Project.objects.get(name='n' * 100)
        self.assertEqual(len(project.description), 2000)
        self.assertRedirects(response, self.detail_url(self.apollo, project))

    def test_duplicate_name_same_workspace_rejected(self):
        """spec 04 AC-5: "roadmap" and "ROADMAP" in Apollo (which has
        "Roadmap") → the duplicate error on name, nothing created."""
        before = Project.objects.count()
        for name in ('roadmap', 'ROADMAP'):
            with self.subTest(name=name):
                response = self.post(self.bob, {'name': name})
                self.assertEqual(response.status_code, 200)
                form = response.context['form']
                self.assertEqual(form.errors['name'], [DUPLICATE_NAME_MESSAGE])
                self.assertEqual(form.non_field_errors(), [])
                self.assertContains(response, DUPLICATE_NAME_MESSAGE)
                self.assertEqual(Project.objects.count(), before)

    def test_same_name_other_workspace_allowed(self):
        """spec 04 AC-5 (OQ-3): Carol creates "Roadmap" in Hermes."""
        response = self.post(self.carol, {'name': 'Roadmap'}, workspace=self.hermes)
        project = Project.objects.get(workspace=self.hermes, name='Roadmap')
        self.assertRedirects(response, self.detail_url(self.hermes, project))
        self.assertEqual(self.apollo.projects.count(), 1)

    def test_blank_description_saved_empty(self):
        """spec 04 AC-6: an all-space description saves as ''."""
        self.post(self.bob, {'name': 'Launch', 'description': '    '})
        project = Project.objects.get(name='Launch')
        self.assertEqual(project.description, '')


# --------------------------------------------------------------------------
# spec 04 AC-7 … AC-9: the workspace page's projects section
# --------------------------------------------------------------------------
class WorkspaceProjectsSectionTests(ProjectTestData):
    def section_html(self, response):
        html = response.content.decode()
        start = html.index('aria-labelledby="projects-heading"')
        end = html.index('</section>', start)
        return html[start:end]

    def test_projects_listed_alphabetically_with_links_and_count(self):
        """spec 04 AC-7: as Alice and as Bob, the projects section shows the
        count, every project linking to its page in case-insensitive
        alphabetical order, and the create action."""
        self.roadmap.delete()
        projects = {
            name: Project.objects.create(workspace=self.apollo, name=name)
            for name in ('gamma', 'Beta', 'alpha')
        }
        expected = [
            self.detail_url(self.apollo, projects[name])
            for name in ('alpha', 'Beta', 'gamma')
        ]
        for user in (self.alice, self.bob):
            with self.subTest(user=user.username):
                response = self.client_for(user).get(self.workspace_url(self.apollo))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    [p.name for p in response.context['projects']],
                    ['alpha', 'Beta', 'gamma'],
                )
                section = self.section_html(response)
                self.assertIn('id="projects-heading"', section)
                self.assertIn('>Projects</h2>', section)
                self.assertRegex(section, r'class="badge[^"]*">3</span>')
                detail_links = [
                    h for h in re.findall(r'href="([^"]*)"', section)
                    if '/projects/' in h and not h.endswith('/new/')
                ]
                self.assertEqual(detail_links, expected)
                self.assertIn(self.create_url(self.apollo), section)

    def test_members_and_add_member_sections_unchanged(self):
        """spec 04 AC-7: the members section remains for everyone, and the
        add-member section remains for the owner only."""
        owner = self.client_for(self.alice).get(self.workspace_url(self.apollo))
        member = self.client_for(self.bob).get(self.workspace_url(self.apollo))
        for response in (owner, member):
            self.assertContains(response, 'id="members-heading"')
            self.assertContains(response, 'Alice')
            self.assertContains(response, 'Bob')
        self.assertContains(owner, 'id="add-member-heading"')
        self.assertNotContains(member, 'id="add-member-heading"')
        self.assertIn('add_member_form', owner.context)

    def test_projects_still_shown_after_add_member_error(self):
        """spec 04 AC-7: the page redrawn after an add-member error still
        shows the projects section."""
        response = self.client_for(self.alice).post(
            reverse('workspaces:add_member', args=[self.apollo.pk]),
            {'username': 'nobody-here'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="projects-heading"')
        self.assertContains(response, self.detail_url(self.apollo, self.roadmap))

    def test_empty_state_has_own_create_action(self):
        """spec 04 AC-8: with no projects the section shows "No projects
        yet." and a create action inside the empty state, and no rows.
        spec 05 AC-22: that action is labelled "New project" (was "Create a
        project")."""
        self.apollo.projects.all().delete()
        for user in (self.alice, self.bob):
            with self.subTest(user=user.username):
                response = self.client_for(user).get(self.workspace_url(self.apollo))
                section = self.section_html(response)
                self.assertIn('No projects yet.', section)
                self.assertIn(self.create_url(self.apollo), section)
                self.assertIn('New project', section)
                self.assertNotIn('Create a project', section)
                self.assertRegex(section, r'class="badge[^"]*">0</span>')
                self.assertNotIn('<li', section)
                rows = [h for h in re.findall(r'href="([^"]*)"', section)
                        if '/projects/' in h and not h.endswith('/new/')]
                self.assertEqual(rows, [])

    def test_never_lists_other_workspaces_projects(self):
        """spec 04 AC-9: Hermes' projects never appear on Apollo's page, and
        Apollo's never appear on Hermes' page."""
        apollo_page = self.client_for(self.alice).get(self.workspace_url(self.apollo))
        self.assertNotContains(apollo_page, 'Hermes Plan')
        self.assertNotIn(
            self.detail_url(self.hermes, self.hermes_plan), hrefs(apollo_page)
        )
        self.assertEqual(list(apollo_page.context['projects']), [self.roadmap])

        hermes_page = self.client_for(self.carol).get(self.workspace_url(self.hermes))
        self.assertNotContains(hermes_page, 'Roadmap')
        self.assertEqual(list(hermes_page.context['projects']), [self.hermes_plan])


# --------------------------------------------------------------------------
# spec 04 AC-10, AC-11: the project page and escaping
# --------------------------------------------------------------------------
class ProjectPageTests(ProjectTestData):
    def test_page_shows_name_description_and_workspace(self):
        """spec 04 AC-10: name as h1, description line breaks kept, and a
        back link naming Apollo to Apollo's page."""
        project = Project.objects.create(
            workspace=self.apollo, name='Launch', description='line1\nline2'
        )
        for user in (self.alice, self.bob):
            with self.subTest(user=user.username):
                response = self.client_for(user).get(
                    self.detail_url(self.apollo, project)
                )
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, 'projects/project_detail.html')
                html = response.content.decode()
                self.assertRegex(html, r'<h1[^>]*>Launch</h1>')
                self.assertIn('line1<br>line2', html)
                self.assertNotContains(response, 'No description')
                back_link = re.compile(
                    r'<a href="%s"[^>]*>.*?Apollo.*?</a>'
                    % re.escape(self.workspace_url(self.apollo)),
                    re.S,
                )
                self.assertRegex(html, back_link)

    def test_back_link_reads_back_to_workspace(self):
        """spec 05 AC-22 (step 04 Q-40): the project page's back link text is
        "Back to Apollo" and it still links to Apollo's workspaces:detail."""
        anchors = re.findall(
            r'<a href="%s"[^>]*>(.*?)</a>'
            % re.escape(self.workspace_url(self.apollo)),
            self.client_for(self.bob)
            .get(self.detail_url(self.apollo, self.roadmap))
            .content.decode(),
            re.S,
        )
        self.assertEqual(len(anchors), 1)
        text = ' '.join(re.sub(r'<[^>]+>', ' ', anchors[0]).split())
        self.assertEqual(text, 'Back to Apollo')

    def test_no_description_note(self):
        """spec 04 AC-10: an empty description shows "No description"."""
        project = Project.objects.create(workspace=self.apollo, name='Launch')
        response = self.client_for(self.bob).get(self.detail_url(self.apollo, project))
        self.assertContains(response, 'No description')

    def test_head_allowed(self):
        """spec 04 AC-10: the project page answers HEAD for a member."""
        response = self.client_for(self.bob).head(
            self.detail_url(self.apollo, self.roadmap)
        )
        self.assertEqual(response.status_code, 200)


class EscapingTests(ProjectTestData):
    NAME = '<script>alert(1)</script>'
    DESCRIPTION = '<b>x</b>\n<i>y</i>'
    ESCAPED_NAME = '&lt;script&gt;alert(1)&lt;/script&gt;'
    ESCAPED_DESCRIPTION = '&lt;b&gt;x&lt;/b&gt;<br>&lt;i&gt;y&lt;/i&gt;'

    def assert_no_raw_markup(self, html):
        self.assertNotIn('<script>alert(1)', html)
        self.assertNotIn('<b>x</b>', html)
        self.assertNotIn('<i>y</i>', html)

    def test_escaped_in_message_page_and_title(self):
        """spec 04 AC-11: a script-like name and HTML-like multi-line
        description are escaped in the creation message, on the project
        page (including <title>) with <br> between escaped lines."""
        client = self.client_for(self.bob)
        response = client.post(
            self.create_url(self.apollo),
            {'name': self.NAME, 'description': self.DESCRIPTION},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        project = Project.objects.get(workspace=self.apollo, name=self.NAME)
        self.assertEqual(project.description, self.DESCRIPTION)
        html = response.content.decode()
        self.assert_no_raw_markup(html)
        # Message.
        self.assertIn('Project &quot;%s&quot; was created.' % self.ESCAPED_NAME, html)
        # Title.
        title = re.search(r'<title>(.*?)</title>', html, re.S).group(1)
        self.assertIn(self.ESCAPED_NAME, title)
        self.assertNotIn('<', title)
        # Heading and description.
        self.assertRegex(html, r'<h1[^>]*>%s</h1>' % re.escape(self.ESCAPED_NAME))
        self.assertIn(self.ESCAPED_DESCRIPTION, html)

    def test_escaped_on_workspace_page(self):
        """spec 04 AC-11: the name is escaped in the workspace page's list."""
        Project.objects.create(
            workspace=self.apollo, name=self.NAME, description=self.DESCRIPTION
        )
        response = self.client_for(self.alice).get(self.workspace_url(self.apollo))
        html = response.content.decode()
        self.assert_no_raw_markup(html)
        self.assertIn(self.ESCAPED_NAME, html)

    def test_workspace_name_escaped_on_project_pages(self):
        """spec 04 AC-11: a markup-like workspace name is shown as text on the
        create page and the project page (heading line, back link, title)."""
        workspace = Workspace.objects.create_with_owner('<em>WS</em>', self.dave)
        project = Project.objects.create(workspace=workspace, name='Plain')
        client = self.client_for(self.dave)
        for url in (self.create_url(workspace), self.detail_url(workspace, project)):
            with self.subTest(url=url):
                html = client.get(url).content.decode()
                self.assertNotIn('<em>WS</em>', html)
                self.assertIn('&lt;em&gt;WS&lt;/em&gt;', html)


# --------------------------------------------------------------------------
# spec 04 AC-12 … AC-14: not found for non-members, wrong workspace, missing IDs
# --------------------------------------------------------------------------
class SecretProjectData(ProjectTestData):
    SECRET_NAME = 'Secret Moonshot'
    SECRET_DESCRIPTION = 'Classified orbital plan'

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.secret = Project.objects.create(
            workspace=cls.apollo,
            name=cls.SECRET_NAME,
            description=cls.SECRET_DESCRIPTION,
        )

    def assert_hidden_404(self, response):
        self.assertEqual(response.status_code, 404)
        self.assertNotContains(response, self.SECRET_NAME, status_code=404)
        self.assertNotContains(response, self.SECRET_DESCRIPTION, status_code=404)
        self.assertNotContains(response, 'Apollo', status_code=404)


class NonMemberAccessTests(SecretProjectData):
    def test_non_member_get_create_is_404(self):
        """spec 04 AC-12: Dave and Carol GET Apollo's create page → 404, not 403."""
        for user in (self.dave, self.carol):
            with self.subTest(user=user.username):
                response = self.client_for(user).get(self.create_url(self.apollo))
                self.assert_hidden_404(response)

    def test_non_member_get_detail_is_404(self):
        """spec 04 AC-12: Dave and Carol GET an Apollo project page → 404
        that reveals neither name nor description."""
        for user in (self.dave, self.carol):
            with self.subTest(user=user.username):
                response = self.client_for(user).get(
                    self.detail_url(self.apollo, self.secret)
                )
                self.assert_hidden_404(response)

    def test_non_member_head_detail_is_404(self):
        """spec 04 AC-12: a HEAD by a non-member is a 404 as well."""
        response = self.client_for(self.dave).head(
            self.detail_url(self.apollo, self.secret)
        )
        self.assertEqual(response.status_code, 404)

    def test_non_member_post_create_is_404_and_creates_nothing(self):
        """spec 04 AC-12: Dave and Carol POST to Apollo's create URL → 404,
        nothing created anywhere."""
        before = Project.objects.count()
        for user in (self.dave, self.carol):
            with self.subTest(user=user.username):
                response = self.client_for(user).post(
                    self.create_url(self.apollo),
                    {'name': 'Intruder', 'description': 'x'},
                )
                self.assert_hidden_404(response)
                self.assertEqual(Project.objects.count(), before)
                self.assertFalse(Project.objects.filter(name='Intruder').exists())

    def test_non_member_404_matches_missing_workspace_404(self):
        """spec 04 AC-12 / AC-14: a non-member's 404 is the same response as
        for a workspace that doesn't exist."""
        client = self.client_for(self.dave)
        missing = self.missing_pk(Workspace)
        real = client.get(self.detail_url(self.apollo, self.secret))
        fake = client.get(self.detail_url(missing, self.secret))
        self.assertEqual(real.status_code, fake.status_code)
        self.assertEqual(real.content, fake.content)
        real = client.get(self.create_url(self.apollo))
        fake = client.get(self.create_url(missing))
        self.assertEqual(real.status_code, 404)
        self.assertEqual(real.content, fake.content)


class WrongWorkspaceTests(SecretProjectData):
    def test_project_under_other_workspace_is_404_for_that_workspaces_member(self):
        """spec 04 AC-13: Carol (member of Hermes) asks for an Apollo project
        under Hermes' ID → 404."""
        response = self.client_for(self.carol).get(
            self.detail_url(self.hermes, self.secret)
        )
        self.assert_hidden_404(response)

    def test_project_under_other_workspace_is_404_for_its_own_member(self):
        """spec 04 AC-13: Bob (member of Apollo only) asks for an Apollo
        project under Hermes' ID → 404."""
        response = self.client_for(self.bob).get(
            self.detail_url(self.hermes, self.secret)
        )
        self.assert_hidden_404(response)

    def test_project_under_other_workspace_is_404_for_member_of_both(self):
        """spec 04 AC-13: even a member of both workspaces gets 404 when the
        project is requested under the wrong workspace, and 200 under its own."""
        self.hermes.add_member(self.bob)
        client = self.client_for(self.bob)
        response = client.get(self.detail_url(self.hermes, self.secret))
        self.assert_hidden_404(response)
        response = client.get(self.detail_url(self.apollo, self.hermes_plan))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            client.get(self.detail_url(self.apollo, self.secret)).status_code, 200
        )
        self.assertEqual(
            client.get(self.detail_url(self.hermes, self.hermes_plan)).status_code,
            200,
        )


class MissingIdTests(SecretProjectData):
    def test_missing_ids_are_404(self):
        """spec 04 AC-14: a missing workspace (create GET/POST, detail) or a
        missing project under Apollo → 404, same response as a non-member."""
        missing_ws = self.missing_pk(Workspace)
        missing_project = self.missing_pk(Project)
        client = self.client_for(self.bob)
        non_member = self.client_for(self.dave).get(
            self.detail_url(self.apollo, self.secret)
        )
        before = Project.objects.count()
        responses = {
            'create GET': client.get(self.create_url(missing_ws)),
            'create POST': client.post(self.create_url(missing_ws), {'name': 'X'}),
            'detail missing ws': client.get(self.detail_url(missing_ws, self.secret)),
            'detail missing project': client.get(
                self.detail_url(self.apollo, missing_project)
            ),
        }
        for label, response in responses.items():
            with self.subTest(case=label):
                self.assertEqual(response.status_code, 404)
                self.assertEqual(response.content, non_member.content)
        self.assertEqual(Project.objects.count(), before)


# --------------------------------------------------------------------------
# spec 04 AC-15, AC-16: anonymous visitors
# --------------------------------------------------------------------------
class AnonymousAccessTests(ProjectTestData):
    def login_redirect(self, path):
        return '%s?next=%s' % (reverse('accounts:login'), path)

    def test_anonymous_get_redirects_with_next(self):
        """spec 04 AC-15: anonymous GET of create and detail → login?next=<path>."""
        for url in (
            self.create_url(self.apollo),
            self.detail_url(self.apollo, self.roadmap),
        ):
            with self.subTest(url=url):
                response = Client().get(url)
                self.assertRedirects(
                    response, self.login_redirect(url), fetch_redirect_response=False
                )

    def test_anonymous_get_missing_ids_also_redirect(self):
        """spec 04 AC-15: login is checked before the workspace lookup, so an
        anonymous visitor learns nothing from IDs."""
        url = self.create_url(self.missing_pk(Workspace))
        response = Client().get(url)
        self.assertRedirects(
            response, self.login_redirect(url), fetch_redirect_response=False
        )

    def test_login_with_next_lands_on_page_for_member(self):
        """spec 04 AC-15: Bob logs in with next=<page> → lands there (200)."""
        for url in (
            self.create_url(self.apollo),
            self.detail_url(self.apollo, self.roadmap),
        ):
            with self.subTest(url=url):
                client = Client()
                response = client.post(
                    self.login_redirect(url),
                    {'username': 'Bob', 'password': PASSWORD},
                )
                self.assertRedirects(response, url)

    def test_login_with_next_still_404_for_non_member(self):
        """spec 04 AC-15: Dave logs in with next=<page> → still 404 there."""
        for url in (
            self.create_url(self.apollo),
            self.detail_url(self.apollo, self.roadmap),
        ):
            with self.subTest(url=url):
                client = Client()
                response = client.post(
                    self.login_redirect(url),
                    {'username': 'Dave', 'password': PASSWORD},
                )
                self.assertRedirects(response, url, target_status_code=404)

    def test_anonymous_post_not_replayed(self):
        """spec 04 AC-16: anonymous POST → exactly the login URL (no next),
        nothing created; logging in afterwards lands on the dashboard and
        still creates nothing."""
        before = Project.objects.count()
        client = Client()
        response = client.post(self.create_url(self.apollo), {'name': 'Ghost'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], reverse('accounts:login'))
        self.assertEqual(Project.objects.count(), before)

        response = client.post(
            reverse('accounts:login'), {'username': 'Bob', 'password': PASSWORD}
        )
        self.assertRedirects(response, reverse('core:dashboard'))
        self.assertEqual(Project.objects.count(), before)
        self.assertFalse(Project.objects.filter(name='Ghost').exists())

    def test_anonymous_post_to_detail_goes_to_login(self):
        """spec 04 AC-16: an anonymous POST to a project page also goes to
        plain login and changes nothing."""
        before = Project.objects.count()
        response = Client().post(self.detail_url(self.apollo, self.roadmap), {})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], reverse('accounts:login'))
        self.assertEqual(Project.objects.count(), before)


# --------------------------------------------------------------------------
# spec 04 AC-17, AC-18: CSRF and GET-never-creates
# --------------------------------------------------------------------------
class CsrfAndMethodTests(ProjectTestData):
    def test_post_without_csrf_token_rejected(self):
        """spec 04 AC-17: a create POST without the CSRF token → 403,
        nothing created."""
        before = Project.objects.count()
        client = self.client_for(self.bob, enforce_csrf_checks=True)
        response = client.post(self.create_url(self.apollo), {'name': 'Forged'})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Project.objects.count(), before)
        self.assertFalse(Project.objects.filter(name='Forged').exists())

    def test_post_with_csrf_token_accepted(self):
        """spec 04 AC-17 (control): the same client with the page's token
        succeeds, so the 403 above is the CSRF check."""
        client = self.client_for(self.bob, enforce_csrf_checks=True)
        page = client.get(self.create_url(self.apollo))
        self.assertContains(page, 'csrfmiddlewaretoken')
        token = page.context['csrf_token']
        response = client.post(
            self.create_url(self.apollo),
            {'name': 'Genuine', 'csrfmiddlewaretoken': str(token)},
        )
        project = Project.objects.get(name='Genuine')
        self.assertRedirects(response, self.detail_url(self.apollo, project))

    def test_get_with_query_params_creates_nothing(self):
        """spec 04 AC-18: GET create?name=X&description=Y shows an unbound
        form and creates nothing."""
        before = Project.objects.count()
        response = self.client_for(self.bob).get(
            self.create_url(self.apollo), {'name': 'Sneaky', 'description': 'Y'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['form'].is_bound)
        self.assertEqual(Project.objects.count(), before)
        self.assertFalse(Project.objects.filter(name='Sneaky').exists())

    def test_post_to_detail_not_allowed(self):
        """spec 04 AC-18: POST (and PUT/DELETE) to a project page → 405 and
        nothing changes."""
        before = list(Project.objects.values_list('pk', 'name', 'description'))
        client = self.client_for(self.bob)
        url = self.detail_url(self.apollo, self.roadmap)
        self.assertEqual(client.post(url, {'name': 'Changed'}).status_code, 405)
        self.assertEqual(client.put(url).status_code, 405)
        self.assertEqual(client.delete(url).status_code, 405)
        self.assertEqual(
            list(Project.objects.values_list('pk', 'name', 'description')), before
        )


# --------------------------------------------------------------------------
# spec 04 AC-19, AC-20: data integrity
# --------------------------------------------------------------------------
class IntegrityTests(ProjectTestData):
    def test_posted_workspace_field_is_ignored(self):
        """spec 04 AC-19: an extra workspace=<Hermes pk> in a POST to Apollo's
        create URL still creates the project in Apollo."""
        hermes_before = self.hermes.projects.count()
        response = self.client_for(self.bob).post(
            self.create_url(self.apollo),
            {'name': 'Moved', 'workspace': self.hermes.pk},
        )
        project = Project.objects.get(name='Moved')
        self.assertEqual(project.workspace, self.apollo)
        self.assertEqual(self.hermes.projects.count(), hermes_before)
        self.assertRedirects(response, self.detail_url(self.apollo, project))

    def test_duplicate_race_shows_field_error_not_500(self):
        """spec 04 AC-20 (plan D-3): with "Roadmap" already in Apollo and the
        form's duplicate check bypassed (simulating a race), POST "roadmap"
        → 200 with exactly the duplicate error on name, no non-field error,
        no extra project, no success message, the typed value kept, and the
        database still usable afterwards."""
        def no_duplicate_check(form):
            return form.cleaned_data['name']

        with mock.patch.object(ProjectForm, 'clean_name', no_duplicate_check):
            response = self.client_for(self.bob).post(
                self.create_url(self.apollo),
                {'name': 'roadmap', 'description': 'Second try'},
            )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/project_form.html')
        form = response.context['form']
        self.assertEqual(form.errors['name'], [DUPLICATE_NAME_MESSAGE])
        self.assertEqual(form.non_field_errors(), [])
        self.assertEqual(list(form.errors), ['name'])
        self.assertEqual(message_texts(response), [])
        self.assertContains(response, 'value="roadmap"')
        self.assertContains(response, 'Second try</textarea>')
        self.assertContains(response, DUPLICATE_NAME_MESSAGE)

        # These queries would raise TransactionManagementError if the view
        # had kept using a broken transaction.
        self.assertEqual(self.apollo.projects.count(), 1)
        self.assertEqual(
            list(self.apollo.projects.values_list('name', flat=True)), ['Roadmap']
        )
        extra = Project.objects.create(workspace=self.apollo, name='After race')
        self.assertTrue(Project.objects.filter(pk=extra.pk).exists())
        self.assertEqual(Workspace.objects.get(pk=self.apollo.pk).name, 'Apollo')

    def test_race_then_normal_create_still_works(self):
        """spec 04 AC-20: after a race-path rejection the same member can
        create a project normally."""
        with mock.patch.object(
            ProjectForm, 'clean_name', lambda form: form.cleaned_data['name']
        ):
            self.client_for(self.bob).post(
                self.create_url(self.apollo), {'name': 'ROADMAP'}
            )
        response = self.client_for(self.bob).post(
            self.create_url(self.apollo), {'name': 'Next'}
        )
        project = Project.objects.get(name='Next')
        self.assertRedirects(response, self.detail_url(self.apollo, project))
        self.assertEqual(self.apollo.projects.count(), 2)


# --------------------------------------------------------------------------
# spec 04 AC-18 (step 05 review S-5): the create URL accepts only GET/HEAD/POST
# --------------------------------------------------------------------------
class CreateMethodRestrictionTests(SecretProjectData):
    """spec 04 AC-18 (step 05 review S-5): PUT, PATCH and DELETE are not a
    second write path into a workspace's project list."""

    BODY = 'name=Smuggled&description=via+other+method'
    CONTENT_TYPE = 'application/x-www-form-urlencoded'

    def assert_nothing_created(self, before):
        self.assertEqual(Project.objects.count(), before)
        self.assertFalse(Project.objects.filter(name='Smuggled').exists())

    def test_member_put_patch_delete_create_is_405_and_creates_nothing(self):
        """spec 04 AC-18 (step 05 review S-5): Bob (member) sends PUT, PATCH
        and DELETE to projects:create → 405, no project created."""
        client = self.client_for(self.bob)
        url = self.create_url(self.apollo)
        before = Project.objects.count()
        for method in ('put', 'patch', 'delete'):
            with self.subTest(method=method):
                response = getattr(client, method)(
                    url, self.BODY, content_type=self.CONTENT_TYPE
                )
                self.assertEqual(response.status_code, 405)
                self.assert_nothing_created(before)

    def test_member_get_and_post_create_still_work(self):
        """spec 04 AC-18 (step 05 review S-5, control): GET still shows the
        form (200) and POST still creates the project, so the 405s above come
        from the method restriction only."""
        client = self.client_for(self.bob)
        url = self.create_url(self.apollo)
        self.assertEqual(client.get(url).status_code, 200)
        response = client.post(url, {'name': 'Allowed', 'description': 'ok'})
        project = Project.objects.get(name='Allowed')
        self.assertEqual(project.workspace, self.apollo)
        self.assertRedirects(response, self.detail_url(self.apollo, project))

    def test_non_member_put_create_is_404_not_405(self):
        """spec 04 AC-12 / AC-18 (step 05 review S-5): Dave and Carol PUT to
        Apollo's create URL → 404, not 405: the workspace is resolved before
        the method is checked, so a 405 never reveals that it exists."""
        url = self.create_url(self.apollo)
        before = Project.objects.count()
        for user in (self.dave, self.carol):
            with self.subTest(user=user.username):
                response = self.client_for(user).put(
                    url, self.BODY, content_type=self.CONTENT_TYPE
                )
                self.assert_hidden_404(response)
                self.assert_nothing_created(before)
