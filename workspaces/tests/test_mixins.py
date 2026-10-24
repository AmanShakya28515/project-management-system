"""MemberWorkspaceMixin tests (spec 05 AC-23, step 04 Q-35).

The mixin is exercised directly through RequestFactory and tiny views, so
these tests pin the shared lookup itself, independent of the project and
task views that use it.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.http import Http404, HttpResponse
from django.test import RequestFactory, TestCase
from django.views import View
from django.views.generic.base import ContextMixin

from workspaces.mixins import MemberWorkspaceMixin
from workspaces.models import Workspace

User = get_user_model()


class _WorkspaceView(MemberWorkspaceMixin, ContextMixin, View):
    handled = False

    def get(self, request, *args, **kwargs):
        type(self).handled = True
        context = self.get_context_data()
        return HttpResponse(context['workspace'].name)


class MemberWorkspaceMixinTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user(username='Alice', password='x')
        cls.bob = User.objects.create_user(username='Bob', password='x')
        cls.carol = User.objects.create_user(username='Carol', password='x')
        cls.dave = User.objects.create_user(username='Dave', password='x')
        cls.apollo = Workspace.objects.create_with_owner('Apollo', cls.alice)
        cls.apollo.add_member(cls.bob)
        cls.hermes = Workspace.objects.create_with_owner('Hermes', cls.carol)

    def setUp(self):
        _WorkspaceView.handled = False

    def call(self, user, workspace_pk):
        request = RequestFactory().get('/x/')
        request.user = user
        return _WorkspaceView.as_view()(request, workspace_pk=workspace_pk)

    def missing_pk(self):
        return Workspace.objects.order_by('-pk').first().pk + 1000

    def test_member_gets_workspace_set_and_in_context(self):
        """spec 05 AC-23: for the owner and a member, the mixin sets
        self.workspace to the URL's workspace and adds it to the context."""
        for user in (self.alice, self.bob):
            with self.subTest(user=user.username):
                response = self.call(user, self.apollo.pk)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.content.decode(), 'Apollo')

    def test_sets_attribute_before_handler(self):
        """spec 05 AC-23: dispatch() resolves the workspace before the
        handler runs, so the handler can rely on self.workspace."""
        view = _WorkspaceView()
        request = RequestFactory().get('/x/')
        request.user = self.bob
        view.setup(request, workspace_pk=self.apollo.pk)
        view.dispatch(request, workspace_pk=self.apollo.pk)
        self.assertEqual(view.workspace, self.apollo)

    def test_non_member_is_404_and_handler_never_runs(self):
        """spec 05 AC-23: a signed-in non-member (Dave, and Carol who owns
        another workspace) gets a 404, and the handler is never reached."""
        for user in (self.dave, self.carol):
            with self.subTest(user=user.username):
                with self.assertRaises(Http404):
                    self.call(user, self.apollo.pk)
                self.assertFalse(_WorkspaceView.handled)

    def test_missing_workspace_is_404(self):
        """spec 05 AC-23: a workspace ID that doesn't exist is a 404, the
        same as for a non-member."""
        with self.assertRaises(Http404):
            self.call(self.bob, self.missing_pk())
        self.assertFalse(_WorkspaceView.handled)

    def test_anonymous_fails_closed(self):
        """spec 05 AC-23: without a login guard in front, an anonymous user
        still gets a 404, never a workspace (for_user is empty for them)."""
        with self.assertRaises(Http404):
            self.call(AnonymousUser(), self.apollo.pk)
        self.assertFalse(_WorkspaceView.handled)
