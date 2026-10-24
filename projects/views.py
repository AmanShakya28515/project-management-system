from django.contrib import messages
from django.db import IntegrityError, transaction
from django.shortcuts import redirect
from django.views.generic import CreateView, DetailView

from core.mixins import LoginRequiredNoReplayMixin
from workspaces.mixins import MemberWorkspaceMixin

from .forms import ProjectForm
from .models import DUPLICATE_NAME_MESSAGE


class ProjectCreateView(LoginRequiredNoReplayMixin, MemberWorkspaceMixin, CreateView):
    """Any workspace member, owner included, can create (spec 04, OQ-1)."""

    form_class = ProjectForm
    template_name = 'projects/project_form.html'
    # GET shows the form, POST creates; no PUT/PATCH/DELETE (review S-5).
    http_method_names = ['get', 'head', 'post', 'options']

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['workspace'] = self.workspace
        return kwargs

    def form_valid(self, form):
        form.instance.workspace = self.workspace
        # The except is outside the atomic block: a duplicate saved between
        # the form check and here rolls the block back first, and only then is
        # the error added, so no query runs in a broken transaction (plan 04, D-3).
        try:
            with transaction.atomic():
                self.object = form.save()
        except IntegrityError:
            # The name constraint is the only expected cause; revisit this if
            # fields or constraints are added to Project.
            form.add_error('name', DUPLICATE_NAME_MESSAGE)
            return self.form_invalid(form)
        messages.success(self.request, f'Project "{self.object.name}" was created.')
        return redirect(
            'projects:detail', workspace_pk=self.workspace.pk, pk=self.object.pk
        )


class ProjectDetailView(LoginRequiredNoReplayMixin, MemberWorkspaceMixin, DetailView):
    template_name = 'projects/project_detail.html'
    context_object_name = 'project'
    http_method_names = ['get', 'head', 'options']

    def get_queryset(self):
        return self.workspace.projects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tasks'] = self.object.tasks.in_creation_order()
        return context
