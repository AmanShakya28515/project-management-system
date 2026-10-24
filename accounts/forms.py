from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError

from .models import EMAIL_TAKEN_MESSAGE, USERNAME_TAKEN_MESSAGE, User


class RegistrationForm(UserCreationForm):
    """Sign-up form: username, email, password and confirmation.

    Username and email must be unique ignoring letter case. These checks give
    field-level errors; the model's unique constraints are the backstop.
    """

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].required = True
        self.fields['email'].widget.attrs['autocomplete'] = 'email'

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username and User.objects.filter(username__iexact=username).exists():
            raise ValidationError(USERNAME_TAKEN_MESSAGE, code='unique')
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip()
        if email and User.objects.filter(email__iexact=email).exists():
            raise ValidationError(EMAIL_TAKEN_MESSAGE, code='unique')
        return email
