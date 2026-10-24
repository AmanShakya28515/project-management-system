"""Shared test data for spec 04 (projects). Holds no tests itself.

Alice owns "Apollo" and Bob is a member of it. Carol owns "Hermes". Dave
belongs to no workspace. All names are ASCII (CLAUDE.md: SQLite folds only
ASCII letters for the case-insensitive rules).

Apollo starts with one project, "Roadmap" (two-line description). Hermes
starts with one project, "Hermes Plan". Tests that need other projects
create them; TestCase rolls every test back.
"""
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from projects.models import Project
from workspaces.models import Workspace

PASSWORD = 'Str0ng-Passw0rd!x'

User = get_user_model()


class ProjectTestData(TestCase):
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
            workspace=cls.apollo,
            name='Roadmap',
            description='Plan the launch.\nShip it.',
        )
        cls.hermes_plan = Project.objects.create(
            workspace=cls.hermes, name='Hermes Plan', description='Deliver mail.'
        )

    # ---- helpers ---------------------------------------------------------

    def client_for(self, user=None, **kwargs):
        client = Client(**kwargs)
        if user is not None:
            client.force_login(user)
        return client

    @staticmethod
    def create_url(workspace_or_pk):
        pk = getattr(workspace_or_pk, 'pk', workspace_or_pk)
        return reverse('projects:create', kwargs={'workspace_pk': pk})

    @staticmethod
    def detail_url(workspace_or_pk, project_or_pk):
        ws = getattr(workspace_or_pk, 'pk', workspace_or_pk)
        pk = getattr(project_or_pk, 'pk', project_or_pk)
        return reverse('projects:detail', kwargs={'workspace_pk': ws, 'pk': pk})

    @staticmethod
    def workspace_url(workspace):
        return reverse('workspaces:detail', args=[workspace.pk])

    @staticmethod
    def missing_pk(model):
        last = model.objects.order_by('-pk').first()
        return (last.pk if last else 0) + 1000
