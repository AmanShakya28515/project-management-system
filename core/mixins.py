from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect


class LoginRequiredNoReplayMixin(LoginRequiredMixin):
    """LoginRequiredMixin that only remembers the page for GET and HEAD.

    An anonymous form submission is sent to login without `next`, so after
    logging in the user lands on LOGIN_REDIRECT_URL instead of a POST-only
    URL, and the submission is never replayed (spec 02, AC-23). Every other
    case, including raise_exception and logged-in users, keeps Django's own
    handling (403 or login with `next`).
    """

    def handle_no_permission(self):
        if (
            not self.request.user.is_authenticated
            and not self.raise_exception
            and self.request.method not in ('GET', 'HEAD')
        ):
            return redirect(settings.LOGIN_URL)
        return super().handle_no_permission()
