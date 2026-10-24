from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LogoutView
from django.shortcuts import redirect, resolve_url
from django.views.generic import FormView

from .forms import RegistrationForm


class RegisterView(FormView):
    """Create an account and log the new user straight in.

    Deliberately ignores any `next` parameter: only LoginView handles
    return-to redirects, so there is a single place that validates them.
    """

    template_name = 'accounts/register.html'
    form_class = RegistrationForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(settings.LOGIN_REDIRECT_URL)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        messages.success(
            self.request,
            f'Welcome, {user.username}! Your account has been created.',
        )
        return super().form_valid(form)

    def get_success_url(self):
        return resolve_url(settings.LOGIN_REDIRECT_URL)


class LogoutWithMessageView(LogoutView):
    """POST-only logout (Django's LogoutView) that confirms with a message."""

    def post(self, request, *args, **kwargs):
        # Log out first: this flushes the session. The message is queued
        # afterwards so it lives in the post-logout request state.
        response = super().post(request, *args, **kwargs)
        messages.info(request, 'You have been logged out.')
        return response
