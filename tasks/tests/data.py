"""Shared test data for spec 05 (tasks). Holds no tests itself.

Alice owns "Apollo" and Bob is a member of it. Carol owns "Hermes". Dave
belongs to no workspace. Apollo has the projects "Roadmap" and "Launch";
Hermes has "Hermes Plan". All names are ASCII (CLAUDE.md: SQLite folds only
ASCII letters).

Roadmap starts with one task, "Draft outline" (two-line description), so
the Roadmap page has a tasks list. Launch and Hermes Plan start with no
tasks. Tests that need other tasks create them; TestCase rolls each test
back.
"""
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from projects.models import Project
from tasks.models import Task
from workspaces.models import Workspace

PASSWORD = 'Str0ng-Passw0rd!x'

User = get_user_model()


def pk_of(obj_or_pk):
    return getattr(obj_or_pk, 'pk', obj_or_pk)


def missing_pk(model):
    """An ID no row of `model` has."""
    last = model.objects.order_by('-pk').first()
    return (last.pk if last else 0) + 1000


class TaskTestData(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user(
            username='Alice', email='alice@example.com', password=PASSWORD
        )
        cls.bob = User.objects.create_user(
            username='Bob', email='bob@example.com', password=PASSWORD
        )
        cls.carol = User.objects.create_user(
            username='Carol', email='carol@example.com', password=PASSWORD
        )
        cls.dave = User.objects.create_user(
            username='Dave', email='dave@example.com', password=PASSWORD
        )
        cls.apollo = Workspace.objects.create_with_owner('Apollo', cls.alice)
        cls.apollo.add_member(cls.bob)
        cls.hermes = Workspace.objects.create_with_owner('Hermes', cls.carol)
        cls.roadmap = Project.objects.create(
            workspace=cls.apollo, name='Roadmap', description='Plan the work.'
        )
        cls.launch = Project.objects.create(workspace=cls.apollo, name='Launch')
        cls.hermes_plan = Project.objects.create(
            workspace=cls.hermes, name='Hermes Plan'
        )
        cls.task = Task.objects.create(
            project=cls.roadmap,
            title='Draft outline',
            description='First line.\nSecond line.',
        )

    # ---- helpers ---------------------------------------------------------

    def client_for(self, user=None, **kwargs):
        client = Client(**kwargs)
        if user is not None:
            client.force_login(user)
        return client

    @staticmethod
    def create_url(workspace, project):
        return reverse(
            'tasks:create',
            kwargs={'workspace_pk': pk_of(workspace), 'project_pk': pk_of(project)},
        )

    @staticmethod
    def detail_url(workspace, project, task):
        return reverse(
            'tasks:detail',
            kwargs={
                'workspace_pk': pk_of(workspace),
                'project_pk': pk_of(project),
                'pk': pk_of(task),
            },
        )

    @staticmethod
    def project_url(workspace, project):
        return reverse(
            'projects:detail',
            kwargs={'workspace_pk': pk_of(workspace), 'pk': pk_of(project)},
        )

    @staticmethod
    def workspace_url(workspace):
        return reverse('workspaces:detail', args=[pk_of(workspace)])
