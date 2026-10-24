from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.views.generic import CreateView, DetailView, FormView
from django.views.generic.detail import SingleObjectMixin

from core.mixins import LoginRequiredNoReplayMixin

from .forms import ALREADY_MEMBER_MESSAGE, AddMemberForm, WorkspaceForm
from .models import Workspace


class WorkspacePageMixin:
    """Members-only lookup and page context, shared by the detail and
    add-member views."""

    def get_queryset(self):
        # Members only: a non-member gets the same 404 as a missing ID, before
        # any owner check runs.
        return Workspace.objects.for_user(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        workspace = self.object
        context['members'] = workspace.member_list()
        context['projects'] = workspace.projects.alphabetical()
        context['viewer_is_owner'] = workspace.is_owner(self.request.user)
        if context['viewer_is_owner'] and 'add_member_form' not in context:
            context['add_member_form'] = AddMemberForm(workspace=workspace)
        return context


class WorkspaceCreateView(LoginRequiredNoReplayMixin, CreateView):
    form_class = WorkspaceForm
    template_name = 'workspaces/workspace_form.html'

    def form_valid(self, form):
        # Always through the manager, so the owner's membership is created too.
        self.object = Workspace.objects.create_with_owner(
            form.cleaned_data['name'], self.request.user
        )
        messages.success(
            self.request, f'Workspace "{self.object.name}" was created.'
        )
        return redirect('workspaces:detail', pk=self.object.pk)


class WorkspaceDetailView(LoginRequiredNoReplayMixin, WorkspacePageMixin, DetailView):
    template_name = 'workspaces/workspace_detail.html'
    context_object_name = 'workspace'
    http_method_names = ['get', 'head', 'options']


class AddMemberView(
    LoginRequiredNoReplayMixin, WorkspacePageMixin, SingleObjectMixin, FormView
):
    """Owner-only, POST-only. Shows the workspace page again on invalid input."""

    form_class = AddMemberForm
    template_name = 'workspaces/workspace_detail.html'
    context_object_name = 'workspace'
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not self.object.is_owner(request.user):
            raise PermissionDenied
        return super().post(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['workspace'] = self.object
        return kwargs

    def form_valid(self, form):
        user = form.user
        _, created = self.object.add_member(user)
        if not created:
            # Someone added the same user between the form check and now.
            form.add_error(
                'username', ALREADY_MEMBER_MESSAGE.format(username=user.username)
            )
            return self.form_invalid(form)
        messages.success(
            self.request, f'{user.username} was added to the workspace.'
        )
        return redirect('workspaces:detail', pk=self.object.pk)

    def form_invalid(self, form):
        return self.render_to_response(
            self.get_context_data(form=form, add_member_form=form)
        )
