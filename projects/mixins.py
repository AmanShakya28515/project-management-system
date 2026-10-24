from django.shortcuts import get_object_or_404

from workspaces.mixins import MemberWorkspaceMixin


class MemberProjectMixin(MemberWorkspaceMixin):
    """Resolves the workspace, then the project inside it, for a member.

    List it after LoginRequiredNoReplayMixin in the bases. The project is
    looked up only inside the already-authorised workspace, so a project from
    another workspace, or a missing one, is the same 404 as a non-member.
    """

    def resolve_scope(self, **kwargs):
        super().resolve_scope(**kwargs)
        self.project = get_object_or_404(
            self.workspace.projects.all(), pk=kwargs['project_pk']
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.project
        return context
