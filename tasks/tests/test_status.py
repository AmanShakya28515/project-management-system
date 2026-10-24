"""Task status (spec 07). Tests are tagged "spec 07 AC-n"."""
from django.contrib.messages import get_messages
from django.db import IntegrityError, transaction
from django.urls import reverse

from core.tests.helpers import component_rules, main_of, parse
from tasks.models import Task

from .data import TaskTestData, missing_pk, pk_of


class StatusData(TaskTestData):
    @staticmethod
    def status_url(workspace, project, task):
        return reverse(
            'tasks:status',
            kwargs={
                'workspace_pk': pk_of(workspace),
                'project_pk': pk_of(project),
                'pk': pk_of(task),
            },
        )

    def set_status(self, user, value, client=None):
        client = client or self.client_for(user)
        return client.post(
            self.status_url(self.apollo, self.roadmap, self.task), {'status': value}
        )

    def stored(self):
        self.task.refresh_from_db()
        return self.task.status

    @staticmethod
    def message_texts(response):
        return [str(m) for m in get_messages(response.wsgi_request)]

    def status_section(self, response):
        main = main_of(parse(response))
        section = main.find('section', **{'aria-labelledby': 'status-heading'})
        self.assertIsNotNone(section)
        return section


class ShowStatusTests(StatusData):
    def test_existing_and_new_tasks_start_as_todo(self):
        """spec 07 AC-1 (OQ-1): existing and new tasks start as To do, and the
        task page shows it."""
        self.assertEqual(self.task.status, Task.Status.TODO)
        new = Task.objects.create(project=self.roadmap, title='Fresh')
        self.assertEqual(new.status, Task.Status.TODO)
        response = self.client_for(self.bob).get(
            self.detail_url(self.apollo, self.roadmap, self.task)
        )
        badge = self.status_section(response).find(class_='badge')
        self.assertEqual(badge.norm_text(), 'To do')

    def test_project_rows_show_status_text_in_creation_order(self):
        """spec 07 AC-2: each task row shows its status as text; rows stay
        oldest first."""
        second = Task.objects.create(
            project=self.roadmap, title='Second', status=Task.Status.DONE
        )
        third = Task.objects.create(
            project=self.roadmap, title='Third', status=Task.Status.IN_PROGRESS
        )
        response = self.client_for(self.bob).get(
            self.project_url(self.apollo, self.roadmap)
        )
        section = main_of(parse(response)).find(
            'section', **{'aria-labelledby': 'tasks-heading'}
        )
        rows = [li.norm_text() for li in section.find_all('li')]
        self.assertEqual(
            rows, ['Draft outline To do', 'Second Done', 'Third In progress']
        )
        for li in section.find_all('li'):
            self.assertIsNotNone(li.find(class_='badge'))
        self.assertLess(self.task.pk, second.pk)
        self.assertLess(second.pk, third.pk)


class ControlTests(StatusData):
    def test_select_offers_exactly_three_statuses_with_current_selected(self):
        """spec 07 AC-3: the control offers To do, In progress, Done in that
        order, with the current one selected."""
        Task.objects.filter(pk=self.task.pk).update(status=Task.Status.IN_PROGRESS)
        response = self.client_for(self.bob).get(
            self.detail_url(self.apollo, self.roadmap, self.task)
        )
        select = self.status_section(response).find('select')
        options = select.find_all('option')
        self.assertEqual(
            [o.norm_text() for o in options], ['To do', 'In progress', 'Done']
        )
        selected = [o.attrs.get('value') for o in options if 'selected' in o.attrs]
        self.assertEqual(selected, ['in_progress'])

    def test_control_labelled_and_badges_use_tokens(self):
        """spec 07 AC-11: the select is labelled, the button is a shared
        style, and the status badge rules live in the components layer."""
        response = self.client_for(self.bob).get(
            self.detail_url(self.apollo, self.roadmap, self.task)
        )
        section = self.status_section(response)
        select = section.find('select')
        label = section.find('label', **{'for': select.attrs['id']})
        self.assertIn('Status', label.norm_text())
        self.assertIn('btn-secondary', section.find('button').classes)
        rules = component_rules()
        for name in ('.badge-status-todo', '.badge-status-progress', '.badge-status-done'):
            with self.subTest(rule=name):
                self.assertIn(name, rules)


class ChangeStatusTests(StatusData):
    def test_change_status(self):
        """spec 07 AC-4: a different status is saved, the member returns to
        the task page, and a message names the new status."""
        response = self.set_status(self.bob, 'in_progress')
        self.assertRedirects(
            response,
            self.detail_url(self.apollo, self.roadmap, self.task),
            fetch_redirect_response=False,
        )
        self.assertEqual(self.stored(), Task.Status.IN_PROGRESS)
        self.assertIn('Status changed to In progress.', self.message_texts(response))

    def test_same_status_is_a_no_op(self):
        """spec 07 AC-5 (OQ-2): re-submitting the current status changes
        nothing and shows an informational message."""
        response = self.set_status(self.bob, 'todo')
        self.assertEqual(self.stored(), Task.Status.TODO)
        self.assertIn('Status is already To do.', self.message_texts(response))

    def test_only_status_changes(self):
        """spec 07 AC-7: title, description, assignee and project are
        untouched by a status change."""
        Task.objects.filter(pk=self.task.pk).update(assignee=self.alice)
        self.set_status(self.bob, 'done')
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.DONE)
        self.assertEqual(self.task.title, 'Draft outline')
        self.assertEqual(self.task.description, 'First line.\nSecond line.')
        self.assertEqual(self.task.assignee, self.alice)
        self.assertEqual(self.task.project, self.roadmap)


class InvalidStatusTests(StatusData):
    def test_invalid_values_rejected_with_field_error(self):
        """spec 07 AC-6: values outside the three statuses are rejected next to
        the control and the status is unchanged."""
        for bad in ('archived', '', 'TODO', 'Done'):
            with self.subTest(bad=bad):
                response = self.set_status(self.bob, bad)
                self.assertEqual(response.status_code, 200)
                self.assertIn('status', response.context['status_form'].errors)
                select = self.status_section(response).find('select')
                self.assertEqual(select.attrs.get('aria-invalid'), 'true')
                self.assertEqual(self.stored(), Task.Status.TODO)

    def test_database_rejects_unknown_status(self):
        """spec 07 AC-6 (plan 07, D-1): the database check constraint refuses
        an unknown status from any write path."""
        with self.assertRaises(IntegrityError), transaction.atomic():
            Task.objects.filter(pk=self.task.pk).update(status='archived')
        self.assertEqual(self.stored(), Task.Status.TODO)


class AccessTests(StatusData):
    def test_non_member_wrong_scope_and_missing_ids_are_404(self):
        """spec 07 AC-8: non-members, the wrong workspace or project and
        missing IDs get 404 and nothing changes."""
        cases = [
            (self.carol, self.status_url(self.apollo, self.roadmap, self.task)),
            (self.dave, self.status_url(self.apollo, self.roadmap, self.task)),
            (self.bob, self.status_url(self.apollo, self.launch, self.task)),
            (self.bob, self.status_url(self.hermes, self.roadmap, self.task)),
            (self.bob, self.status_url(self.apollo, self.roadmap, missing_pk(Task))),
        ]
        for user, url in cases:
            with self.subTest(user=user.username, url=url):
                response = self.client_for(user).post(url, {'status': 'done'})
                self.assertEqual(response.status_code, 404)
                self.assertEqual(self.stored(), Task.Status.TODO)

    def test_anonymous_post_not_replayed(self):
        """spec 07 AC-9: an anonymous change goes to login without next, and
        nothing changes."""
        response = self.client_for().post(
            self.status_url(self.apollo, self.roadmap, self.task), {'status': 'done'}
        )
        self.assertRedirects(
            response, reverse('accounts:login'), fetch_redirect_response=False
        )
        self.assertEqual(self.stored(), Task.Status.TODO)

    def test_csrf_and_get_change_nothing(self):
        """spec 07 AC-10: no CSRF token → 403; a GET → 405; no change."""
        url = self.status_url(self.apollo, self.roadmap, self.task)
        client = self.client_for(self.bob, enforce_csrf_checks=True)
        self.assertEqual(client.post(url, {'status': 'done'}).status_code, 403)
        self.assertEqual(
            self.client_for(self.bob).get(url, {'status': 'done'}).status_code, 405
        )
        self.assertEqual(self.stored(), Task.Status.TODO)
