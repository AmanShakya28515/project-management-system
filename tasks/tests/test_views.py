"""View tests for spec 05 (tasks): create and detail flows, the project
page's tasks section, access rules (non-member, wrong parent, missing IDs,
anonymous), CSRF, GET-never-creates, posted-ID tampering and escaping.

Test data (data.py): Alice owns Apollo, Bob is a member; Carol owns Hermes;
Dave belongs to nothing. Apollo has Roadmap and Launch; Hermes has Hermes
Plan. Roadmap starts with the task "Draft outline".

Spec 05 AC-21 (all step 01-04 behaviour unchanged) is met by the full suite
passing; StepFourBehaviourKeptTests below adds one direct check that the
step 04 project page still renders as before.
"""
import re

from django.contrib.messages import get_messages
from django.test import Client
from django.urls import reverse

from core.tests.helpers import by_id, main_of, parse
from projects.models import Project
from tasks.forms import TaskForm
from tasks.models import Task
from workspaces.models import Workspace

from .data import PASSWORD, TaskTestData, missing_pk

# Text that would reveal a creation date or time (spec 05 OQ-4).
DATE_OR_TIME = re.compile(
    r'\b\d{1,2}:\d{2}\b'
    r'|\b\d{4}-\d{1,2}-\d{1,2}\b'
    r'|\b\d{1,2}/\d{1,2}/\d{2,4}\b'
    r'|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.? \d{1,2}\b'
    r'|\b\d{1,2} (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)'
    r'|\b(?:ago|today|yesterday|a\.m\.|p\.m\.)\b',
    re.I,
)


def hrefs(response):
    return re.findall(r'href="([^"]*)"', response.content.decode())


def message_texts(response):
    return [str(m) for m in get_messages(response.wsgi_request)]


def section_of(root, heading_id):
    heading = by_id(root, heading_id)
    assert heading is not None, 'no #%s' % heading_id
    for node in heading.ancestors():
        if node.tag == 'section':
            return node
    raise AssertionError('#%s is not inside a <section>' % heading_id)


# --------------------------------------------------------------------------
# spec 05 AC-1 … AC-6: creating a task
# --------------------------------------------------------------------------
class CreateTaskPageTests(TaskTestData):
    def test_owner_and_member_see_create_form(self):
        """spec 05 AC-1: Alice (owner) and Bob (member) both get the create
        form with title and description fields; the page names Roadmap and
        Apollo, and Cancel goes back to Roadmap's page."""
        url = self.create_url(self.apollo, self.roadmap)
        for user in (self.alice, self.bob):
            with self.subTest(user=user.username):
                response = self.client_for(user).get(url)
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, 'tasks/task_form.html')
                form = response.context['form']
                self.assertIsInstance(form, TaskForm)
                self.assertFalse(form.is_bound)
                self.assertEqual(list(form.fields), ['title', 'description'])
                self.assertEqual(response.context['workspace'], self.apollo)
                self.assertEqual(response.context['project'], self.roadmap)
                self.assertContains(response, 'name="title"')
                self.assertContains(response, '<textarea')
                self.assertContains(response, 'name="description"')
                main = main_of(parse(response))
                self.assertIn('Roadmap', main.norm_text())
                self.assertIn('Apollo', main.norm_text())
                cancel = [a for a in main.find_all('a') if a.norm_text() == 'Cancel']
                self.assertEqual(len(cancel), 1)
                self.assertEqual(
                    cancel[0].attrs.get('href'),
                    self.project_url(self.apollo, self.roadmap),
                )

    def test_create_page_says_which_project_and_workspace(self):
        """spec 05 AC-1: the line under the heading names the project and
        the workspace the task will be created in."""
        root = parse(self.client_for(self.bob).get(
            self.create_url(self.apollo, self.launch)
        ))
        main = main_of(root)
        h1 = main.find('h1')
        self.assertEqual(h1.norm_text(), 'New task')
        context_lines = [
            p for p in main.find_all('p')
            if 'Launch' in p.norm_text() and 'Apollo' in p.norm_text()
        ]
        self.assertEqual(len(context_lines), 1)
        self.assertNotIn('Roadmap', main.norm_text())

    def test_project_page_links_to_create(self):
        """spec 05 AC-1: a project page offers the create-task action to
        every member, with and without existing tasks."""
        for project in (self.roadmap, self.launch):
            for user in (self.alice, self.bob):
                with self.subTest(project=project.name, user=user.username):
                    response = self.client_for(user).get(
                        self.project_url(self.apollo, project)
                    )
                    self.assertIn(self.create_url(self.apollo, project), hrefs(response))


class CreateTaskSubmitTests(TaskTestData):
    def post(self, user, data, project=None, **kwargs):
        project = project or self.roadmap
        return self.client_for(user).post(
            self.create_url(project.workspace, project), data, **kwargs
        )

    def test_member_creates_task_in_that_project_only(self):
        """spec 05 AC-2: Bob's valid submission creates exactly one task, in
        Roadmap only, redirects to its page and shows a confirmation."""
        before = Task.objects.count()
        client = self.client_for(self.bob)
        response = client.post(
            self.create_url(self.apollo, self.roadmap),
            {'title': 'Write brief', 'description': 'Two pages.'},
        )
        self.assertEqual(Task.objects.count(), before + 1)
        task = Task.objects.get(title='Write brief')
        self.assertEqual(task.project, self.roadmap)
        self.assertEqual(task.description, 'Two pages.')
        self.assertEqual(self.launch.tasks.count(), 0)
        self.assertEqual(self.hermes_plan.tasks.count(), 0)
        self.assertRedirects(
            response,
            self.detail_url(self.apollo, self.roadmap, task),
            fetch_redirect_response=False,
        )
        page = client.get(response['Location'])
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, 'Task &quot;Write brief&quot; was created.')

    def test_message_on_redirect_target(self):
        """spec 05 AC-2: following the redirect lands on the task page with
        the success message containing the title."""
        response = self.post(self.alice, {'title': 'Write brief'}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tasks/task_detail.html')
        self.assertEqual(message_texts(response), ['Task "Write brief" was created.'])

    def test_create_without_description(self):
        """spec 05 AC-2: a title alone (no description key) creates the task."""
        response = self.post(self.alice, {'title': 'Write brief'})
        task = Task.objects.get(title='Write brief')
        self.assertEqual(task.project, self.roadmap)
        self.assertEqual(task.description, '')
        self.assertRedirects(response, self.detail_url(self.apollo, self.roadmap, task))

    def test_empty_or_blank_title_creates_nothing(self):
        """spec 05 AC-3: "" or "   " → form shown again with a title error,
        nothing created."""
        before = Task.objects.count()
        for title in ('', '   '):
            with self.subTest(title=repr(title)):
                response = self.post(self.bob, {'title': title, 'description': 'x'})
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, 'tasks/task_form.html')
                self.assertIn('title', response.context['form'].errors)
                self.assertEqual(Task.objects.count(), before)
                self.assertEqual(message_texts(response), [])

    def test_title_trimmed_before_saving(self):
        """spec 05 AC-3: "  Write brief  " is saved as "Write brief"."""
        self.post(self.bob, {'title': '  Write brief  '})
        self.assertTrue(
            Task.objects.filter(project=self.roadmap, title='Write brief').exists()
        )
        self.assertFalse(Task.objects.filter(title__startswith=' ').exists())
        self.assertFalse(Task.objects.filter(title__endswith=' ').exists())

    def test_too_long_title_rejected_and_kept(self):
        """spec 05 AC-4: a 201-character title → title error stating the
        limit, nothing created, typed values shown again."""
        before = Task.objects.count()
        long_title = 't' * 201
        response = self.post(self.bob, {'title': long_title, 'description': 'kept'})
        self.assertEqual(response.status_code, 200)
        errors = response.context['form'].errors['title']
        self.assertEqual(len(errors), 1)
        self.assertIn('200', errors[0])
        self.assertContains(response, 'value="%s"' % long_title)
        self.assertContains(response, 'kept</textarea>')
        self.assertEqual(Task.objects.count(), before)

    def test_too_long_description_rejected_and_kept(self):
        """spec 05 AC-4: a 2001-character description → description error
        stating the limit, nothing created, typed values shown again."""
        before = Task.objects.count()
        long_text = 'd' * 2001
        response = self.post(self.bob, {'title': 'Write brief', 'description': long_text})
        self.assertEqual(response.status_code, 200)
        errors = response.context['form'].errors['description']
        self.assertEqual(len(errors), 1)
        self.assertIn('2000', errors[0].replace(',', ''))
        self.assertContains(response, long_text + '</textarea>')
        self.assertContains(response, 'value="Write brief"')
        self.assertEqual(Task.objects.count(), before)

    def test_exact_limits_accepted(self):
        """spec 05 AC-4: exactly 200 and 2000 characters are accepted."""
        response = self.post(self.bob, {'title': 't' * 200, 'description': 'd' * 2000})
        task = Task.objects.get(title='t' * 200)
        self.assertEqual(len(task.description), 2000)
        self.assertRedirects(response, self.detail_url(self.apollo, self.roadmap, task))

    def test_blank_description_saved_empty(self):
        """spec 05 AC-5: an all-space description saves as ''."""
        self.post(self.bob, {'title': 'Write brief', 'description': '    '})
        task = Task.objects.get(title='Write brief')
        self.assertEqual(task.description, '')

    def test_duplicate_titles_create_separate_tasks(self):
        """spec 05 AC-6 (OQ-3): two "Review" tasks in Roadmap give two
        separate tasks; a title differing only in letter case is allowed
        too."""
        before = self.roadmap.tasks.count()
        first = self.post(self.bob, {'title': 'Review'})
        second = self.post(self.alice, {'title': 'Review'})
        third = self.post(self.bob, {'title': 'REVIEW'})
        for response in (first, second, third):
            self.assertEqual(response.status_code, 302)
        self.assertEqual(self.roadmap.tasks.count(), before + 3)
        self.assertEqual(self.roadmap.tasks.filter(title='Review').count(), 2)
        self.assertEqual(self.roadmap.tasks.filter(title='REVIEW').count(), 1)
        self.assertNotEqual(first['Location'], second['Location'])


# --------------------------------------------------------------------------
# spec 05 AC-7 … AC-9: the project page's tasks section
# --------------------------------------------------------------------------
class ProjectTasksSectionTests(TaskTestData):
    def page(self, user, project):
        response = self.client_for(user).get(self.project_url(self.apollo, project))
        self.assertEqual(response.status_code, 200)
        return response

    def task_links(self, section, project):
        prefix = self.project_url(self.apollo, project).rstrip('/') + '/tasks/'
        create = self.create_url(self.apollo, project)
        return [
            a.attrs['href'] for a in section.find_all('a')
            if a.attrs.get('href', '').startswith(prefix)
            and a.attrs.get('href') != create
        ]

    def test_tasks_listed_in_creation_order_not_alphabetically(self):
        """spec 05 AC-7 (OQ-4): tasks created "Zeta", "alpha", "Mid" are
        listed in that order (not alphabetically), each linking to its page,
        with the count and a header "New task"; after a fourth is added the
        first three keep their positions and it appears last."""
        self.roadmap.tasks.all().delete()
        created = [
            Task.objects.create(project=self.roadmap, title=title)
            for title in ('Zeta', 'alpha', 'Mid')
        ]
        expected = [self.detail_url(self.apollo, self.roadmap, t) for t in created]
        for user in (self.alice, self.bob):
            with self.subTest(user=user.username):
                response = self.page(user, self.roadmap)
                self.assertEqual(
                    [t.title for t in response.context['tasks']],
                    ['Zeta', 'alpha', 'Mid'],
                )
                section = section_of(parse(response), 'tasks-heading')
                self.assertEqual(section.attrs.get('aria-labelledby'), 'tasks-heading')
                self.assertEqual(by_id(section, 'tasks-heading').norm_text(), 'Tasks')
                self.assertEqual(section.find(class_='badge').norm_text(), '3')
                self.assertEqual(self.task_links(section, self.roadmap), expected)
                # Step 07 (spec 07 AC-2) deliberately adds each task's status to
                # its row, so a row reads '<title> <status>'; the order is unchanged.
                rows = [li.norm_text() for li in section.find_all('li')]
                self.assertEqual(rows, ['Zeta To do', 'alpha To do', 'Mid To do'])
                create = [
                    a for a in section.find_all('a')
                    if a.attrs.get('href') == self.create_url(self.apollo, self.roadmap)
                ]
                self.assertEqual([a.norm_text() for a in create], ['New task'])
                self.assertIn('btn-primary', create[0].classes)

        # A fourth task, added through the form, goes last.
        self.client_for(self.bob).post(
            self.create_url(self.apollo, self.roadmap), {'title': 'Beta'}
        )
        fourth = Task.objects.get(title='Beta')
        section = section_of(parse(self.page(self.alice, self.roadmap)), 'tasks-heading')
        self.assertEqual(
            self.task_links(section, self.roadmap),
            expected + [self.detail_url(self.apollo, self.roadmap, fourth)],
        )
        self.assertEqual(
            [li.norm_text() for li in section.find_all('li')],
            ['Zeta To do', 'alpha To do', 'Mid To do', 'Beta To do'],
        )
        self.assertEqual(section.find(class_='badge').norm_text(), '4')

    def test_order_is_the_same_on_every_load(self):
        """spec 05 AC-7 (OQ-4): the order is stable across page loads."""
        Task.objects.create(project=self.roadmap, title='Aardvark')
        Task.objects.create(project=self.roadmap, title='Zebra')
        first = self.page(self.bob, self.roadmap)
        second = self.page(self.alice, self.roadmap)
        titles = [t.title for t in first.context['tasks']]
        self.assertEqual(titles, ['Draft outline', 'Aardvark', 'Zebra'])
        self.assertEqual([t.title for t in second.context['tasks']], titles)

    def test_no_date_or_time_shown(self):
        """spec 05 AC-7 (OQ-4): no creation date or time appears in the
        tasks section."""
        for title in ('Zeta', 'alpha', 'Mid'):
            Task.objects.create(project=self.roadmap, title=title)
        section = section_of(parse(self.page(self.bob, self.roadmap)), 'tasks-heading')
        text = section.norm_text()
        self.assertEqual(DATE_OR_TIME.findall(text), [], text)
        self.assertEqual(section.find_all('time'), [])

    def test_project_content_kept_and_tasks_after_description(self):
        """spec 05 AC-7: the project's name, description and back link stay,
        and the tasks section comes after the description."""
        root = parse(self.page(self.bob, self.roadmap))
        main = main_of(root)
        h1 = main.find('h1')
        self.assertEqual(h1.norm_text(), 'Roadmap')
        description = section_of(root, 'description-heading')
        self.assertIn('Plan the work.', description.norm_text())
        back = main.find_all('a', href=self.workspace_url(self.apollo))
        self.assertEqual(len(back), 1)
        self.assertLess(back[0].order, h1.order)
        tasks = section_of(root, 'tasks-heading')
        self.assertLess(description.order, tasks.order)

    def test_empty_state_has_own_create_action(self):
        """spec 05 AC-8 (OQ-5): Launch, with no tasks, shows "No tasks yet."
        and its own "New task" link inside the empty state; the header has
        no create action and there are no task rows."""
        for user in (self.alice, self.bob):
            with self.subTest(user=user.username):
                response = self.page(user, self.launch)
                self.assertEqual(list(response.context['tasks']), [])
                section = section_of(parse(response), 'tasks-heading')
                self.assertIn('No tasks yet.', section.norm_text())
                self.assertEqual(section.find(class_='badge').norm_text(), '0')
                create_url = self.create_url(self.apollo, self.launch)
                create = [
                    a for a in section.find_all('a')
                    if a.attrs.get('href') == create_url
                ]
                self.assertEqual(len(create), 1)
                self.assertEqual(create[0].norm_text(), 'New task')
                self.assertIn('btn-primary', create[0].classes)
                # Inside the empty state: it shares a container with the message.
                self.assertIn('No tasks yet.', create[0].parent.norm_text())
                # Not in the header (the element holding the heading).
                header = by_id(section, 'tasks-heading').parent.parent
                self.assertFalse(create[0].has_ancestor(lambda n: n is header))
                self.assertEqual(section.find_all('li'), [])
                self.assertEqual(self.task_links(section, self.launch), [])

    def test_never_lists_other_projects_tasks(self):
        """spec 05 AC-9: Launch's tasks never appear on Roadmap's page, and
        Hermes Plan's appear on neither, nor do Roadmap's on Launch's."""
        launch_task = Task.objects.create(project=self.launch, title='Go live now')
        hermes_task = Task.objects.create(project=self.hermes_plan, title='Deliver mail')

        roadmap_page = self.page(self.bob, self.roadmap)
        self.assertEqual(list(roadmap_page.context['tasks']), [self.task])
        self.assertNotContains(roadmap_page, 'Go live now')
        self.assertNotContains(roadmap_page, 'Deliver mail')
        self.assertNotIn(
            self.detail_url(self.apollo, self.launch, launch_task), hrefs(roadmap_page)
        )

        launch_page = self.page(self.bob, self.launch)
        self.assertEqual(list(launch_page.context['tasks']), [launch_task])
        self.assertNotContains(launch_page, 'Draft outline')
        self.assertNotContains(launch_page, 'Deliver mail')

        hermes_page = self.client_for(self.carol).get(
            self.project_url(self.hermes, self.hermes_plan)
        )
        self.assertEqual(list(hermes_page.context['tasks']), [hermes_task])
        self.assertNotContains(hermes_page, 'Draft outline')
        self.assertNotContains(hermes_page, 'Go live now')


class StepFourBehaviourKeptTests(TaskTestData):
    def test_project_page_still_renders_step_04_content(self):
        """spec 05 AC-21 (with the full suite): Roadmap's project page still
        answers 200 to members with its name as h1, its description and the
        back link to Apollo, and still 404s for a non-member."""
        url = self.project_url(self.apollo, self.roadmap)
        for user in (self.alice, self.bob):
            with self.subTest(user=user.username):
                response = self.client_for(user).get(url)
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, 'projects/project_detail.html')
                main = main_of(parse(response))
                self.assertEqual(main.find('h1').norm_text(), 'Roadmap')
                self.assertIn('Plan the work.', main.norm_text())
                self.assertEqual(
                    len(main.find_all('a', href=self.workspace_url(self.apollo))), 1
                )
        self.assertEqual(self.client_for(self.dave).get(url).status_code, 404)


# --------------------------------------------------------------------------
# spec 05 AC-10, AC-11: the task page and escaping
# --------------------------------------------------------------------------
class TaskPageTests(TaskTestData):
    def test_page_shows_title_description_and_where_it_belongs(self):
        """spec 05 AC-10: the title as h1, the description with its line
        breaks, a context line naming Apollo and Roadmap, and a back link
        "Back to Roadmap" to Roadmap's page."""
        url = self.detail_url(self.apollo, self.roadmap, self.task)
        for user in (self.alice, self.bob):
            with self.subTest(user=user.username):
                response = self.client_for(user).get(url)
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, 'tasks/task_detail.html')
                self.assertEqual(response.context['task'], self.task)
                html = response.content.decode()
                self.assertIn('First line.<br>Second line.', html)
                self.assertNotContains(response, 'No description')
                main = main_of(parse(response))
                self.assertEqual(len(main.find_all('h1')), 1)
                self.assertEqual(main.find('h1').norm_text(), 'Draft outline')
                back = main.find_all('a', href=self.project_url(self.apollo, self.roadmap))
                self.assertEqual(len(back), 1)
                self.assertEqual(back[0].norm_text(), 'Back to Roadmap')
                context_lines = [
                    p for p in main.find_all('p')
                    if 'Apollo' in p.norm_text() and 'Roadmap' in p.norm_text()
                ]
                self.assertEqual(len(context_lines), 1)

    def test_no_description_note(self):
        """spec 05 AC-10: an empty description shows "No description"."""
        task = Task.objects.create(project=self.roadmap, title='Bare')
        response = self.client_for(self.bob).get(
            self.detail_url(self.apollo, self.roadmap, task)
        )
        self.assertContains(response, 'No description')

    def test_no_creator_or_date_shown(self):
        """spec 05 AC-10 (OQ-6): the task page shows no creator and no
        creation date.

        Updated in step 06: spec 06 AC-2 deliberately lists workspace members
        in the Assignee section's control, so member names are checked
        everywhere on the page except that section. The no-creator and
        no-date rules themselves are unchanged."""
        response = self.client_for(self.bob).get(
            self.detail_url(self.apollo, self.roadmap, self.task)
        )
        main = main_of(parse(response))
        self.assertEqual(DATE_OR_TIME.findall(main.norm_text()), [])
        self.assertEqual(main.find_all('time'), [])
        assignee_section = main.find('section', **{'aria-labelledby': 'assignee-heading'})
        self.assertIsNotNone(assignee_section)
        outside = main.norm_text().replace(assignee_section.norm_text(), '')
        for name in ('Alice', 'Bob'):
            self.assertNotIn(name, outside)

    def test_head_allowed(self):
        """spec 05 AC-10: the task page answers HEAD for a member."""
        response = self.client_for(self.bob).head(
            self.detail_url(self.apollo, self.roadmap, self.task)
        )
        self.assertEqual(response.status_code, 200)


class EscapingTests(TaskTestData):
    TITLE = '<script>alert(1)</script>'
    DESCRIPTION = '<b>x</b>\n<i>y</i>'
    ESCAPED_TITLE = '&lt;script&gt;alert(1)&lt;/script&gt;'
    ESCAPED_DESCRIPTION = '&lt;b&gt;x&lt;/b&gt;<br>&lt;i&gt;y&lt;/i&gt;'

    def assert_no_raw_markup(self, html):
        self.assertNotIn('<script>alert(1)', html)
        self.assertNotIn('<b>x</b>', html)
        self.assertNotIn('<i>y</i>', html)

    def test_escaped_in_message_task_page_and_title(self):
        """spec 05 AC-11: a script-like title and HTML-like two-line
        description are escaped in the creation message and on the task page
        (including <title>), with <br> between the escaped lines."""
        response = self.client_for(self.bob).post(
            self.create_url(self.apollo, self.roadmap),
            {'title': self.TITLE, 'description': self.DESCRIPTION},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        task = Task.objects.get(project=self.roadmap, title=self.TITLE)
        self.assertEqual(task.description, self.DESCRIPTION)
        html = response.content.decode()
        self.assert_no_raw_markup(html)
        self.assertIn('Task &quot;%s&quot; was created.' % self.ESCAPED_TITLE, html)
        title = re.search(r'<title>(.*?)</title>', html, re.S).group(1)
        self.assertIn(self.ESCAPED_TITLE, title)
        self.assertNotIn('<', title)
        self.assertRegex(html, r'<h1[^>]*>%s</h1>' % re.escape(self.ESCAPED_TITLE))
        self.assertIn(self.ESCAPED_DESCRIPTION, html)

    def test_escaped_on_project_page(self):
        """spec 05 AC-11: the title is escaped in the project page's task list."""
        Task.objects.create(
            project=self.roadmap, title=self.TITLE, description=self.DESCRIPTION
        )
        response = self.client_for(self.alice).get(
            self.project_url(self.apollo, self.roadmap)
        )
        html = response.content.decode()
        self.assert_no_raw_markup(html)
        self.assertIn(self.ESCAPED_TITLE, html)

    def test_markup_like_project_and_workspace_names_escaped(self):
        """spec 05 AC-11: markup-like workspace and project names are shown
        as text on the create page and the task page."""
        workspace = Workspace.objects.create_with_owner('<em>WS</em>', self.dave)
        project = Project.objects.create(workspace=workspace, name='<u>P</u>')
        task = Task.objects.create(project=project, title='Plain')
        client = self.client_for(self.dave)
        for url in (
            self.create_url(workspace, project),
            self.detail_url(workspace, project, task),
        ):
            with self.subTest(url=url):
                html = client.get(url).content.decode()
                self.assertNotIn('<em>WS</em>', html)
                self.assertNotIn('<u>P</u>', html)
                self.assertIn('&lt;u&gt;P&lt;/u&gt;', html)
        detail = client.get(self.detail_url(workspace, project, task)).content.decode()
        self.assertIn('&lt;em&gt;WS&lt;/em&gt;', detail)


# --------------------------------------------------------------------------
# spec 05 AC-12 … AC-14: not found for non-members, wrong parents, missing IDs
# --------------------------------------------------------------------------
class SecretTaskData(TaskTestData):
    SECRET_TITLE = 'Secret Moonshot'
    SECRET_DESCRIPTION = 'Classified orbital plan'

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.secret = Task.objects.create(
            project=cls.roadmap,
            title=cls.SECRET_TITLE,
            description=cls.SECRET_DESCRIPTION,
        )

    def assert_hidden_404(self, response):
        self.assertEqual(response.status_code, 404)
        for text in (self.SECRET_TITLE, self.SECRET_DESCRIPTION, 'Apollo', 'Roadmap'):
            self.assertNotContains(response, text, status_code=404)

    def assert_nothing_created(self, before, title):
        self.assertEqual(Task.objects.count(), before)
        self.assertFalse(Task.objects.filter(title=title).exists())


class NonMemberAccessTests(SecretTaskData):
    def test_non_member_get_create_is_404(self):
        """spec 05 AC-12: Dave and Carol GET Roadmap's create page → 404,
        never 403."""
        for user in (self.dave, self.carol):
            with self.subTest(user=user.username):
                response = self.client_for(user).get(
                    self.create_url(self.apollo, self.roadmap)
                )
                self.assert_hidden_404(response)

    def test_non_member_get_and_head_detail_is_404(self):
        """spec 05 AC-12: Dave and Carol GET or HEAD a Roadmap task → 404
        that reveals neither its title nor its description."""
        url = self.detail_url(self.apollo, self.roadmap, self.secret)
        for user in (self.dave, self.carol):
            with self.subTest(user=user.username):
                client = self.client_for(user)
                self.assert_hidden_404(client.get(url))
                self.assertEqual(client.head(url).status_code, 404)

    def test_non_member_post_create_is_404_and_creates_nothing(self):
        """spec 05 AC-12: Dave and Carol POST to Roadmap's create URL → 404,
        nothing created anywhere."""
        before = Task.objects.count()
        for user in (self.dave, self.carol):
            with self.subTest(user=user.username):
                response = self.client_for(user).post(
                    self.create_url(self.apollo, self.roadmap),
                    {'title': 'Intruder', 'description': 'x'},
                )
                self.assert_hidden_404(response)
                self.assert_nothing_created(before, 'Intruder')

    def test_non_member_404_matches_missing_workspace_404(self):
        """spec 05 AC-12 / AC-14: a non-member's 404 is the same response as
        for a workspace that doesn't exist."""
        client = self.client_for(self.dave)
        missing = missing_pk(Workspace)
        real = client.get(self.detail_url(self.apollo, self.roadmap, self.secret))
        fake = client.get(self.detail_url(missing, self.roadmap, self.secret))
        self.assertEqual(real.status_code, 404)
        self.assertEqual(fake.status_code, 404)
        self.assertEqual(real.content, fake.content)
        real = client.get(self.create_url(self.apollo, self.roadmap))
        fake = client.get(self.create_url(missing, self.roadmap))
        self.assertEqual(real.status_code, 404)
        self.assertEqual(real.content, fake.content)


class WrongParentViewTests(SecretTaskData):
    """spec 05 AC-13, viewing: an existing task in Apollo/Roadmap is only
    reachable through Apollo/Roadmap."""

    def test_task_under_other_workspace_is_404(self):
        """spec 05 AC-13 (a): workspace=Hermes, project=Roadmap, task=T →
        404 for Carol, and for Bob after he joins Hermes too."""
        url = self.detail_url(self.hermes, self.roadmap, self.secret)
        self.assert_hidden_404(self.client_for(self.carol).get(url))
        self.hermes.add_member(self.bob)
        self.assert_hidden_404(self.client_for(self.bob).get(url))

    def test_task_under_other_project_in_same_workspace_is_404(self):
        """spec 05 AC-13 (b): workspace=Apollo, project=Launch, task=T → 404
        for Bob and Alice (right workspace, wrong project)."""
        url = self.detail_url(self.apollo, self.launch, self.secret)
        for user in (self.alice, self.bob):
            with self.subTest(user=user.username):
                response = self.client_for(user).get(url)
                self.assertEqual(response.status_code, 404)
                self.assertNotContains(response, self.SECRET_TITLE, status_code=404)
                self.assertNotContains(
                    response, self.SECRET_DESCRIPTION, status_code=404
                )

    def test_task_under_project_of_other_workspace_is_404(self):
        """spec 05 AC-13 (c): workspace=Apollo, project=Hermes Plan, task=T
        → 404, even for a member of both workspaces."""
        url = self.detail_url(self.apollo, self.hermes_plan, self.secret)
        self.assert_hidden_404(self.client_for(self.bob).get(url))
        self.hermes.add_member(self.bob)
        self.assert_hidden_404(self.client_for(self.bob).get(url))

    def test_task_reachable_through_its_real_parents(self):
        """spec 05 AC-13 (control): the same task under Apollo/Roadmap is 200."""
        self.hermes.add_member(self.bob)
        response = self.client_for(self.bob).get(
            self.detail_url(self.apollo, self.roadmap, self.secret)
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.SECRET_TITLE)


class WrongParentCreateTests(SecretTaskData):
    """spec 05 AC-13, creating: 404 only when the URL's workspace/project
    scope is itself invalid, inaccessible or missing; nothing is created."""

    def assert_create_404(self, user, url):
        before = Task.objects.count()
        client = self.client_for(user)
        get = client.get(url)
        post = client.post(url, {'title': 'Misplaced', 'description': 'x'})
        for method, response in (('GET', get), ('POST', post)):
            with self.subTest(user=user.username, method=method, url=url):
                self.assertEqual(response.status_code, 404)
        self.assert_nothing_created(before, 'Misplaced')

    def test_project_not_in_that_workspace(self):
        """spec 05 AC-13 (d) / (e): Hermes/Roadmap and Apollo/Hermes Plan →
        404 for GET and POST, even for a member of both workspaces."""
        self.hermes.add_member(self.bob)
        for user in (self.bob, self.carol, self.alice):
            self.assert_create_404(user, self.create_url(self.hermes, self.roadmap))
            self.assert_create_404(user, self.create_url(self.apollo, self.hermes_plan))

    def test_workspace_user_is_not_member_of(self):
        """spec 05 AC-13 (f): Dave and Carol under Apollo/Roadmap → 404."""
        for user in (self.dave, self.carol):
            self.assert_create_404(user, self.create_url(self.apollo, self.roadmap))

    def test_missing_workspace_or_project(self):
        """spec 05 AC-13 (g): a missing workspace or project ID → 404."""
        missing_ws = missing_pk(Workspace)
        missing_project = missing_pk(Project)
        self.assert_create_404(self.bob, self.create_url(missing_ws, self.roadmap))
        self.assert_create_404(self.bob, self.create_url(self.apollo, missing_project))
        self.assert_create_404(self.bob, self.create_url(missing_ws, missing_project))

    def test_valid_other_project_in_same_workspace_creates_there(self):
        """spec 05 AC-13 (clarified): Bob POSTs under Apollo/Launch, a valid
        scope he can access → 302, exactly one new task, in Launch, none
        added to Roadmap."""
        before = Task.objects.count()
        roadmap_before = self.roadmap.tasks.count()
        response = self.client_for(self.bob).post(
            self.create_url(self.apollo, self.launch), {'title': 'Go live'}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Task.objects.count(), before + 1)
        task = Task.objects.get(title='Go live')
        self.assertEqual(task.project, self.launch)
        self.assertEqual(self.roadmap.tasks.count(), roadmap_before)
        self.assertRedirects(response, self.detail_url(self.apollo, self.launch, task))


class MissingIdTests(SecretTaskData):
    def test_missing_ids_are_404_like_non_member(self):
        """spec 05 AC-14: a missing workspace, project or task ID → 404 with
        the same body as a non-member's 404 (AC-12)."""
        missing_ws = missing_pk(Workspace)
        missing_project = missing_pk(Project)
        missing_task = missing_pk(Task)
        non_member = self.client_for(self.dave).get(
            self.detail_url(self.apollo, self.roadmap, self.secret)
        )
        self.assertEqual(non_member.status_code, 404)
        client = self.client_for(self.bob)
        before = Task.objects.count()
        responses = {
            'detail missing workspace': client.get(
                self.detail_url(missing_ws, self.roadmap, self.secret)
            ),
            'detail missing project': client.get(
                self.detail_url(self.apollo, missing_project, self.secret)
            ),
            'detail missing task': client.get(
                self.detail_url(self.apollo, self.roadmap, missing_task)
            ),
            'create GET missing project': client.get(
                self.create_url(self.apollo, missing_project)
            ),
            'create POST missing workspace': client.post(
                self.create_url(missing_ws, self.roadmap), {'title': 'X'}
            ),
        }
        for label, response in responses.items():
            with self.subTest(case=label):
                self.assertEqual(response.status_code, 404)
                self.assertEqual(response.content, non_member.content)
        self.assertEqual(Task.objects.count(), before)


# --------------------------------------------------------------------------
# spec 05 AC-15, AC-16: anonymous visitors
# --------------------------------------------------------------------------
class AnonymousAccessTests(TaskTestData):
    def login_redirect(self, path):
        return '%s?next=%s' % (reverse('accounts:login'), path)

    def urls(self):
        return (
            self.create_url(self.apollo, self.roadmap),
            self.detail_url(self.apollo, self.roadmap, self.task),
        )

    def test_anonymous_get_redirects_with_next(self):
        """spec 05 AC-15: anonymous GET of create and detail → login?next=<path>."""
        for url in self.urls():
            with self.subTest(url=url):
                response = Client().get(url)
                self.assertRedirects(
                    response, self.login_redirect(url), fetch_redirect_response=False
                )

    def test_anonymous_get_missing_ids_also_redirect(self):
        """spec 05 AC-15: login is checked before any lookup, so an anonymous
        visitor learns nothing from IDs."""
        for url in (
            self.create_url(missing_pk(Workspace), missing_pk(Project)),
            self.detail_url(self.apollo, self.roadmap, missing_pk(Task)),
        ):
            with self.subTest(url=url):
                response = Client().get(url)
                self.assertRedirects(
                    response, self.login_redirect(url), fetch_redirect_response=False
                )

    def test_login_with_next_lands_on_page_for_member(self):
        """spec 05 AC-15: Bob logs in with next=<page> → lands there (200)."""
        for url in self.urls():
            with self.subTest(url=url):
                response = Client().post(
                    self.login_redirect(url), {'username': 'Bob', 'password': PASSWORD}
                )
                self.assertRedirects(response, url)

    def test_login_with_next_still_404_for_non_member(self):
        """spec 05 AC-15: Dave logs in with next=<page> → still 404 there."""
        for url in self.urls():
            with self.subTest(url=url):
                response = Client().post(
                    self.login_redirect(url), {'username': 'Dave', 'password': PASSWORD}
                )
                self.assertRedirects(response, url, target_status_code=404)

    def test_anonymous_post_not_replayed(self):
        """spec 05 AC-16: anonymous POST → exactly the login URL (no next),
        nothing created; logging in afterwards lands on the dashboard and
        still creates nothing."""
        before = Task.objects.count()
        client = Client()
        response = client.post(
            self.create_url(self.apollo, self.roadmap), {'title': 'Ghost'}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], reverse('accounts:login'))
        self.assertEqual(Task.objects.count(), before)

        response = client.post(
            reverse('accounts:login'), {'username': 'Bob', 'password': PASSWORD}
        )
        self.assertRedirects(response, reverse('core:dashboard'))
        self.assertEqual(Task.objects.count(), before)
        self.assertFalse(Task.objects.filter(title='Ghost').exists())

    def test_anonymous_post_to_detail_goes_to_login(self):
        """spec 05 AC-16: an anonymous POST to a task page also goes to plain
        login and changes nothing."""
        before = list(Task.objects.values_list('pk', 'title', 'description'))
        response = Client().post(
            self.detail_url(self.apollo, self.roadmap, self.task), {'title': 'X'}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], reverse('accounts:login'))
        self.assertEqual(
            list(Task.objects.values_list('pk', 'title', 'description')), before
        )


# --------------------------------------------------------------------------
# spec 05 AC-17, AC-18: CSRF and GET-never-creates
# --------------------------------------------------------------------------
class CsrfAndMethodTests(TaskTestData):
    def test_post_without_csrf_token_rejected(self):
        """spec 05 AC-17: a create POST without the CSRF token → 403,
        nothing created."""
        before = Task.objects.count()
        client = self.client_for(self.bob, enforce_csrf_checks=True)
        response = client.post(
            self.create_url(self.apollo, self.roadmap), {'title': 'Forged'}
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Task.objects.count(), before)
        self.assertFalse(Task.objects.filter(title='Forged').exists())

    def test_post_with_csrf_token_accepted(self):
        """spec 05 AC-17 (control): the same client with the page's token
        succeeds, so the 403 above is the CSRF check."""
        client = self.client_for(self.bob, enforce_csrf_checks=True)
        url = self.create_url(self.apollo, self.roadmap)
        page = client.get(url)
        self.assertContains(page, 'csrfmiddlewaretoken')
        response = client.post(
            url, {'title': 'Genuine', 'csrfmiddlewaretoken': str(page.context['csrf_token'])}
        )
        task = Task.objects.get(title='Genuine')
        self.assertRedirects(response, self.detail_url(self.apollo, self.roadmap, task))

    def test_get_with_query_params_creates_nothing(self):
        """spec 05 AC-18: GET create?title=X&description=Y shows an unbound
        form and creates nothing."""
        before = Task.objects.count()
        response = self.client_for(self.bob).get(
            self.create_url(self.apollo, self.roadmap),
            {'title': 'Sneaky', 'description': 'Y'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['form'].is_bound)
        self.assertEqual(Task.objects.count(), before)
        self.assertFalse(Task.objects.filter(title='Sneaky').exists())

    def test_post_to_detail_not_allowed(self):
        """spec 05 AC-18: POST (and PUT/DELETE) to a task page → 405 and
        nothing changes."""
        before = list(Task.objects.values_list('pk', 'project', 'title', 'description'))
        client = self.client_for(self.bob)
        url = self.detail_url(self.apollo, self.roadmap, self.task)
        self.assertEqual(client.post(url, {'title': 'Changed'}).status_code, 405)
        self.assertEqual(client.put(url).status_code, 405)
        self.assertEqual(client.delete(url).status_code, 405)
        self.assertEqual(
            list(Task.objects.values_list('pk', 'project', 'title', 'description')),
            before,
        )


# --------------------------------------------------------------------------
# spec 05 AC-19: data integrity
# --------------------------------------------------------------------------
class PostedIdsIgnoredTests(TaskTestData):
    def test_posted_project_and_workspace_ignored(self):
        """spec 05 AC-19: extra project=<Launch> / <Hermes Plan> and
        workspace=<Hermes> values posted to Roadmap's create URL never move
        the task: it is created in Roadmap every time."""
        cases = {
            'Moved to Launch': {'project': self.launch.pk, 'workspace': self.hermes.pk},
            'Moved to Hermes Plan': {'project': self.hermes_plan.pk},
            'Moved everywhere': {
                'project': self.hermes_plan.pk,
                'project_id': self.launch.pk,
                'workspace': self.hermes.pk,
            },
        }
        for title, extra in cases.items():
            with self.subTest(title=title):
                response = self.client_for(self.bob).post(
                    self.create_url(self.apollo, self.roadmap),
                    {'title': title, **extra},
                )
                task = Task.objects.get(title=title)
                self.assertEqual(task.project, self.roadmap)
                self.assertRedirects(
                    response, self.detail_url(self.apollo, self.roadmap, task)
                )
        self.assertEqual(self.launch.tasks.count(), 0)
        self.assertEqual(self.hermes_plan.tasks.count(), 0)


# --------------------------------------------------------------------------
# spec 05 AC-18 (review S-5): the create URL accepts only GET/HEAD/POST
# --------------------------------------------------------------------------
class CreateMethodRestrictionTests(SecretTaskData):
    """spec 05 AC-18 (review S-5): PUT, PATCH and DELETE are not a second
    write path into a project's task list."""

    BODY = 'title=Smuggled&description=via+other+method'
    CONTENT_TYPE = 'application/x-www-form-urlencoded'

    def test_member_put_patch_delete_create_is_405_and_creates_nothing(self):
        """spec 05 AC-18 (review S-5): Bob (member, valid scope) sends PUT,
        PATCH and DELETE to tasks:create → 405, no task created."""
        client = self.client_for(self.bob)
        url = self.create_url(self.apollo, self.roadmap)
        before = Task.objects.count()
        for method in ('put', 'patch', 'delete'):
            with self.subTest(method=method):
                response = getattr(client, method)(
                    url, self.BODY, content_type=self.CONTENT_TYPE
                )
                self.assertEqual(response.status_code, 405)
                self.assert_nothing_created(before, 'Smuggled')

    def test_member_get_and_post_create_still_work(self):
        """spec 05 AC-18 (review S-5, control): GET still shows the form
        (200) and POST still creates the task, so the 405s above come from
        the method restriction only."""
        client = self.client_for(self.bob)
        url = self.create_url(self.apollo, self.roadmap)
        self.assertEqual(client.get(url).status_code, 200)
        response = client.post(url, {'title': 'Allowed', 'description': 'ok'})
        task = Task.objects.get(title='Allowed')
        self.assertEqual(task.project, self.roadmap)
        self.assertRedirects(response, self.detail_url(self.apollo, self.roadmap, task))

    def test_non_member_put_create_is_404_not_405(self):
        """spec 05 AC-12 / AC-18 (review S-5): Dave and Carol PUT to Roadmap's
        create URL → 404, not 405: the scope is resolved before the method
        is checked, so a 405 never reveals that the project exists."""
        url = self.create_url(self.apollo, self.roadmap)
        before = Task.objects.count()
        for user in (self.dave, self.carol):
            with self.subTest(user=user.username):
                response = self.client_for(user).put(
                    url, self.BODY, content_type=self.CONTENT_TYPE
                )
                self.assert_hidden_404(response)
                self.assert_nothing_created(before, 'Smuggled')
