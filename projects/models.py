from django.db import models
from django.db.models import F
from django.db.models.functions import Lower

# Shown by ProjectForm.clean_name and by ProjectCreateView's race path (spec 04,
# AC-5/AC-20). The constraint only uses it via full_clean(); forms never run
# that constraint, so in the app it is the race backstop, not a message source.
DUPLICATE_NAME_MESSAGE = 'This workspace already has a project with that name.'


class ProjectQuerySet(models.QuerySet):
    def alphabetical(self):
        """By name ignoring letter case; pk breaks ties (spec 04, OQ-4)."""
        return self.order_by(Lower('name'), 'pk')


class ProjectManager(models.Manager.from_queryset(ProjectQuerySet)):
    pass


class Project(models.Model):
    """A project inside exactly one workspace (spec 04, AC-19).

    Views reach projects only through `workspace.projects`, after the
    workspace itself was looked up with Workspace.objects.for_user(), so a
    non-member never gets past the workspace lookup.
    """

    # CASCADE: a project can't exist without its workspace (plan 04, D-2).
    workspace = models.ForeignKey(
        'workspaces.Workspace',
        on_delete=models.CASCADE,
        related_name='projects',
    )
    name = models.CharField(max_length=100)
    description = models.TextField(max_length=2000, blank=True)

    objects = ProjectManager()

    class Meta:
        constraints = [
            # Unique per workspace ignoring letter case (spec 04, OQ-3); the
            # same name may be reused in another workspace.
            models.UniqueConstraint(
                F('workspace'),
                Lower('name'),
                name='projects_project_name_ci_unique_per_workspace',
                violation_error_message=DUPLICATE_NAME_MESSAGE,
            ),
        ]

    def __str__(self):
        return self.name
