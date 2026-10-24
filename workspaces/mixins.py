from django.shortcuts import get_object_or_404

from .models import Workspace


class MemberWorkspaceMixin:
    """Resolves the URL's workspace for a member, for resources nested under it.

    List it after LoginRequiredNoReplayMixin in the bases, so login is
    checked first. A non-member and a missing workspace get the same 404.
    Nested resources look their children up only inside self.workspace, so a
    child requested under another workspace's ID is a 404 too.

    Subclasses extend resolve_scope() to resolve deeper levels, always after
    calling super(), so the chain runs workspace → project → task.
    """

    def dispatch(self, request, *args, **kwargs):
        self.resolve_scope(**kwargs)
        return super().dispatch(request, *args, **kwargs)

    def resolve_scope(self, **kwargs):
        self.workspace = get_object_or_404(
            Workspace.objects.for_user(self.request.user), pk=kwargs['workspace_pk']
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['workspace'] = self.workspace
        return context
