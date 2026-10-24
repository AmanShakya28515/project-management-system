"""TaskForm tests for spec 05 (tasks)."""
from django import forms

from tasks.forms import TaskForm

from .data import TaskTestData


class TaskFormTests(TaskTestData):
    def form(self, **data):
        return TaskForm(data=data)

    def test_fields_are_title_and_optional_description(self):
        """spec 05 AC-1 / AC-19: the form asks for a title and an optional
        description, and never for a project or workspace."""
        form = TaskForm()
        self.assertEqual(list(form.fields), ['title', 'description'])
        self.assertTrue(form.fields['title'].required)
        self.assertFalse(form.fields['description'].required)
        self.assertIsInstance(form.fields['description'].widget, forms.Textarea)
        self.assertNotIn('project', form.fields)
        self.assertNotIn('workspace', form.fields)

    def test_valid_with_and_without_description(self):
        """spec 05 AC-2: a valid title is enough; a description is optional."""
        self.assertTrue(self.form(title='Write brief', description='Two pages.').is_valid())
        self.assertTrue(self.form(title='Write brief', description='').is_valid())
        self.assertTrue(self.form(title='Write brief').is_valid())

    def test_empty_or_blank_title_rejected(self):
        """spec 05 AC-3: an empty or all-space title is an error on title."""
        for title in ('', '   '):
            with self.subTest(title=repr(title)):
                form = self.form(title=title, description='x')
                self.assertFalse(form.is_valid())
                self.assertIn('title', form.errors)
                self.assertEqual(form.non_field_errors(), [])

    def test_title_is_trimmed(self):
        """spec 05 AC-3: leading and trailing spaces are removed from the title."""
        form = self.form(title='  Write brief  ')
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['title'], 'Write brief')

    def test_title_length_limit(self):
        """spec 05 AC-4 (OQ-2): 200 characters accepted, 201 rejected with an
        error stating the limit."""
        self.assertTrue(self.form(title='t' * 200).is_valid())
        form = self.form(title='t' * 201)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors['title']), 1)
        self.assertIn('200', form.errors['title'][0])

    def test_description_length_limit(self):
        """spec 05 AC-4 (OQ-2): 2000 characters accepted, 2001 rejected with
        an error stating the limit."""
        self.assertTrue(self.form(title='T', description='d' * 2000).is_valid())
        form = self.form(title='T', description='d' * 2001)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors['description']), 1)
        self.assertIn('2000', form.errors['description'][0].replace(',', ''))
        self.assertNotIn('title', form.errors)

    def test_blank_description_cleaned_to_empty(self):
        """spec 05 AC-5: an empty or all-space description is cleaned to ''."""
        for description in ('', '   ', '  \n  '):
            with self.subTest(description=repr(description)):
                form = self.form(title='T', description=description)
                self.assertTrue(form.is_valid(), form.errors)
                self.assertEqual(form.cleaned_data['description'], '')

    def test_description_is_trimmed(self):
        """spec 05 AC-5 (OQ-2): spaces at the ends of the description are removed."""
        form = self.form(title='T', description='  Two pages.  ')
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['description'], 'Two pages.')

    def test_duplicate_title_is_valid(self):
        """spec 05 AC-6 (OQ-3): a title that already exists in the project is
        still valid."""
        form = self.form(title='Draft outline')
        self.assertTrue(form.is_valid(), form.errors)
