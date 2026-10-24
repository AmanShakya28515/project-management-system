from django import forms
from django.core.exceptions import ValidationError

from .models import DUPLICATE_NAME_MESSAGE, Project


class ProjectForm(forms.ModelForm):
    """Name and optional description (spec 04, OQ-2).

    Both fields strip spaces, so an all-space name fails as required and an
    all-space description saves as ''. The model's max_length values give
    the "at most N characters" errors. The workspace is never a form field:
    the view sets it from the already-authorised workspace (AC-19).
    """

    class Meta:
        model = Project
        fields = ('name', 'description')
        labels = {
            'name': 'Project name',
            'description': 'Description (optional)',
        }
        widgets = {
            'name': forms.TextInput(attrs={'autocomplete': 'off'}),
            'description': forms.Textarea(attrs={'rows': 5}),
        }

    def __init__(self, *args, workspace, **kwargs):
        super().__init__(*args, **kwargs)
        self.workspace = workspace

    def clean_name(self):
        name = self.cleaned_data['name']
        # Form validation never runs the model's F('workspace') constraint
        # (workspace isn't a form field), so this is the only friendly check.
        # The DB constraint plus the view's IntegrityError path catch races.
        if self.workspace.projects.filter(name__iexact=name).exists():
            raise ValidationError(DUPLICATE_NAME_MESSAGE, code='duplicate')
        return name
