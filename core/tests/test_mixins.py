"""LoginRequiredNoReplayMixin tests (spec 02 AC-22/AC-23, review Q-6).

The mixin is exercised directly through RequestFactory and a tiny view class,
so these tests don't depend on any particular workspace view.
"""
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import resolve_url
from django.test import RequestFactory, TestCase
from django.views import View

from core.mixins import LoginRequiredNoReplayMixin


class _ProtectedView(LoginRequiredNoReplayMixin, View):
    def get(self, request):
        return HttpResponse('ok')

    def post(self, request):
        return HttpResponse('ok')


class _RaisingView(_ProtectedView):
    raise_exception = True


PATH = '/some/protected/path/'


class LoginRequiredNoReplayMixinTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.login_url = resolve_url(settings.LOGIN_URL)

    def _anon(self, request):
        request.user = AnonymousUser()
        return request

    def test_anonymous_get_redirects_with_next(self):
        """spec 02 AC-22 (review Q-6): anonymous GET → login with ?next=<path>."""
        request = self._anon(self.factory.get(PATH))
        response = _ProtectedView.as_view()(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response['Location'], '%s?next=%s' % (self.login_url, PATH)
        )

    def test_anonymous_head_redirects_with_next(self):
        """spec 02 AC-22 (review Q-6): anonymous HEAD keeps ?next= like GET."""
        request = self._anon(self.factory.head(PATH))
        response = _ProtectedView.as_view()(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response['Location'], '%s?next=%s' % (self.login_url, PATH)
        )

    def test_anonymous_post_redirects_to_plain_login(self):
        """spec 02 AC-23 (review Q-6): anonymous POST → exactly the login URL, no next."""
        request = self._anon(self.factory.post(PATH, {'x': '1'}))
        response = _ProtectedView.as_view()(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], self.login_url)
        self.assertNotIn('next', response['Location'])

    def test_raise_exception_anonymous_post_is_permission_denied(self):
        """spec 02 AC-23 (review Q-6): raise_exception=True → POST raises PermissionDenied, no redirect."""
        request = self._anon(self.factory.post(PATH, {'x': '1'}))
        with self.assertRaises(PermissionDenied):
            _RaisingView.as_view()(request)

    def test_raise_exception_anonymous_get_is_permission_denied(self):
        """spec 02 AC-22 (review Q-6): raise_exception=True → GET also raises PermissionDenied."""
        request = self._anon(self.factory.get(PATH))
        with self.assertRaises(PermissionDenied):
            _RaisingView.as_view()(request)
