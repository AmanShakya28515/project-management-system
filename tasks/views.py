from django.contrib import messages
from django.shortcuts import redirect
from django.views.generic import CreateView, DetailView, FormView
from django.views.generic.detail import SingleObjectMixin

from core.mixins import LoginRequiredNoReplayMixin
from projects.mixins import MemberProjectMixin

from .forms import TaskAssignForm, TaskForm, TaskStatusForm


class TaskCreateView(LoginRequiredNoReplayMixin, MemberProjectMixin, CreateView):
    """Any workspace member can create a task in a project they can access.

    The project comes only from the authorised URL scope; any posted project
    or workspace value is ignored (spec 05, AC-13/AC-19).
    """

    form_class = TaskForm
    template_name = 'tasks/task_form.html'
    # GET shows the form, POST creates; no PUT/PATCH/DELETE (review S-5).
    http_method_names = ['get', 'head', 'post', 'options']

    def form_valid(self, form):
        form.instance.project = self.project
        self.object = form.save()
        messages.success(self.request, f'Task "{self.object.title}" was created.')
        return redirect(
            'tasks:detail',
            workspace_pk=self.workspace.pk,
            project_pk=self.project.pk,
            pk=self.object.pk,
        )


class TaskPageMixin:
    """Scoped task lookup and task-page context, shared by the detail and
    assign views (like WorkspacePageMixin for the workspace page)."""

    template_name = 'tasks/task_detail.html'
    context_object_name = 'task'

    def get_queryset(self):
        return self.project.tasks.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if 'assign_form' not in context:
            context['assign_form'] = TaskAssignForm(
                instance=self.object, workspace=self.workspace
            )
        if 'status_form' not in context:
            context['status_form'] = TaskStatusForm(instance=self.object)
        return context


class TaskDetailView(
    LoginRequiredNoReplayMixin, MemberProjectMixin, TaskPageMixin, DetailView
):
    http_method_names = ['get', 'head', 'options']


class TaskAssignView(
    LoginRequiredNoReplayMixin,
    MemberProjectMixin,
    TaskPageMixin,
    SingleObjectMixin,
    FormView,
):
    """POST-only assignment (spec 06). Scope is resolved first, so a wrong or
    missing scope is a 404 before the form runs (AC-9)."""

    form_class = TaskAssignForm
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        # Captured before validation: a ModelForm copies the new value onto
        # its instance (this task) while validating.
        self.previous_assignee_id = self.object.assignee_id
        return super().post(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = self.object
        kwargs['workspace'] = self.workspace
        return kwargs

    def form_valid(self, form):
        task = self.object
        new = form.cleaned_data['assignee']
        if (new.pk if new else None) == self.previous_assignee_id:
            if new:
                messages.info(self.request, f'{new.username} is already assigned.')
            else:
                messages.info(self.request, 'This task is already unassigned.')
        else:
            task.assignee = new
            task.save(update_fields=['assignee'])
            if new:
                messages.success(self.request, f'Task assigned to {new.username}.')
            else:
                messages.success(self.request, 'Task is now unassigned.')
        return redirect(
            'tasks:detail',
            workspace_pk=self.workspace.pk,
            project_pk=self.project.pk,
            pk=task.pk,
        )

    def form_invalid(self, form):
        return self.render_to_response(
            self.get_context_data(form=form, assign_form=form)
        )


class TaskStatusView(
    LoginRequiredNoReplayMixin,
    MemberProjectMixin,
    TaskPageMixin,
    SingleObjectMixin,
    FormView,
):
    """POST-only status change (spec 07), built like TaskAssignView: scope
    first (404, AC-8), then the form; only the status is written (AC-7)."""

    form_class = TaskStatusForm
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        # Captured before validation: a ModelForm copies the new value onto
        # its instance (this task) while validating.
        self.previous_status = self.object.status
        return super().post(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = self.object
        return kwargs

    def form_valid(self, form):
        task = self.object
        new = form.cleaned_data['status']
        label = task.Status(new).label
        if new == self.previous_status:
            messages.info(self.request, f'Status is already {label}.')
        else:
            task.status = new
            task.save(update_fields=['status'])
            messages.success(self.request, f'Status changed to {label}.')
        return redirect(
            'tasks:detail',
            workspace_pk=self.workspace.pk,
            project_pk=self.project.pk,
            pk=task.pk,
        )

    def form_invalid(self, form):
        return self.render_to_response(
            self.get_context_data(form=form, status_form=form)
        )
