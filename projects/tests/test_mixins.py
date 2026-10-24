"""MemberProjectMixin tests and the shared-access source check (spec 05
AC-23, step 04 Q-35).

The mixin is exercised directly through RequestFactory and a tiny view. The
source check reads the application code (not the tests) to confirm there is
one workspace lookup, used by every nested view, and no leftover copy.
"""
import ast
from pathlib import Path
from unittest import mock

from django.apps import apps
from django.conf import settings
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.test import RequestFactory, SimpleTestCase
from django.views import View
from django.views.generic.base import ContextMixin

from core.mixins import LoginRequiredNoReplayMixin
from projects.mixins import MemberProjectMixin
from projects.models import Project
from projects.views import ProjectCreateView, ProjectDetailView
from tasks.views import TaskCreateView, TaskDetailView
from workspaces.mixins import MemberWorkspaceMixin
from workspaces.models import Workspace

from .data import ProjectTestData


class _ProjectView(MemberProjectMixin, ContextMixin, View):
    handled = False

    def get(self, request, *args, **kwargs):
        type(self).handled = True
        context = self.get_context_data()
        return HttpResponse('%s/%s' % (context['workspace'].name, context['project'].name))


class MemberProjectMixinTests(ProjectTestData):
    """Alice owns Apollo (Roadmap), Bob is a member; Carol owns Hermes
    (Hermes Plan); Dave belongs to nothing."""

    def setUp(self):
        _ProjectView.handled = False

    def call(self, user, workspace_pk, project_pk):
        request = RequestFactory().get('/x/')
        request.user = user
        return _ProjectView.as_view()(
            request, workspace_pk=workspace_pk, project_pk=project_pk
        )

    def assert_404(self, user, workspace_pk, project_pk):
        with self.assertRaises(Http404):
            self.call(user, workspace_pk, project_pk)
        self.assertFalse(_ProjectView.handled)

    def test_member_gets_workspace_and_project(self):
        """spec 05 AC-23: for a member, the mixin sets self.workspace and
        self.project and adds both to the context."""
        for user in (self.alice, self.bob):
            with self.subTest(user=user.username):
                response = self.call(user, self.apollo.pk, self.roadmap.pk)
                self.assertEqual(response.content.decode(), 'Apollo/Roadmap')

    def test_project_of_another_workspace_is_404(self):
        """spec 05 AC-23: Apollo's ID with Hermes Plan's ID is a 404, even
        for a member of both workspaces."""
        self.assert_404(self.bob, self.apollo.pk, self.hermes_plan.pk)
        self.hermes.add_member(self.bob)
        self.assert_404(self.bob, self.apollo.pk, self.hermes_plan.pk)
        self.assert_404(self.bob, self.hermes.pk, self.roadmap.pk)

    def test_missing_project_is_404(self):
        """spec 05 AC-23: a project ID that doesn't exist is a 404."""
        self.assert_404(self.bob, self.apollo.pk, self.missing_pk(Project))

    def test_non_member_or_missing_workspace_is_404(self):
        """spec 05 AC-23: a non-member, or a missing workspace, is a 404
        even when the project ID is real."""
        self.assert_404(self.dave, self.apollo.pk, self.roadmap.pk)
        self.assert_404(self.carol, self.apollo.pk, self.roadmap.pk)
        self.assert_404(self.bob, self.missing_pk(Workspace), self.roadmap.pk)

    def test_workspace_resolved_before_project(self):
        """spec 05 AC-23: the workspace is resolved first; the project is
        then looked up only inside that workspace's projects, and never at
        all when the workspace lookup fails."""
        calls = []

        def recording(queryset, **kwargs):
            calls.append((queryset.model, list(queryset), kwargs))
            return get_object_or_404(queryset, **kwargs)

        with mock.patch('projects.mixins.get_object_or_404', side_effect=recording):
            self.call(self.bob, self.apollo.pk, self.roadmap.pk)
        self.assertEqual(len(calls), 1)
        model, scope, kwargs = calls[0]
        self.assertIs(model, Project)
        self.assertEqual(scope, list(self.apollo.projects.all()))
        self.assertEqual(kwargs, {'pk': self.roadmap.pk})

        calls.clear()
        with mock.patch('projects.mixins.get_object_or_404', side_effect=recording):
            with self.assertRaises(Http404):
                self.call(self.dave, self.apollo.pk, self.roadmap.pk)
        self.assertEqual(calls, [])

    def test_extends_member_workspace_mixin(self):
        """spec 05 AC-23: MemberProjectMixin builds on the single workspace
        lookup rather than copying it."""
        self.assertTrue(issubclass(MemberProjectMixin, MemberWorkspaceMixin))
        self.assertNotIn('dispatch', vars(MemberProjectMixin))


def _app_python_files():
    """Application .py files of every local app (tests and migrations
    excluded)."""
    base = Path(settings.BASE_DIR).resolve()
    files = []
    for config in apps.get_app_configs():
        root = Path(config.path).resolve()
        if base not in root.parents:
            continue
        for path in root.rglob('*.py'):
            parts = path.relative_to(root).parts
            if parts[0] in ('tests', 'migrations'):
                continue
            files.append(path)
    return base, files


def _for_user_calls(path):
    """(enclosing class or function name, line) for each `.for_user(` call."""
    tree = ast.parse(path.read_text(encoding='utf-8'))
    found = []

    def visit(node, owner):
        for child in ast.iter_child_nodes(node):
            name = owner
            if isinstance(child, ast.ClassDef):
                name = child.name
            if (
                isinstance(child, ast.Call)
                and isinstance(child.func, ast.Attribute)
                and child.func.attr == 'for_user'
            ):
                found.append((owner, child.lineno))
            visit(child, name)

    visit(tree, None)
    return found


class SharedAccessSourceTests(SimpleTestCase):
    def test_no_project_workspace_mixin_left(self):
        """spec 05 AC-23 (Q-35): the old ProjectWorkspaceMixin is gone from
        the application code."""
        base, files = _app_python_files()
        self.assertTrue(files)
        for path in files:
            with self.subTest(file=str(path.relative_to(base))):
                self.assertNotIn(
                    'ProjectWorkspaceMixin', path.read_text(encoding='utf-8')
                )

    def test_for_user_lookups_only_in_the_two_shared_mixins(self):
        """spec 05 AC-23 (Q-35): views look a workspace up with
        Workspace.objects.for_user only in WorkspacePageMixin (the workspace's
        own pages) and MemberWorkspaceMixin (everything nested under it).

        The dashboard's DashboardView also calls for_user, but only to list
        the user's own workspaces (step 02), not to resolve a URL's scope; it
        is allowed by name so any new caller still fails this test."""
        base, files = _app_python_files()
        allowed = {
            ('workspaces/views.py', 'WorkspacePageMixin'),
            ('workspaces/mixins.py', 'MemberWorkspaceMixin'),
            ('core/views.py', 'DashboardView'),
        }
        seen = set()
        for path in files:
            relative = path.relative_to(base).as_posix()
            for owner, line in _for_user_calls(path):
                with self.subTest(file=relative, line=line):
                    self.assertIn((relative, owner), allowed)
                seen.add((relative, owner))
        self.assertIn(('workspaces/views.py', 'WorkspacePageMixin'), seen)
        self.assertIn(('workspaces/mixins.py', 'MemberWorkspaceMixin'), seen)

    def test_nested_views_have_no_unscoped_lookups(self):
        """spec 05 AC-23 / AC-13: project and task views and mixins never
        query Workspace, Project or Task directly; they go through the
        resolved parent (self.workspace.projects, self.project.tasks)."""
        base = Path(settings.BASE_DIR)
        for relative in (
            'projects/views.py', 'projects/mixins.py',
            'tasks/views.py', 'workspaces/mixins.py',
        ):
            source = (base / relative).read_text(encoding='utf-8')
            with self.subTest(file=relative):
                self.assertNotIn('Project.objects', source)
                self.assertNotIn('Task.objects', source)
                if relative != 'workspaces/mixins.py':
                    self.assertNotIn('Workspace.objects', source)

    def test_views_check_login_before_scope(self):
        """spec 05 AC-23 / AC-15: every nested view lists
        LoginRequiredNoReplayMixin before the member mixin, so login is
        checked before any lookup."""
        cases = (
            (ProjectCreateView, MemberWorkspaceMixin),
            (ProjectDetailView, MemberWorkspaceMixin),
            (TaskCreateView, MemberProjectMixin),
            (TaskDetailView, MemberProjectMixin),
        )
        for view, member_mixin in cases:
            with self.subTest(view=view.__name__):
                mro = view.__mro__
                self.assertIn(member_mixin, mro)
                self.assertLess(
                    mro.index(LoginRequiredNoReplayMixin), mro.index(member_mixin)
                )
