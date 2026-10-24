"""ProjectForm tests for spec 04 (projects)."""
from django import forms

from projects.forms import ProjectForm
from projects.models import DUPLICATE_NAME_MESSAGE

from .data import ProjectTestData


class ProjectFormTests(ProjectTestData):
    def form(self, workspace=None, **data):
        return ProjectForm(data=data, workspace=workspace or self.apollo)

    def test_fields_are_name_and_optional_description(self):
        """spec 04 AC-1: the form asks for a name and an optional
        description, and never for the workspace (spec 04 AC-19)."""
        form = ProjectForm(workspace=self.apollo)
        self.assertEqual(list(form.fields), ['name', 'description'])
        self.assertTrue(form.fields['name'].required)
        self.assertFalse(form.fields['description'].required)
        self.assertIsInstance(form.fields['description'].widget, forms.Textarea)
        self.assertNotIn('workspace', form.fields)

    def test_valid_with_and_without_description(self):
        """spec 04 AC-2: a valid name is enough; a description is optional."""
        self.assertTrue(self.form(name='Launch', description='Go.').is_valid())
        self.assertTrue(self.form(name='Launch', description='').is_valid())
        self.assertTrue(self.form(name='Launch').is_valid())

    def test_empty_or_blank_name_rejected(self):
        """spec 04 AC-3: an empty or all-space name is an error on name."""
        for name in ('', '   '):
            with self.subTest(name=repr(name)):
                form = self.form(name=name)
                self.assertFalse(form.is_valid())
                self.assertIn('name', form.errors)
                self.assertEqual(form.non_field_errors(), [])

    def test_name_is_trimmed(self):
        """spec 04 AC-3: leading and trailing spaces are removed from the name."""
        form = self.form(name='  Launch  ')
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['name'], 'Launch')

    def test_name_length_limit(self):
        """spec 04 AC-4: 100 characters accepted, 101 rejected with the limit."""
        self.assertTrue(self.form(name='a' * 100).is_valid())
        form = self.form(name='a' * 101)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors['name']), 1)
        self.assertIn('100', form.errors['name'][0])

    def test_description_length_limit(self):
        """spec 04 AC-4: 2000 characters accepted, 2001 rejected with the limit."""
        self.assertTrue(self.form(name='Launch', description='d' * 2000).is_valid())
        form = self.form(name='Launch', description='d' * 2001)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors['description']), 1)
        self.assertIn('2000', form.errors['description'][0].replace(',', ''))
        self.assertNotIn('name', form.errors)

    def test_duplicate_name_in_same_workspace_ignoring_case(self):
        """spec 04 AC-5: "Roadmap" exists in Apollo, so "Roadmap", "roadmap",
        "ROADMAP" and "  Roadmap  " give exactly the duplicate error on name."""
        for name in ('Roadmap', 'roadmap', 'ROADMAP', '  Roadmap  '):
            with self.subTest(name=name):
                form = self.form(name=name)
                self.assertFalse(form.is_valid())
                self.assertEqual(form.errors['name'], [DUPLICATE_NAME_MESSAGE])
                self.assertEqual(form.non_field_errors(), [])

    def test_same_name_in_other_workspace_allowed(self):
        """spec 04 AC-5 (OQ-3): "Roadmap" is free in Hermes."""
        form = self.form(workspace=self.hermes, name='Roadmap')
        self.assertTrue(form.is_valid(), form.errors)

    def test_blank_description_saved_empty(self):
        """spec 04 AC-6: an all-space description is cleaned to ''."""
        form = self.form(name='Launch', description='   \n  ')
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['description'], '')

    def test_description_is_trimmed(self):
        """spec 04 AC-6 (OQ-2): spaces at the ends of the description are removed."""
        form = self.form(name='Launch', description='  Go.  ')
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['description'], 'Go.')
