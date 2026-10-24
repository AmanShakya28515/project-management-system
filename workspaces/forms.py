from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from .models import Workspace

# Shared by AddMemberForm and AddMemberView so both show the same text.
USER_NOT_FOUND_MESSAGE = 'No user with that username was found.'
ALREADY_MEMBER_MESSAGE = '{username} is already a member of this workspace.'


class WorkspaceForm(forms.ModelForm):
    """Workspace name only. CharField strips spaces, so all-space names fail
    as required (spec 02, AC-3); the model's max_length gives AC-4."""

    class Meta:
        model = Workspace
        fields = ('name',)
        labels = {'name': 'Workspace name'}
        widgets = {'name': forms.TextInput(attrs={'autocomplete': 'off'})}


class AddMemberForm(forms.Form):
    # Someone else's username, so the browser must not offer the viewer's own
    # (spec 03, AC-13).
    username = forms.CharField(
        max_length=150,
        label='Username',
        widget=forms.TextInput(
            attrs={
                'autocomplete': 'off',
                'autocapitalize': 'none',
                'spellcheck': 'false',
            }
        ),
    )

    def __init__(self, *args, workspace, **kwargs):
        super().__init__(*args, **kwargs)
        self.workspace = workspace
        self.user = None

    def clean_username(self):
        username = self.cleaned_data['username']
        # Letter case is ignored (OQ-2) and inactive accounts can't be added
        # (OQ-3). Anything other than exactly one match counts as not found,
        # so a Unicode case-folding clash (finding S-1) can't cause a 500.
        matches = list(
            get_user_model().objects.filter(
                username__iexact=username, is_active=True
            )[:2]
        )
        if len(matches) != 1:
            raise ValidationError(USER_NOT_FOUND_MESSAGE, code='not_found')
        user = matches[0]
        # The owner is a member too, so this also covers their own name (AC-15).
        if self.workspace.memberships.filter(user=user).exists():
            raise ValidationError(
                ALREADY_MEMBER_MESSAGE.format(username=user.username),
                code='already_member',
            )
        self.user = user
        return username
