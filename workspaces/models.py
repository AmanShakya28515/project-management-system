from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models, transaction
from django.db.models import Case, IntegerField, Value, When
from django.db.models.functions import Lower


class WorkspaceQuerySet(models.QuerySet):
    def for_user(self, user):
        """Workspaces the user is a member of (owners are members too).

        Every workspace view looks objects up through this, so a missing
        membership fails closed as a 404.
        """
        if not user.is_authenticated:
            return self.none()
        # No distinct() needed: the membership constraint allows one row per user.
        return self.filter(memberships__user=user)


class WorkspaceManager(models.Manager.from_queryset(WorkspaceQuerySet)):
    def create_with_owner(self, name, owner):
        """Create a workspace and its owner's membership together (spec 02, AC-27)."""
        with transaction.atomic():
            workspace = self.create(name=name, owner=owner)
            Membership.objects.create(workspace=workspace, user=owner)
        return workspace


class Workspace(models.Model):
    """A shared space with one owner and any number of members.

    `owner` is the only record of ownership. The owner also has a Membership
    row, which `create_with_owner` guarantees.
    """

    name = models.CharField(max_length=100)
    # PROTECT: deleting a user who owns a workspace is refused (plan 02, D-1).
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='owned_workspaces',
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='Membership',
        related_name='workspaces',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects = WorkspaceManager()

    def __str__(self):
        return self.name

    def is_owner(self, user):
        return user.pk == self.owner_id

    def add_member(self, user):
        """Add `user` once. Returns (membership, created).

        get_or_create also handles two simultaneous adds: the second one's
        IntegrityError is caught and the existing row is returned.
        """
        return Membership.objects.get_or_create(workspace=self, user=user)

    def assignable_users(self):
        """Active users who are members here, owner first, then by username
        ignoring case (spec 06, OQ-1). The only users a task can be assigned to."""
        return (
            get_user_model()
            .objects.filter(workspace_memberships__workspace=self, is_active=True)
            .annotate(
                is_workspace_owner=Case(
                    When(pk=self.owner_id, then=Value(1)),
                    default=Value(0),
                    output_field=IntegerField(),
                )
            )
            .order_by('-is_workspace_owner', Lower('username'), 'pk')
        )

    def member_list(self):
        """Memberships with users: owner first, then by username ignoring case.

        Each row is annotated with `is_workspace_owner`, which the template
        uses for the Owner/Member label, so the rule lives only here.
        """
        return (
            self.memberships.select_related('user')
            .annotate(
                is_workspace_owner=Case(
                    When(user_id=self.owner_id, then=Value(1)),
                    default=Value(0),
                    output_field=IntegerField(),
                )
            )
            .order_by('-is_workspace_owner', Lower('user__username'), 'user_id')
        )


class Membership(models.Model):
    workspace = models.ForeignKey(
        Workspace, on_delete=models.CASCADE, related_name='memberships'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='workspace_memberships',
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['workspace', 'user'],
                name='workspaces_membership_unique_user',
            ),
        ]

    def __str__(self):
        return f'{self.user} in {self.workspace}'
