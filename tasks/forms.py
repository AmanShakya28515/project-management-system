from django import forms

from .models import Task


class TaskForm(forms.ModelForm):
    """Title and optional description (spec 05, OQ-2).

    Both fields strip spaces, so an all-space title fails as required and an
    all-space description saves as ''. The model's max_length values give
    the "at most N characters" errors. The project is never a form field:
    the view sets it from the already-authorised URL scope (AC-19).
    """

    class Meta:
        model = Task
        fields = ('title', 'description')
        labels = {
            'title': 'Task title',
            'description': 'Description (optional)',
        }
        widgets = {
            'title': forms.TextInput(attrs={'autocomplete': 'off'}),
            'description': forms.Textarea(attrs={'rows': 5}),
        }


class TaskStatusForm(forms.ModelForm):
    """Choose one of the three statuses (spec 07). The field has a default and
    isn't blank, so there is no empty choice; any other value is an invalid
    choice and the status is left unchanged (AC-3, AC-6)."""

    class Meta:
        model = Task
        fields = ('status',)
        labels = {'status': 'Status'}


class TaskAssignForm(forms.ModelForm):
    """Choose one assignee, or none (spec 06).

    The choices are limited to the task's workspace's active members, so any
    other submitted user ID (another workspace, inactive, missing) fails as
    an invalid choice and the assignee is left unchanged (AC-7, AC-8).
    """

    class Meta:
        model = Task
        fields = ('assignee',)
        labels = {'assignee': 'Assignee'}

    def __init__(self, *args, workspace, **kwargs):
        super().__init__(*args, **kwargs)
        field = self.fields['assignee']
        field.queryset = workspace.assignable_users()
        field.required = False
        field.empty_label = 'Unassigned'
