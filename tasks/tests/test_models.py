"""Model tests for spec 05 (tasks)."""
from django.db import IntegrityError, models, transaction

from projects.models import Project
from tasks.models import Task

from .data import TaskTestData


class TaskModelTests(TaskTestData):
    def test_task_belongs_to_one_project_and_its_workspace(self):
        """spec 05 AC-2 / AC-19: a task is stored against exactly one project
        and so belongs to that project's workspace."""
        self.assertEqual(self.task.project, self.roadmap)
        self.assertEqual(self.task.project.workspace, self.apollo)
        self.assertEqual(list(self.roadmap.tasks.all()), [self.task])
        self.assertEqual(list(self.launch.tasks.all()), [])
        self.assertEqual(list(self.hermes_plan.tasks.all()), [])
        self.assertEqual(str(self.task), 'Draft outline')

    def test_project_is_required(self):
        """spec 05 AC-19: a task without a project can't be saved."""
        before = Task.objects.count()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Task.objects.create(title='Orphan')
        self.assertEqual(Task.objects.count(), before)
        field = Task._meta.get_field('project')
        self.assertFalse(field.null)
        self.assertIs(field.related_model, Project)

    def test_no_separate_workspace_field(self):
        """spec 05 AC-19: the workspace comes only through the project, so
        there is no second, possibly disagreeing, workspace reference."""
        names = {f.name for f in Task._meta.get_fields()}
        self.assertNotIn('workspace', names)

    def test_field_limits(self):
        """spec 05 AC-3 / AC-4 (OQ-2): the title is required and at most 200
        characters; the description is optional and at most 2000."""
        title = Task._meta.get_field('title')
        description = Task._meta.get_field('description')
        self.assertEqual(title.max_length, 200)
        self.assertFalse(title.blank)
        self.assertEqual(description.max_length, 2000)
        self.assertTrue(description.blank)

    def test_duplicate_titles_allowed(self):
        """spec 05 AC-6 (OQ-3): two tasks with the same title, or titles that
        differ only in letter case, can exist in one project."""
        first = Task.objects.create(project=self.roadmap, title='Review')
        second = Task.objects.create(project=self.roadmap, title='Review')
        third = Task.objects.create(project=self.roadmap, title='REVIEW')
        self.assertEqual(len({first.pk, second.pk, third.pk}), 3)
        self.assertEqual(
            self.roadmap.tasks.filter(title__iexact='review').count(), 3
        )
        # Step 07 (plan 07, D-1) deliberately adds a status check constraint;
        # what matters here is that no uniqueness constraint exists.
        from django.db.models import UniqueConstraint
        self.assertFalse(
            [c for c in Task._meta.constraints if isinstance(c, UniqueConstraint)]
        )

    def test_in_creation_order_is_by_pk_not_title(self):
        """spec 05 AC-7 (OQ-4, D-3): in_creation_order() lists tasks oldest
        first, by primary key, never alphabetically; adding a task never
        moves the earlier ones."""
        self.roadmap.tasks.all().delete()
        zeta = Task.objects.create(project=self.roadmap, title='Zeta')
        alpha = Task.objects.create(project=self.roadmap, title='alpha')
        mid = Task.objects.create(project=self.roadmap, title='Mid')
        ordered = list(self.roadmap.tasks.in_creation_order())
        self.assertEqual(ordered, [zeta, alpha, mid])
        self.assertEqual([t.pk for t in ordered], sorted(t.pk for t in ordered))
        self.assertEqual(
            self.roadmap.tasks.in_creation_order().query.order_by, ('pk',)
        )

        beta = Task.objects.create(project=self.roadmap, title='Beta')
        self.assertEqual(
            list(self.roadmap.tasks.in_creation_order()), [zeta, alpha, mid, beta]
        )

    def test_no_timestamp_field(self):
        """spec 05 AC-7 (OQ-4, D-3): no creation date or time is stored, so
        none can be shown."""
        date_fields = [
            f.name for f in Task._meta.get_fields()
            if isinstance(f, (models.DateField, models.TimeField))
        ]
        self.assertEqual(date_fields, [])

    def test_deleting_project_deletes_only_its_tasks(self):
        """spec 05 AC-19 (D-2): deleting a project deletes its own tasks
        (CASCADE) and leaves other projects' tasks alone."""
        launch_task = Task.objects.create(project=self.launch, title='Go live')
        hermes_task = Task.objects.create(project=self.hermes_plan, title='Mail')
        self.roadmap.delete()
        self.assertFalse(Task.objects.filter(pk=self.task.pk).exists())
        self.assertTrue(Task.objects.filter(pk=launch_task.pk).exists())
        self.assertTrue(Task.objects.filter(pk=hermes_task.pk).exists())
