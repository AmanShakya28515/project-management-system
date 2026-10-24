from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models.functions import Lower
from django.shortcuts import resolve_url
from django.views.generic import RedirectView, TemplateView

from workspaces.models import Workspace


class HomeRedirectView(RedirectView):
    """Site root: logged-in users go to the dashboard, everyone else to login."""

    def get_redirect_url(self, *args, **kwargs):
        if self.request.user.is_authenticated:
            return resolve_url(settings.LOGIN_REDIRECT_URL)
        return resolve_url(settings.LOGIN_URL)


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'core/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['workspaces'] = Workspace.objects.for_user(
            self.request.user
        ).order_by(Lower('name'), 'pk')
        return context
