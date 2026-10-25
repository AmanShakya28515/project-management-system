from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager as DjangoUserManager
from django.db import models
from django.db.models import Q, Value
from django.db.models.functions import Lower

# Shared by the model constraints and RegistrationForm so both show the same text.
USERNAME_TAKEN_MESSAGE = 'A user with that username already exists.'
EMAIL_TAKEN_MESSAGE = 'A user with that email already exists.'


class UserManager(DjangoUserManager):
    # Case-insensitive lookups use the same database LOWER() as the unique
    # constraints below, on both sides, so at most one user can ever match.
    # __iexact uses UPPER() on PostgreSQL, which can disagree with LOWER()
    # for some letters such as the dotless ı (finding S-1, plan 09 D-4).
    def filter_username_ci(self, username):
        return self.alias(username_ci=Lower('username')).filter(
            username_ci=Lower(Value(username))
        )

    def filter_email_ci(self, email):
        return self.alias(email_ci=Lower('email')).filter(
            email_ci=Lower(Value(email))
        )

    def get_by_natural_key(self, username):
        # Login matches usernames ignoring letter case (spec 01, AC-9).
        return self.filter_username_ci(username).get()


class User(AbstractUser):
    """Project user. Usernames and emails are unique ignoring letter case,
    while the casing chosen at registration is stored and displayed."""

    objects = UserManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower('username'),
                name='accounts_user_username_ci_unique',
                violation_error_message=USERNAME_TAKEN_MESSAGE,
            ),
            # Blank emails are excluded: createsuperuser allows them.
            models.UniqueConstraint(
                Lower('email'),
                condition=~Q(email=''),
                name='accounts_user_email_ci_unique',
                violation_error_message=EMAIL_TAKEN_MESSAGE,
            ),
        ]
