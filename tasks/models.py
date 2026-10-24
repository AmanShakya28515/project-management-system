from django.conf import settings
from django.db import models
from django.db.models import Q


class TaskQuerySet(models.QuerySet):
    def in_creation_order(self):
        """Oldest first, by the auto-increment primary key (plan 05, D-3).

        The pk records insertion order and never changes, so a task keeps its
        position as others are added. No timestamp is stored or shown.
        """
        return self.order_by('pk')


class TaskManager(models.Manager.from_queryset(TaskQuerySet)):
    pass


class Task(models.Model):
    """A task inside exactly one project, and so one workspace (spec 05, AC-19).

    Views reach tasks only through `project.tasks`, after the workspace and
    then the project were resolved for a member (MemberProjectMixin).
    Titles may repeat (spec 05, OQ-3), so there is no uniqueness constraint.
    """

    class Status(models.TextChoices):
        """Exactly three statuses (spec 07); any can change to any other."""

        TODO = 'todo', 'To do'
        IN_PROGRESS = 'in_progress', 'In progress'
        DONE = 'done', 'Done'

    # CASCADE: a task can't exist without its project (plan 05, D-2).
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='tasks',
    )
    title = models.CharField(max_length=200)
    description = models.TextField(max_length=2000, blank=True)
    # At most one assignee (spec 06). Only active members of the task's
    # workspace can be chosen; TaskAssignForm enforces that. SET_NULL: deleting
    # the user leaves the task unassigned (plan 06, D-1).
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='assigned_tasks',
    )
    # New and existing tasks start as To do (spec 07, OQ-1).
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.TODO
    )

    objects = TaskManager()

    class Meta:
        constraints = [
            # Only the three statuses can ever be stored (plan 07, D-1).
            models.CheckConstraint(
                condition=Q(status__in=['todo', 'in_progress', 'done']),
                name='tasks_task_status_valid',
            ),
        ]

    def __str__(self):
        return self.title
