"""Model tests for spec 04 (projects)."""
from django.db import IntegrityError, transaction

from projects.models import DUPLICATE_NAME_MESSAGE, Project
from workspaces.models import Membership, Workspace

from .data import ProjectTestData


class ProjectModelTests(ProjectTestData):
    def test_project_belongs_to_its_workspace(self):
        """spec 04 AC-2 / AC-19: a project is stored against exactly one
        workspace and is reachable through workspace.projects."""
        self.assertEqual(self.roadmap.workspace, self.apollo)
        self.assertEqual(list(self.apollo.projects.all()), [self.roadmap])
        self.assertEqual(list(self.hermes.projects.all()), [self.hermes_plan])
        self.assertEqual(str(self.roadmap), 'Roadmap')

    def test_workspace_is_required(self):
        """spec 04 AC-19: a project without a workspace can't be saved."""
        before = Project.objects.count()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Project.objects.create(name='Orphan')
        self.assertEqual(Project.objects.count(), before)
        self.assertFalse(Project._meta.get_field('workspace').null)

    def test_field_limits(self):
        """spec 04 AC-4 (OQ-2): name at most 100, description at most 2000
        and optional."""
        name = Project._meta.get_field('name')
        description = Project._meta.get_field('description')
        self.assertEqual(name.max_length, 100)
        self.assertFalse(name.blank)
        self.assertEqual(description.max_length, 2000)
        self.assertTrue(description.blank)

    def test_duplicate_name_ignoring_case_rejected_by_database(self):
        """spec 04 AC-5 / AC-20: inside transaction.atomic(), a duplicate
        name in the same workspace (any letter case) raises IntegrityError,
        and the database stays usable afterwards."""
        for name in ('roadmap', 'ROADMAP', 'Roadmap'):
            with self.subTest(name=name):
                with self.assertRaises(IntegrityError):
                    with transaction.atomic():
                        Project.objects.create(workspace=self.apollo, name=name)
                self.assertEqual(self.apollo.projects.count(), 1)

    def test_same_name_allowed_in_other_workspace(self):
        """spec 04 AC-5 (OQ-3): the same name may be used in another workspace."""
        project = Project.objects.create(workspace=self.hermes, name='roadmap')
        self.assertEqual(project.workspace, self.hermes)
        self.assertEqual(Project.objects.filter(name__iexact='roadmap').count(), 2)

    def test_constraint_uses_shared_message(self):
        """spec 04 AC-5: the per-workspace constraint carries the shared
        duplicate message."""
        constraints = {c.name: c for c in Project._meta.constraints}
        constraint = constraints['projects_project_name_ci_unique_per_workspace']
        self.assertEqual(constraint.violation_error_message, DUPLICATE_NAME_MESSAGE)

    def test_alphabetical_ignores_case(self):
        """spec 04 AC-7 (OQ-4): alphabetical() orders by name ignoring case."""
        self.roadmap.delete()
        for name in ('gamma', 'Beta', 'alpha'):
            Project.objects.create(workspace=self.apollo, name=name)
        self.assertEqual(
            [p.name for p in self.apollo.projects.alphabetical()],
            ['alpha', 'Beta', 'gamma'],
        )

    def test_deleting_workspace_deletes_its_projects_only(self):
        """spec 04 AC-19 (plan D-2): projects can't outlive their workspace
        (CASCADE); other workspaces' projects are untouched."""
        Membership.objects.filter(workspace=self.apollo).delete()
        Workspace.objects.filter(pk=self.apollo.pk).delete()
        self.assertFalse(Project.objects.filter(pk=self.roadmap.pk).exists())
        self.assertTrue(Project.objects.filter(pk=self.hermes_plan.pk).exists())
