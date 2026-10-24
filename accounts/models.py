from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager as DjangoUserManager
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower

# Shared by the model constraints and RegistrationForm so both show the same text.
USERNAME_TAKEN_MESSAGE = 'A user with that username already exists.'
EMAIL_TAKEN_MESSAGE = 'A user with that email already exists.'


class UserManager(DjangoUserManager):
    def get_by_natural_key(self, username):
        # Login matches usernames ignoring letter case (spec 01, AC-9). The
        # case-insensitive unique constraint keeps this to one match on SQLite;
        # on PostgreSQL UPPER/LOWER folding can differ (review finding S-1,
        # deferred to the PostgreSQL step).
        return self.get(**{f'{self.model.USERNAME_FIELD}__iexact': username})


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
