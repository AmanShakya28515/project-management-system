"""RegistrationForm validation tests (spec 01).

Case-insensitivity tests use ASCII names only (plan 01, D-3).
"""
from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.forms import RegistrationForm

PASSWORD = 'Str0ng-Passw0rd!x'

User = get_user_model()


def form_data(**overrides):
    data = {
        'username': 'newuser',
        'email': 'newuser@example.com',
        'password1': PASSWORD,
        'password2': PASSWORD,
    }
    data.update(overrides)
    return data


class RegistrationFormBaseTests(TestCase):
    def test_form_has_expected_fields(self):
        """AC-1: the form asks for username, email, password, confirmation."""
        form = RegistrationForm()
        self.assertEqual(
            set(form.fields), {'username', 'email', 'password1', 'password2'}
        )
        self.assertTrue(form.fields['email'].required)

    def test_valid_data_creates_user_with_hashed_password(self):
        """AC-2, AC-22: valid data saves a user whose password is hashed."""
        form = RegistrationForm(data=form_data())
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertEqual(user.username, 'newuser')
        self.assertEqual(user.email, 'newuser@example.com')
        self.assertNotEqual(user.password, PASSWORD)
        self.assertTrue(user.check_password(PASSWORD))

    def test_unicode_username_is_accepted(self):
        """AC-2: a Unicode username such as 'José' is valid (D-3)."""
        form = RegistrationForm(
            data=form_data(username='José', email='jose@example.com')
        )
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertEqual(user.username, 'José')


class RegistrationFormUniquenessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User.objects.create_user(
            username='Alice', email='a@x.com', password=PASSWORD
        )

    def test_username_taken_ignoring_case(self):
        """AC-3: 'alice'/'ALICE'/'Alice' rejected on username when 'Alice' exists."""
        for variant in ('alice', 'ALICE', 'Alice'):
            with self.subTest(variant=variant):
                form = RegistrationForm(
                    data=form_data(username=variant, email='other@example.com')
                )
                self.assertFalse(form.is_valid())
                self.assertIn('username', form.errors)
                self.assertNotIn('email', form.errors)
        self.assertEqual(User.objects.count(), 1)

    def test_email_taken_ignoring_case(self):
        """AC-4: 'A@X.com' rejected on email when 'a@x.com' exists."""
        for variant in ('A@X.com', 'a@x.com', 'A@X.COM'):
            with self.subTest(variant=variant):
                form = RegistrationForm(
                    data=form_data(username='bob', email=variant)
                )
                self.assertFalse(form.is_valid())
                self.assertIn('email', form.errors)
                self.assertNotIn('username', form.errors)
        self.assertEqual(User.objects.count(), 1)

    def test_email_with_surrounding_spaces_is_still_a_duplicate(self):
        """AC-4: surrounding whitespace does not bypass the email check."""
        form = RegistrationForm(data=form_data(username='bob', email='  A@x.com  '))
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)


class RegistrationFormRequiredAndFormatTests(TestCase):
    def assert_error_on(self, data, field):
        form = RegistrationForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn(field, form.errors)
        self.assertEqual(User.objects.count(), 0)
        return form

    def test_missing_username(self):
        """AC-5: a missing username is reported on the username field."""
        self.assert_error_on(form_data(username=''), 'username')

    def test_missing_email(self):
        """AC-5: a missing email is reported on the email field."""
        self.assert_error_on(form_data(email=''), 'email')

    def test_invalid_email_format(self):
        """AC-5: an invalid email is reported on the email field."""
        self.assert_error_on(form_data(email='not-an-email'), 'email')

    def test_missing_password1(self):
        """AC-5: a missing password is reported on the password1 field."""
        self.assert_error_on(form_data(password1=''), 'password1')

    def test_missing_password2(self):
        """AC-5: a missing confirmation is reported on the password2 field."""
        self.assert_error_on(form_data(password2=''), 'password2')

    def test_mismatched_passwords(self):
        """AC-5: mismatched passwords are reported on the password2 field."""
        form = self.assert_error_on(
            form_data(password2=PASSWORD + 'x'), 'password2'
        )
        codes = [e.code for e in form.errors.as_data()['password2']]
        self.assertIn('password_mismatch', codes)

    def test_each_problem_reported_on_its_own_field(self):
        """AC-5: several problems at once each appear on their own field."""
        form = RegistrationForm(
            data=form_data(username='', email='bad', password2='different')
        )
        self.assertFalse(form.is_valid())
        for field in ('username', 'email', 'password2'):
            self.assertIn(field, form.errors)


class RegistrationFormWeakPasswordTests(TestCase):
    def assert_rejected_with(self, data, code):
        form = RegistrationForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)
        codes = [e.code for e in form.errors.as_data()['password2']]
        self.assertIn(code, codes)
        # A human-readable reason is given.
        self.assertTrue(all(str(m).strip() for m in form.errors['password2']))
        self.assertEqual(User.objects.count(), 0)

    def test_too_short(self):
        """AC-6: a too-short password is rejected with a reason."""
        self.assert_rejected_with(
            form_data(password1='Xq7!z', password2='Xq7!z'), 'password_too_short'
        )

    def test_too_common(self):
        """AC-6: a common password is rejected with a reason."""
        self.assert_rejected_with(
            form_data(password1='password', password2='password'),
            'password_too_common',
        )

    def test_entirely_numeric(self):
        """AC-6: an all-numeric password is rejected with a reason."""
        self.assert_rejected_with(
            form_data(password1='84739201657', password2='84739201657'),
            'password_entirely_numeric',
        )

    def test_too_similar_to_username(self):
        """AC-6: a password too similar to the username is rejected."""
        self.assert_rejected_with(
            form_data(
                username='marmaladefox',
                password1='marmaladefox1',
                password2='marmaladefox1',
            ),
            'password_too_similar',
        )

    def test_too_similar_to_email(self):
        """AC-6: a password too similar to the email is rejected."""
        self.assert_rejected_with(
            form_data(
                username='someoneelse',
                email='zebracrossing@example.com',
                password1='zebracrossing',
                password2='zebracrossing',
            ),
            'password_too_similar',
        )
