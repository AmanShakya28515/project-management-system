"""Task assignment (spec 06). Tests are tagged "spec 06 AC-n"."""
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.urls import reverse

from core.tests.helpers import main_of, parse
from tasks.models import Task

from .data import PASSWORD, TaskTestData, missing_pk, pk_of

User = get_user_model()


class AssignmentData(TaskTestData):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        # Erin is a member of Apollo but deactivated: never assignable.
        cls.erin = User.objects.create_user(
            username='Erin', email='erin@example.com', password=PASSWORD,
            is_active=False,
        )
        cls.apollo.add_member(cls.erin)

    @staticmethod
    def assign_url(workspace, project, task):
        return reverse(
            'tasks:assign',
            kwargs={
                'workspace_pk': pk_of(workspace),
                'project_pk': pk_of(project),
                'pk': pk_of(task),
            },
        )

    def assign(self, user, assignee, client=None, task=None):
        task = task or self.task
        client = client or self.client_for(user)
        data = {'assignee': '' if assignee is None else pk_of(assignee)}
        return client.post(self.assign_url(self.apollo, self.roadmap, task), data)

    def refresh(self):
        self.task.refresh_from_db()
        return self.task.assignee

    @staticmethod
    def message_texts(response):
        return [str(m) for m in get_messages(response.wsgi_request)]

    def assignee_section(self, response):
        main = main_of(parse(response))
        section = main.find('section', **{'aria-labelledby': 'assignee-heading'})
        self.assertIsNotNone(section)
        return section


class ShowAssigneeTests(AssignmentData):
    def test_new_task_shows_unassigned(self):
        """spec 06 AC-1: a new task starts unassigned and says so."""
        self.assertIsNone(self.task.assignee)
        response = self.client_for(self.bob).get(
            self.detail_url(self.apollo, self.roadmap, self.task)
        )
        section = self.assignee_section(response)
        self.assertIn('Unassigned', section.norm_text())

    def test_assigned_task_shows_username(self):
        """spec 06 AC-1: the page shows the current assignee's username."""
        Task.objects.filter(pk=self.task.pk).update(assignee=self.alice)
        response = self.client_for(self.bob).get(
            self.detail_url(self.apollo, self.roadmap, self.task)
        )
        text = self.assignee_section(response).norm_text()
        self.assertIn('Alice', text.split('Assignee', 1)[1])


class ChoicesTests(AssignmentData):
    def test_choices_are_unassigned_then_active_members(self):
        """spec 06 AC-2 (OQ-1): "Unassigned" first, then active members of
        this workspace, owner first then alphabetical; nobody else."""
        response = self.client_for(self.bob).get(
            self.detail_url(self.apollo, self.roadmap, self.task)
        )
        select = self.assignee_section(response).find('select')
        self.assertIsNotNone(select)
        options = [o.norm_text() for o in select.find_all('option')]
        self.assertEqual(options, ['Unassigned', 'Alice', 'Bob'])

    def test_control_is_labelled(self):
        """spec 06 AC-12: the select has a visible label and the button is a
        shared button style."""
        response = self.client_for(self.bob).get(
            self.detail_url(self.apollo, self.roadmap, self.task)
        )
        section = self.assignee_section(response)
        select = section.find('select')
        label = section.find('label', **{'for': select.attrs['id']})
        self.assertIsNotNone(label)
        self.assertIn('Assignee', label.norm_text())
        button = section.find('button')
        self.assertIn('btn-secondary', button.classes)


class AssignTests(AssignmentData):
    def test_assign_member(self):
        """spec 06 AC-3: assigning redirects to the task page with a message
        naming the assignee."""
        response = self.assign(self.bob, self.alice)
        self.assertRedirects(
            response,
            self.detail_url(self.apollo, self.roadmap, self.task),
            fetch_redirect_response=False,
        )
        self.assertEqual(self.refresh(), self.alice)
        self.assertIn('Task assigned to Alice.', self.message_texts(response))

    def test_reassign_replaces(self):
        """spec 06 AC-4: choosing another member replaces the assignee."""
        self.assign(self.bob, self.alice)
        self.assign(self.bob, self.bob)
        self.assertEqual(self.refresh(), self.bob)

    def test_unassign(self):
        """spec 06 AC-5: choosing "Unassigned" removes the assignee."""
        self.assign(self.bob, self.alice)
        response = self.assign(self.bob, None)
        self.assertIsNone(self.refresh())
        self.assertIn('Task is now unassigned.', self.message_texts(response))

    def test_same_assignee_is_a_no_op(self):
        """spec 06 AC-6 (OQ-3): re-submitting the current state changes
        nothing and says so; title and description are untouched."""
        response = self.assign(self.bob, None)
        self.assertIsNone(self.refresh())
        self.assertIn('This task is already unassigned.', self.message_texts(response))
        self.assign(self.bob, self.alice)
        response = self.assign(self.bob, self.alice)
        self.assertEqual(self.refresh(), self.alice)
        self.assertIn('Alice is already assigned.', self.message_texts(response))
        self.assertEqual(self.task.title, 'Draft outline')
        self.assertEqual(self.task.description, 'First line.\nSecond line.')


class InvalidAssigneeTests(AssignmentData):
    def test_outsiders_inactive_and_missing_are_rejected(self):
        """spec 06 AC-7/AC-8: another workspace's user, an inactive member and
        a missing ID are rejected with a field error; the assignee is
        unchanged."""
        Task.objects.filter(pk=self.task.pk).update(assignee=self.alice)
        for bad in (self.carol, self.dave, self.erin, missing_pk(User)):
            with self.subTest(bad=bad):
                response = self.assign(self.bob, bad)
                self.assertEqual(response.status_code, 200)
                form = response.context['assign_form']
                self.assertIn('assignee', form.errors)
                self.assertEqual(self.refresh(), self.alice)
                select = self.assignee_section(response).find('select')
                self.assertEqual(select.attrs.get('aria-invalid'), 'true')


class AccessTests(AssignmentData):
    def test_non_member_wrong_scope_and_missing_ids_are_404(self):
        """spec 06 AC-9: non-members, the wrong workspace or project and
        missing IDs get 404 and nothing changes."""
        cases = [
            (self.carol, self.assign_url(self.apollo, self.roadmap, self.task)),
            (self.dave, self.assign_url(self.apollo, self.roadmap, self.task)),
            (self.bob, self.assign_url(self.apollo, self.launch, self.task)),
            (self.bob, self.assign_url(self.hermes, self.roadmap, self.task)),
            (self.bob, self.assign_url(self.apollo, self.roadmap, missing_pk(Task))),
        ]
        for user, url in cases:
            with self.subTest(user=user.username, url=url):
                response = self.client_for(user).post(url, {'assignee': self.bob.pk})
                self.assertEqual(response.status_code, 404)
                self.assertIsNone(self.refresh())

    def test_anonymous_post_not_replayed(self):
        """spec 06 AC-10: an anonymous assignment goes to login without next,
        and nothing changes."""
        response = self.client_for().post(
            self.assign_url(self.apollo, self.roadmap, self.task),
            {'assignee': self.bob.pk},
        )
        self.assertRedirects(
            response, reverse('accounts:login'), fetch_redirect_response=False
        )
        self.assertIsNone(self.refresh())

    def test_csrf_and_get_change_nothing(self):
        """spec 06 AC-11: no CSRF token → 403; a GET → 405; no change."""
        client = self.client_for(self.bob, enforce_csrf_checks=True)
        url = self.assign_url(self.apollo, self.roadmap, self.task)
        self.assertEqual(client.post(url, {'assignee': self.bob.pk}).status_code, 403)
        self.assertEqual(
            self.client_for(self.bob).get(url, {'assignee': self.bob.pk}).status_code,
            405,
        )
        self.assertIsNone(self.refresh())


class DeleteAssigneeTests(AssignmentData):
    def test_deleting_assignee_leaves_task_unassigned(self):
        """plan 06 D-1: SET_NULL — deleting the assignee's account leaves the
        task unassigned rather than deleting it or blocking the delete."""
        Task.objects.filter(pk=self.task.pk).update(assignee=self.bob)
        self.bob.delete()
        self.assertTrue(Task.objects.filter(pk=self.task.pk).exists())
        self.assertIsNone(self.refresh())
