"""UI refresh tests (spec 03).

These check every acceptance criterion of spec 03 that can be seen in the
rendered HTML, the base template's style block or the design-system document.
Layout at real screen widths (AC-9, AC-23), measured target sizes (AC-21) and
the build notes (AC-2) are checked by hand / at review, per plan 03 D-1; only
their HTML-observable parts are tested here.

Page matrix: login and register (anonymous); dashboard with and without
workspaces; create workspace; workspace detail as owner and as member.

HTML is parsed with the stdlib html.parser into a small tree, so the tests
don't depend on attribute order or whitespace. The parser and CSS helpers
live in core/tests/helpers.py (step 05 Q-46).
"""
import re

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from accounts.forms import RegistrationForm
from workspaces.models import Workspace

# The HTML tree and CSS helpers are shared with the projects and tasks UI
# tests, so they live in a non-test module (step 05 Q-46).
from .helpers import (
    BASE_TEMPLATE,
    FOCUSABLE_TAGS,
    HEX_COLOUR,
    PALETTE_CLASS,
    TAILWIND_CDN,
    Node,
    apply_rules,
    base_source,
    by_id,
    component_rules,
    css_block,
    effective_min_h,
    in_nav,
    local_template_dirs,
    main_of,
    ordered_apply_rules,
    parse,
    specificity,
    strip_comments,
    subject_type,
    tailwind_css,
    theme_tokens,
)

PASSWORD = 'Str0ng-Passw0rd!x'
MASTER_PATH = (
    settings.BASE_DIR / 'design-system' / 'project-management-system' / 'MASTER.md'
)

User = get_user_model()


# --------------------------------------------------------------------------
# WCAG contrast
# --------------------------------------------------------------------------

def relative_luminance(hex_colour):
    hex_colour = hex_colour.lstrip('#')
    channels = []
    for i in (0, 2, 4):
        c = int(hex_colour[i:i + 2], 16) / 255
        channels.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    r, g, b = channels
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(fg, bg):
    l1, l2 = sorted((relative_luminance(fg), relative_luminance(bg)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


# Text pairs need 4.5:1; interface parts and focus indicators need 3:1.
TEXT_PAIRS = [
    ('ink', 'canvas'), ('ink', 'surface'),
    ('ink-soft', 'surface'), ('ink-soft', 'subtle'),
    ('muted', 'surface'), ('muted', 'canvas'),
    ('link', 'surface'), ('link', 'canvas'), ('link', 'subtle'),
    ('primary', 'surface'),  # current-page nav link text
    ('on-primary', 'primary'), ('on-primary', 'primary-hover'),
    ('danger', 'surface'),
    ('success-fg', 'success-bg'), ('info-fg', 'info-bg'),
    ('warning-fg', 'warning-bg'), ('danger-fg', 'danger-bg'),
    ('owner-fg', 'owner-bg'), ('member-fg', 'member-bg'),
]
UI_PAIRS = [
    ('line-strong', 'surface'),
    ('ring', 'surface'), ('ring', 'canvas'),
    ('primary', 'surface'), ('primary', 'canvas'),
    ('danger', 'surface'),  # invalid-input border
]


# --------------------------------------------------------------------------
# Shared data and the page matrix
# --------------------------------------------------------------------------

class UITestData(TestCase):
    """Alice owns Apollo (Bob is a member); Carol has no workspaces."""

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
        cls.hermes = Workspace.objects.create_with_owner('Hermes', cls.alice)

    def client_for(self, user=None):
        client = Client()
        if user is not None:
            client.force_login(user)
        return client

    def get(self, url, user=None):
        response = self.client_for(user).get(url)
        self.assertEqual(response.status_code, 200, url)
        return response

    def pages(self):
        """name -> response for every page in the matrix."""
        detail = reverse('workspaces:detail', args=[self.apollo.pk])
        return {
            'login': self.get(reverse('accounts:login')),
            'register': self.get(reverse('accounts:register')),
            'dashboard': self.get(reverse('core:dashboard'), self.alice),
            'dashboard_empty': self.get(reverse('core:dashboard'), self.carol),
            'create': self.get(reverse('workspaces:create'), self.alice),
            'detail_owner': self.get(detail, self.alice),
            'detail_member': self.get(detail, self.bob),
        }

    def parsed_pages(self):
        return {name: parse(r) for name, r in self.pages().items()}


# --------------------------------------------------------------------------
# AC-1: design-system document
# --------------------------------------------------------------------------

class DesignSystemDocumentTests(TestCase):
    def test_master_file_exists_with_project_adjustments(self):
        """spec 03 AC-1: MASTER.md exists at the required location and has
        the "Project adjustments (step 03)" section."""
        self.assertTrue(MASTER_PATH.is_file(), MASTER_PATH)
        text = MASTER_PATH.read_text(encoding='utf-8')
        self.assertRegex(text, r'(?m)^#+ Project adjustments \(step 03\)\s*$')

    def test_adjustments_cover_required_topics(self):
        """spec 03 AC-1: the adjustments state palette and contrast pairs,
        font stack and type scale, spacing and radius, button, form-field,
        card, message and badge styles, and focus rules."""
        text = MASTER_PATH.read_text(encoding='utf-8')
        adjustments = text.split('Project adjustments (step 03)', 1)[1]
        for needle in (
            'Semantic tokens', 'Contrast', 'Font stack', 'system-ui',
            'Scale', 'Spacing', 'Radius', 'Buttons', 'Form fields', 'Cards',
            'Messages', 'Badges', 'Focus',
        ):
            with self.subTest(needle=needle):
                self.assertIn(needle, adjustments)
        # The palette keeps the indigo identity (indigo-600 primary).
        self.assertIn('#4F46E5', adjustments)


# --------------------------------------------------------------------------
# AC-3, AC-4, AC-5: consistency
# --------------------------------------------------------------------------

class ConsistencyTests(UITestData):
    def test_every_page_shares_header_nav_main_and_card(self):
        """spec 03 AC-3: every page has the same <header> holding
        <nav aria-label="Main">, a <main id="main"> and .card panels."""
        for name, root in self.parsed_pages().items():
            with self.subTest(page=name):
                headers = root.find_all('header')
                self.assertEqual(len(headers), 1)
                navs = root.find_all('nav')
                self.assertEqual(len(navs), 1)
                self.assertEqual(navs[0].attrs.get('aria-label'), 'Main')
                self.assertIs(navs[0].parent, headers[0])
                main = main_of(root)
                self.assertEqual(main.attrs.get('id'), 'main')
                self.assertIn('max-w-5xl', main.classes)
                self.assertTrue(main.find(class_='card'), 'no .card in <main>')

    def test_templates_use_tokens_not_palette_classes_or_raw_hex(self):
        """spec 03 AC-3 / AC-4: no template uses Tailwind palette colour
        classes (e.g. bg-indigo-600) or raw hex colours outside @theme.

        Spec 05 AC-23 (step 04 Q-46): the scan covers the shared templates
        folder plus every local app in INSTALLED_APPS that has a templates
        folder, so new apps (projects, tasks) are checked automatically."""
        base = settings.BASE_DIR
        app_dirs = local_template_dirs()
        scanned_apps = {d.parent.name for d in app_dirs}
        self.assertLessEqual(
            {'accounts', 'core', 'workspaces', 'projects', 'tasks'}, scanned_apps
        )
        templates = list((base / 'templates').rglob('*.html'))
        for directory in app_dirs:
            templates += list(directory.rglob('*.html'))
        self.assertTrue(templates)
        for path in templates:
            source = path.read_text(encoding='utf-8')
            if path == BASE_TEMPLATE:
                theme = css_block(tailwind_css(), '@theme')
                source = source.replace(theme, '')
            with self.subTest(template=str(path.relative_to(base))):
                self.assertEqual(PALETTE_CLASS.findall(source), [])
                self.assertEqual(HEX_COLOUR.findall(source), [])

    def test_every_submit_button_uses_shared_button_class(self):
        """spec 03 AC-4: every submit button (including nav "Log out")
        carries btn-primary or btn-secondary."""
        for name, root in self.parsed_pages().items():
            buttons = [
                b for b in root.find_all('button')
                if b.attrs.get('type', 'submit') == 'submit'
            ]
            with self.subTest(page=name):
                self.assertTrue(buttons, 'expected at least one submit button')
                for button in buttons:
                    self.assertTrue(
                        {'btn-primary', 'btn-secondary'} & set(button.classes),
                        button,
                    )

    def test_nav_register_and_logout_use_shared_button_classes(self):
        """spec 03 AC-4: nav "Register" is .btn-primary and nav "Log out"
        is .btn-secondary, the same classes as the page buttons."""
        pages = self.parsed_pages()
        nav = pages['login'].find('nav')
        register = [a for a in nav.find_all('a') if a.norm_text() == 'Register']
        self.assertEqual(len(register), 1)
        self.assertIn('btn-primary', register[0].classes)

        nav = pages['dashboard'].find('nav')
        logout = [b for b in nav.find_all('button') if b.norm_text() == 'Log out']
        self.assertEqual(len(logout), 1)
        self.assertIn('btn-secondary', logout[0].classes)

    def test_button_rules_live_in_components_layer(self):
        """spec 03 AC-4 (Q-11): .btn-primary and .btn-secondary are defined
        only inside @layer components, with one shared base."""
        css = tailwind_css()
        components = css_block(css, '@layer components')
        outside = css.replace(components, '')
        self.assertNotIn('.btn-primary', outside)
        self.assertNotIn('.btn-secondary', outside)
        rules = apply_rules(components)
        primary, secondary = rules['.btn-primary'], rules['.btn-secondary']
        shared = {'inline-flex', 'min-h-11', 'rounded-lg', 'px-4', 'text-sm',
                  'font-semibold'}
        self.assertLessEqual(shared, primary)
        self.assertLessEqual(shared, secondary)

    def test_page_override_applies_on_top_of_shared_button(self):
        """spec 03 AC-4: a page-level change (full width on login/register)
        is a utility next to the shared class, not a separate style."""
        pages = self.parsed_pages()
        for name in ('login', 'register'):
            button = main_of(pages[name]).find('button', type='submit')
            with self.subTest(page=name):
                self.assertIn('btn-primary', button.classes)
                self.assertIn('w-full', button.classes)

    def test_system_font_stack_and_no_downloaded_fonts(self):
        """spec 03 AC-5: --font-sans is a system stack, body text is 16px
        with comfortable line height, and nothing loads a font."""
        theme = css_block(tailwind_css(), '@theme')
        match = re.search(r'--font-sans:\s*([^;]+);', theme)
        self.assertIsNotNone(match)
        stack = match.group(1)
        self.assertTrue(stack.startswith('ui-sans-serif, system-ui'), stack)
        self.assertTrue(stack.rstrip().endswith('sans-serif'), stack)
        base_rules = apply_rules(css_block(tailwind_css(), '@layer base'))
        body = base_rules['body']
        self.assertIn('font-sans', body)
        self.assertIn('text-base', body)
        self.assertTrue({'leading-normal', 'leading-relaxed'} & body)
        for name, response in self.pages().items():
            html = response.content.decode()
            with self.subTest(page=name):
                self.assertNotIn('fonts.googleapis', html)
                self.assertNotIn('fonts.gstatic', html)
                self.assertNotIn('@import url(', html)
                self.assertNotIn('@font-face', html)


# --------------------------------------------------------------------------
# AC-7, AC-8, AC-9: navigation
# --------------------------------------------------------------------------

class NavigationTests(UITestData):
    def test_current_page_marked_with_aria_current(self):
        """spec 03 AC-7: exactly one aria-current="page" on the matching nav
        link; none on the workspace pages."""
        expected = {
            'login': 'Log in',
            'register': 'Register',
            'dashboard': 'Dashboard',
            'dashboard_empty': 'Dashboard',
            'create': None,
            'detail_owner': None,
            'detail_member': None,
        }
        for name, root in self.parsed_pages().items():
            current = [n for n in root.iter() if 'aria-current' in n.attrs]
            with self.subTest(page=name):
                if expected[name] is None:
                    self.assertEqual(current, [])
                else:
                    self.assertEqual(len(current), 1)
                    self.assertEqual(current[0].attrs['aria-current'], 'page')
                    self.assertEqual(current[0].tag, 'a')
                    self.assertTrue(in_nav(current[0]))
                    self.assertEqual(current[0].norm_text(), expected[name])

    def test_current_page_has_visual_marker(self):
        """spec 03 AC-7: the current link is also marked visually (an
        underline rule keyed on aria-current)."""
        rules = component_rules()
        self.assertIn('underline', rules['.nav-link[aria-current="page"]'])
        self.assertIn('underline', rules['.btn-primary[aria-current="page"]'])

    def test_skip_link_is_first_focusable_element(self):
        """spec 03 AC-8: the first focusable element in <body> is the
        "Skip to main content" link to #main; <main id="main" tabindex="-1">
        receives focus; the link is visible while focused."""
        for name, root in self.parsed_pages().items():
            body = root.find('body')
            focusable = [
                n for n in body.iter()
                if n.tag in FOCUSABLE_TAGS
                and not (n.tag == 'input' and n.attrs.get('type') == 'hidden')
                and not (n.tag == 'a' and 'href' not in n.attrs)
            ]
            with self.subTest(page=name):
                first = focusable[0]
                self.assertEqual(first.tag, 'a')
                self.assertEqual(first.attrs.get('href'), '#main')
                self.assertEqual(first.norm_text(), 'Skip to main content')
                self.assertFalse(in_nav(first))
                main = by_id(root, 'main')
                self.assertIsNotNone(main)
                self.assertEqual(main.tag, 'main')
                self.assertEqual(main.attrs.get('tabindex'), '-1')
        skip = component_rules()['.skip-link']
        self.assertIn('sr-only', skip)
        self.assertIn('focus:not-sr-only', skip)

    def test_viewport_meta_and_wrapping_nav(self):
        """spec 03 AC-9 / AC-23 (HTML part): viewport meta is present and
        the nav wraps with flex-wrap; no item is hidden per breakpoint and
        no menu script is added."""
        for name, root in self.parsed_pages().items():
            with self.subTest(page=name):
                meta = root.find('meta', name='viewport')
                self.assertIsNotNone(meta)
                self.assertIn('width=device-width', meta.attrs.get('content', ''))
                nav = root.find('nav')
                self.assertIn('flex-wrap', nav.classes)
                for node in [nav, *nav.iter()]:
                    for token in node.classes:
                        self.assertFalse(
                            token == 'hidden' or token.endswith(':hidden'),
                            '%s hides a nav item' % token,
                        )
                self.assertEqual(len(root.find_all('script')), 1)

    def test_long_username_in_nav_can_wrap(self):
        """spec 03 AC-23 (review Q-14, HTML part): a very long unbroken
        username in the nav sits in an element that may shrink and break
        anywhere (min-w-0 + wrap-anywhere), so it can't push the page
        sideways at 320px."""
        username = 'u' * 150
        user = User.objects.create_user(
            username=username, email='long@example.com', password=PASSWORD
        )
        root = parse(self.get(reverse('core:dashboard'), user))
        nav = root.find('nav')
        holders = [n for n in nav.iter() if n.norm_text() == username
                   and not any(isinstance(c, Node) for c in n.children)]
        self.assertEqual(len(holders), 1, holders)
        holder = holders[0]
        self.assertIn('wrap-anywhere', holder.classes)
        self.assertIn('min-w-0', holder.classes)


# --------------------------------------------------------------------------
# AC-10: messages
# --------------------------------------------------------------------------

class MessageTests(UITestData):
    def assert_message(self, response, text, kind_word, kind_class):
        root = parse(response)
        status = root.find(role='status')
        self.assertIsNotNone(status, 'no role="status" region')
        items = [li for li in status.find_all('li') if text in li.text()]
        self.assertEqual(len(items), 1, 'message %r not in status region' % text)
        item = items[0]
        # Exact text, unchanged, in its own element.
        self.assertTrue(
            any(n.text().strip() == text for n in item.iter()),
            'no element holds exactly %r' % text,
        )
        # Nothing else visible: kind word + message text only.
        self.assertEqual(item.norm_text(), '%s %s' % (kind_word, text))
        hidden = item.find('span', class_='sr-only')
        self.assertIsNotNone(hidden)
        self.assertEqual(hidden.norm_text(), kind_word)
        svg = item.find('svg')
        self.assertIsNotNone(svg)
        self.assertEqual(svg.attrs.get('aria-hidden'), 'true')
        self.assertIn('msg', item.classes)
        self.assertIn(kind_class, item.classes)
        # Announced without moving focus; no dismiss control.
        self.assertNotEqual(status.attrs.get('aria-live'), 'assertive')
        self.assertEqual(status.find_all('button'), [])
        self.assertEqual(status.find_all('a'), [])
        self.assertNotIn('tabindex', status.attrs)

    def test_register_success_message(self):
        """spec 03 AC-10: the registration message keeps its exact text and
        is shown as a success message."""
        response = Client().post(
            reverse('accounts:register'),
            {'username': 'Newbie', 'email': 'newbie@example.com',
             'password1': PASSWORD, 'password2': PASSWORD},
            follow=True,
        )
        self.assert_message(
            response, 'Welcome, Newbie! Your account has been created.',
            'Success:', 'msg-success',
        )

    def test_logout_info_message(self):
        """spec 03 AC-10: "You have been logged out." is an information
        message."""
        client = self.client_for(self.alice)
        response = client.post(reverse('accounts:logout'), follow=True)
        self.assert_message(
            response, 'You have been logged out.', 'Information:', 'msg-info'
        )

    def test_create_workspace_success_message(self):
        """spec 03 AC-10: the create-workspace message keeps its exact text."""
        client = self.client_for(self.carol)
        response = client.post(
            reverse('workspaces:create'), {'name': 'Zephyr'}, follow=True
        )
        self.assert_message(
            response, 'Workspace "Zephyr" was created.', 'Success:', 'msg-success'
        )

    def test_add_member_success_message(self):
        """spec 03 AC-10: the add-member message keeps its exact text."""
        client = self.client_for(self.alice)
        response = client.post(
            reverse('workspaces:add_member', args=[self.apollo.pk]),
            {'username': 'Carol'},
            follow=True,
        )
        self.assert_message(
            response, 'Carol was added to the workspace.', 'Success:', 'msg-success'
        )

    def test_all_four_message_kinds_are_defined(self):
        """spec 03 AC-10 / OQ-2: the design defines success, information,
        warning and error message styles and kind words."""
        rules = component_rules()
        for kind in ('success', 'info', 'warning', 'error'):
            with self.subTest(kind=kind):
                self.assertIn('.msg-%s' % kind, rules)
        source = base_source()
        for word in ('Success:', 'Information:', 'Warning:', 'Error:'):
            with self.subTest(word=word):
                self.assertIn(word, source)


# --------------------------------------------------------------------------
# AC-11, AC-12, AC-13: forms
# --------------------------------------------------------------------------

def form_nodes(root):
    """Forms in <main> (excludes the nav logout form)."""
    return [f for f in main_of(root).find_all('form')]


def visible_inputs(form):
    return [
        i for i in form.find_all('input') if i.attrs.get('type') != 'hidden'
    ]


class FormTests(UITestData):
    def form_pages(self):
        pages = self.parsed_pages()
        return {
            name: pages[name]
            for name in ('login', 'register', 'create', 'detail_owner')
        }

    def test_every_field_has_visible_label_and_required_mark(self):
        """spec 03 AC-11: every field has a visible <label for>; required
        fields carry the shared required mark; the note appears once per
        form."""
        for name, root in self.form_pages().items():
            forms = form_nodes(root)
            self.assertEqual(len(forms), 1, name)
            form = forms[0]
            inputs = visible_inputs(form)
            with self.subTest(page=name):
                self.assertTrue(inputs)
                for field in inputs:
                    labels = form.find_all('label', for_=field.attrs.get('id'))
                    self.assertEqual(len(labels), 1, field)
                    label = labels[0]
                    self.assertNotIn('sr-only', label.classes)
                    if 'required' in field.attrs:
                        mark = label.find('span', class_='required-mark')
                        self.assertIsNotNone(mark, label)
                        self.assertEqual(mark.attrs.get('aria-hidden'), 'true')
                self.assertEqual(form.text().count('Required field'), 1)

    def test_help_text_is_linked_to_its_field(self):
        """spec 03 AC-11: help text (including the password rules on
        registration) sits with its field and is referenced by the input's
        aria-describedby."""
        root = self.parsed_pages()['register']
        form = RegistrationForm()
        fields_with_help = [bf for bf in form if bf.help_text]
        self.assertIn('password1', [bf.name for bf in fields_with_help])
        for bf in fields_with_help:
            with self.subTest(field=bf.name):
                field = by_id(root, bf.auto_id)
                self.assertIsNotNone(field)
                help_id = '%s_helptext' % bf.auto_id
                self.assertIn(help_id, field.attrs.get('aria-describedby', '').split())
                help_node = by_id(root, help_id)
                self.assertIsNotNone(help_node)
                expected = ' '.join(parse(str(bf.help_text)).text().split())
                self.assertEqual(help_node.norm_text(), expected)
                # Help text sits in the same field wrapper as its input.
                self.assertIs(help_node.parent, field.parent)

    def assert_errors_linked(self, response, form):
        self.assertTrue(form.errors)
        root = parse(response)
        for bf in form:
            if not bf.errors:
                continue
            with self.subTest(field=bf.name):
                field = by_id(root, bf.auto_id)
                self.assertIsNotNone(field)
                self.assertEqual(field.attrs.get('aria-invalid'), 'true')
                error_id = '%s_error' % bf.auto_id
                self.assertIn(
                    error_id, field.attrs.get('aria-describedby', '').split()
                )
                error_node = by_id(root, error_id)
                self.assertIsNotNone(error_node)
                self.assertIs(error_node.parent, field.parent)
                for error in bf.errors:
                    self.assertIn(error, error_node.norm_text())
        return root

    def test_register_errors_linked_to_fields(self):
        """spec 03 AC-12: an invalid registration marks each invalid input
        aria-invalid and links it to an element holding its error."""
        response = Client().post(
            reverse('accounts:register'),
            {'username': '', 'email': 'not-an-email',
             'password1': PASSWORD, 'password2': PASSWORD + 'x'},
        )
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertIn('username', form.errors)
        self.assertIn('email', form.errors)
        self.assert_errors_linked(response, form)

    def test_create_workspace_empty_name_error_linked(self):
        """spec 03 AC-12: an empty workspace name is marked invalid and
        linked to its error."""
        response = self.client_for(self.alice).post(
            reverse('workspaces:create'), {'name': ''}
        )
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertIn('name', form.errors)
        self.assert_errors_linked(response, form)

    def test_add_member_unknown_user_error_linked(self):
        """spec 03 AC-12: adding an unknown user marks the username invalid
        and links it to "No user with that username was found."."""
        response = self.client_for(self.alice).post(
            reverse('workspaces:add_member', args=[self.apollo.pk]),
            {'username': 'nobody-here'},
        )
        self.assertEqual(response.status_code, 200)
        form = response.context['add_member_form']
        self.assertIn('username', form.errors)
        root = self.assert_errors_linked(response, form)
        self.assertIn(
            'No user with that username was found.',
            by_id(root, '%s_error' % form['username'].auto_id).norm_text(),
        )

    def test_invalid_input_is_styled_by_aria_invalid(self):
        """spec 03 AC-12 (review Q-12): invalid fields are visibly marked
        through the aria-invalid attribute, and that danger border actually
        wins over the normal field border: the invalid rule sits in the same
        @layer components as the normal rule and has higher specificity, or
        equal specificity and comes later."""
        css = strip_comments(tailwind_css())
        components = css_block(css, '@layer components')
        outside = css.replace(components, '')
        # Both rules live only in the components layer.
        self.assertNotIn('aria-invalid', outside)
        self.assertNotIn('border-line-strong', outside)
        self.assertNotIn('border-danger', outside)

        rules = ordered_apply_rules(components)
        invalid = [
            (pos, sel) for pos, sel, tokens in rules
            if '[aria-invalid="true"]' in sel and 'border-danger' in tokens
        ]
        normal = [
            (pos, sel) for pos, sel, tokens in rules
            if sel.startswith('.form-field ') and 'border-line-strong' in tokens
        ]
        self.assertTrue(invalid, 'no [aria-invalid="true"] rule applies border-danger')
        self.assertIn(
            '.form-field input:not([type="hidden"])', [sel for _, sel in normal]
        )

        def targets(selector, element):
            kind = subject_type(selector)
            return kind is None or kind == element

        for element in ('input', 'select', 'textarea'):
            with self.subTest(element=element):
                normal_for = [(p, s) for p, s in normal if targets(s, element)]
                invalid_for = [(p, s) for p, s in invalid if targets(s, element)]
                self.assertTrue(normal_for, 'no normal field rule for %s' % element)
                self.assertTrue(invalid_for, 'no invalid rule for %s' % element)

                def wins(inv):
                    inv_pos, inv_sel = inv
                    for pos, sel in normal_for:
                        mine, theirs = specificity(inv_sel), specificity(sel)
                        if mine < theirs:
                            return False
                        if mine == theirs and inv_pos <= pos:
                            return False
                    return True

                self.assertTrue(
                    any(wins(inv) for inv in invalid_for),
                    '%s: invalid rules %r lose to normal rules %r' % (
                        element,
                        [(s, specificity(s)) for _, s in invalid_for],
                        [(s, specificity(s)) for _, s in normal_for],
                    ),
                )

    def test_specificity_helper(self):
        """spec 03 AC-12 (review Q-12): sanity check of the specificity
        helper the invalid-style test relies on."""
        self.assertEqual(specificity('.form-field input:not([type="hidden"])'), (0, 2, 1))
        self.assertEqual(specificity('.form-field input[aria-invalid="true"]'), (0, 2, 1))
        self.assertEqual(specificity('.form-field [aria-invalid="true"]'), (0, 2, 0))
        self.assertEqual(specificity('.form-field select'), (0, 1, 1))
        self.assertEqual(specificity(':where(a, button):focus-visible'), (0, 1, 0))
        self.assertEqual(specificity('#main > p::before'), (1, 0, 2))

    def test_login_non_field_error_above_fields(self):
        """spec 03 AC-12: a non-field error (wrong password) appears above
        the fields, inside the form."""
        response = Client().post(
            reverse('accounts:login'),
            {'username': 'Alice', 'password': 'wrong-password'},
        )
        self.assertEqual(response.status_code, 200)
        errors = response.context['form'].non_field_errors()
        self.assertTrue(errors)
        root = parse(response)
        form = form_nodes(root)[0]
        boxes = [
            n for n in form.find_all(class_='msg-error') if errors[0] in n.norm_text()
        ]
        self.assertEqual(len(boxes), 1)
        first_field = visible_inputs(form)[0]
        self.assertLess(boxes[0].order, first_field.order)

    def test_autocomplete_hints(self):
        """spec 03 AC-13: input types and autofill hints are right on every
        form."""
        pages = self.form_pages()
        expected = {
            'login': {'username': ('text', 'username'),
                      'password': ('password', 'current-password')},
            'register': {'username': ('text', 'username'),
                         'email': ('email', 'email'),
                         'password1': ('password', 'new-password'),
                         'password2': ('password', 'new-password')},
            'create': {'name': ('text', 'off')},
            'detail_owner': {'username': ('text', 'off')},
        }
        for page, fields in expected.items():
            form = form_nodes(pages[page])[0]
            for field_name, (input_type, hint) in fields.items():
                with self.subTest(page=page, field=field_name):
                    field = form.find('input', name=field_name)
                    self.assertIsNotNone(field)
                    self.assertEqual(field.attrs.get('type'), input_type)
                    self.assertEqual(field.attrs.get('autocomplete'), hint)

    def test_submit_buttons_say_what_they_do(self):
        """spec 03 AC-13: submit labels are "Log in", "Create account",
        "Create workspace" and "Add member"."""
        pages = self.form_pages()
        expected = {
            'login': 'Log in', 'register': 'Create account',
            'create': 'Create workspace', 'detail_owner': 'Add member',
        }
        for page, label in expected.items():
            form = form_nodes(pages[page])[0]
            buttons = form.find_all('button')
            with self.subTest(page=page):
                self.assertEqual(len(buttons), 1)
                self.assertEqual(buttons[0].attrs.get('type'), 'submit')
                self.assertEqual(buttons[0].norm_text(), label)


# --------------------------------------------------------------------------
# AC-14 … AC-17: pages
# --------------------------------------------------------------------------

class PageTests(UITestData):
    def test_auth_pages_single_card_with_cross_link(self):
        """spec 03 AC-14: login and register each show one centred card that
        links to the other page."""
        pages = self.parsed_pages()
        for name, other in (('login', 'accounts:register'),
                            ('register', 'accounts:login')):
            main = main_of(pages[name])
            cards = main.find_all(class_='card')
            with self.subTest(page=name):
                self.assertEqual(len(cards), 1)
                self.assertIn('mx-auto', cards[0].classes)
                self.assertEqual(len(main.find_all('h1')), 1)
                self.assertTrue(cards[0].find('h1'))
                self.assertTrue(cards[0].find('form'))
                self.assertTrue(cards[0].find('a', href=reverse(other)))

    def test_dashboard_with_workspaces(self):
        """spec 03 AC-15: greeting, a visible primary "Create workspace"
        action, and each workspace as a row link to its detail page."""
        main = main_of(self.parsed_pages()['dashboard'])
        self.assertEqual(main.find('h1').norm_text(), 'Welcome, Alice')
        create = main.find_all('a', href=reverse('workspaces:create'))
        self.assertEqual(len(create), 1)
        self.assertIn('btn-primary', create[0].classes)
        self.assertEqual(create[0].norm_text(), 'Create workspace')
        section = main.find('section')
        rows = section.find_all('li')
        self.assertEqual(len(rows), 2)
        for workspace, row in zip((self.apollo, self.hermes), rows):
            link = row.find('a')
            self.assertEqual(
                link.attrs.get('href'),
                reverse('workspaces:detail', args=[workspace.pk]),
            )
            self.assertEqual(link.norm_text(), workspace.name)
        self.assertNotIn("You don't belong to any workspaces yet.", main.text())

    def test_dashboard_empty_state_has_own_call_to_action(self):
        """spec 03 AC-15: with no workspaces, the section holds the empty
        message and its own "Create workspace" link."""
        main = main_of(self.parsed_pages()['dashboard_empty'])
        section = main.find('section')
        self.assertIsNotNone(section)
        self.assertIn("You don't belong to any workspaces yet.", section.norm_text())
        own = section.find_all('a', href=reverse('workspaces:create'))
        self.assertEqual(len(own), 1)
        self.assertIn('btn-primary', own[0].classes)
        self.assertEqual(own[0].norm_text(), 'Create workspace')
        self.assertEqual(section.find_all('li'), [])

    def test_workspace_detail_structure(self):
        """spec 03 AC-16: name as h1, a back link to the dashboard, the
        member count, Owner/Member text labels."""
        pages = self.parsed_pages()
        for name in ('detail_owner', 'detail_member'):
            main = main_of(pages[name])
            with self.subTest(page=name):
                self.assertEqual(main.find('h1').norm_text(), 'Apollo')
                back = main.find_all('a', href=reverse('core:dashboard'))
                self.assertEqual(len(back), 1)
                self.assertIn('Back to dashboard', back[0].norm_text())
                self.assertLess(back[0].order, main.find('h1').order)
                members = by_id(pages[name], 'members-heading').parent.parent
                self.assertEqual(members.tag, 'section')
                count = members.find(class_='badge')
                self.assertEqual(count.norm_text(), '2')
                rows = [li.norm_text() for li in members.find_all('li')]
                self.assertEqual(rows, ['Alice Owner', 'Bob Member'])
                badges = [b.norm_text() for b in members.find('ul').find_all(class_='badge')]
                self.assertEqual(badges, ['Owner', 'Member'])

    def test_add_member_section_only_for_owner(self):
        """spec 03 AC-16: the owner sees a separate "Add a member" section;
        a member doesn't."""
        pages = self.parsed_pages()
        owner_heading = by_id(pages['detail_owner'], 'add-member-heading')
        self.assertIsNotNone(owner_heading)
        self.assertEqual(owner_heading.tag, 'h2')
        self.assertEqual(owner_heading.norm_text(), 'Add a member')
        section = owner_heading.parent
        self.assertEqual(section.tag, 'section')
        self.assertEqual(section.attrs.get('aria-labelledby'), 'add-member-heading')
        self.assertIn('card', section.classes)
        self.assertTrue(section.find('form'))
        # Separate from the members card.
        self.assertIsNone(section.find(id='members-heading'))

        member_main = main_of(pages['detail_member'])
        self.assertIsNone(by_id(pages['detail_member'], 'add-member-heading'))
        self.assertNotIn('Add a member', member_main.text())
        self.assertEqual(member_main.find_all('form'), [])

    def test_create_page_card_with_primary_and_cancel(self):
        """spec 03 AC-17: the form is in a card with a primary "Create
        workspace" button and a secondary "Cancel" link to the dashboard."""
        main = main_of(self.parsed_pages()['create'])
        card = main.find(class_='card')
        self.assertIsNotNone(card)
        form = card.find('form')
        self.assertIsNotNone(form)
        submit = form.find('button', type='submit')
        self.assertEqual(submit.norm_text(), 'Create workspace')
        self.assertIn('btn-primary', submit.classes)
        cancel = [a for a in card.find_all('a') if a.norm_text() == 'Cancel']
        self.assertEqual(len(cancel), 1)
        self.assertEqual(cancel[0].attrs.get('href'), reverse('core:dashboard'))
        self.assertIn('btn-secondary', cancel[0].classes)


# --------------------------------------------------------------------------
# AC-18 … AC-22: accessibility
# --------------------------------------------------------------------------

class AccessibilityTests(UITestData):
    def test_language_landmarks_and_headings(self):
        """spec 03 AC-18: lang="en", one <h1>, no skipped heading levels, a
        <main> and a labelled <nav>."""
        for name, root in self.parsed_pages().items():
            with self.subTest(page=name):
                html = root.find('html')
                self.assertEqual(html.attrs.get('lang'), 'en')
                self.assertEqual(len(root.find_all('h1')), 1)
                levels = [
                    int(n.tag[1]) for n in root.iter()
                    if re.fullmatch(r'h[1-6]', n.tag)
                ]
                self.assertEqual(levels[0], 1)
                for previous, current in zip(levels, levels[1:]):
                    self.assertLessEqual(current, previous + 1, levels)
                self.assertEqual(len(root.find_all('main')), 1)
                nav = root.find('nav')
                self.assertTrue(nav.attrs.get('aria-label', '').strip())

    def test_titles_unique_and_descriptive(self):
        """spec 03 AC-18: each page has its own descriptive <title>."""
        pages = self.parsed_pages()
        titles = {}
        for name in ('login', 'register', 'dashboard', 'create', 'detail_owner'):
            title = pages[name].find('title').norm_text()
            titles[name] = title
            with self.subTest(page=name):
                self.assertTrue(title.endswith('· Project Management System'), title)
                self.assertNotEqual(title, 'Project Management System')
        self.assertEqual(len(set(titles.values())), len(titles), titles)
        self.assertIn('Apollo', titles['detail_owner'])

    def test_focus_visible_rules(self):
        """spec 03 AC-19: a focus-visible ring for plain links, buttons and
        inputs in @layer base, and in both button classes."""
        base = css_block(tailwind_css(), '@layer base')
        match = re.search(r':where\(([^)]*)\):focus-visible\s*\{\s*@apply([^;]+);', base)
        self.assertIsNotNone(match)
        elements = {e.strip() for e in match.group(1).split(',')}
        self.assertLessEqual({'a', 'button', 'input'}, elements)
        tokens = set(match.group(2).split())
        self.assertLessEqual({'ring-2', 'ring-ring', 'ring-offset-2'}, tokens)
        rules = component_rules()
        for cls in ('.btn-primary', '.btn-secondary'):
            with self.subTest(cls=cls):
                self.assertIn('focus-visible:ring-2', rules[cls])
                self.assertIn('focus-visible:ring-ring', rules[cls])

    def test_focus_rules_use_outline_hidden(self):
        """spec 03 AC-19 (review Q-13): the base focus-visible rule and the
        .btn-* rule hide the outline with outline-hidden (which stays visible
        in forced-colors mode), and no focus rule for an interactive element
        uses outline-none. main:focus is not a control and may use it."""
        css = tailwind_css()
        base = apply_rules(css_block(css, '@layer base'))
        focus = base[':where(a, button, input, select, textarea, summary):focus-visible']
        self.assertIn('outline-hidden', focus)
        self.assertNotIn('outline-none', focus)
        components = component_rules()
        for cls in ('.btn-primary', '.btn-secondary'):
            with self.subTest(cls=cls):
                self.assertIn('focus-visible:outline-hidden', components[cls])
                self.assertNotIn('focus-visible:outline-none', components[cls])
                self.assertNotIn('outline-none', components[cls])

        allowed = {'main:focus'}
        for _, selector, tokens in ordered_apply_rules(css):
            with self.subTest(selector=selector):
                # A variant such as focus:outline-none / focus-visible:outline-none.
                self.assertEqual(
                    [t for t in tokens if re.search(r'(^|:)focus[\w-]*:.*outline-none$', t)],
                    [],
                )
                if ':focus' in selector and selector not in allowed:
                    self.assertNotIn('outline-none', tokens)

    def test_no_focus_outline_removed_without_replacement(self):
        """spec 03 AC-19: no element in the pages removes its outline or
        ring on focus."""
        for name, root in self.parsed_pages().items():
            for node in root.iter():
                for token in node.classes:
                    with self.subTest(page=name, token=token):
                        self.assertNotIn(token, {
                            'outline-none', 'focus:outline-none',
                            'focus-visible:outline-none', 'focus:ring-0',
                            'focus-visible:ring-0',
                        })

    def test_theme_tokens_meet_wcag_aa(self):
        """spec 03 AC-20: text pairs ≥ 4.5:1 and UI / focus pairs ≥ 3:1,
        computed from the @theme hex tokens in base.html."""
        tokens = theme_tokens()
        for pairs, minimum in ((TEXT_PAIRS, 4.5), (UI_PAIRS, 3.0)):
            for fg, bg in pairs:
                with self.subTest(fg=fg, bg=bg):
                    self.assertIn(fg, tokens)
                    self.assertIn(bg, tokens)
                    ratio = contrast(tokens[fg], tokens[bg])
                    self.assertGreaterEqual(
                        ratio, minimum, '%s on %s is %.2f:1' % (fg, bg, ratio)
                    )

    def test_master_lists_pairs_with_correct_ratios(self):
        """spec 03 AC-20: the design system's contrast table lists the pairs
        with ratios that match the formula and meet their threshold, and its
        token hex values match base.html."""
        text = MASTER_PATH.read_text(encoding='utf-8')
        rows = re.findall(
            r'^\|\s*([^|]+?)\s*\|\s*`(#[0-9A-Fa-f]{6})`\s*/\s*`(#[0-9A-Fa-f]{6})`'
            r'\s*\|\s*([\d.]+):1\s*\|\s*([\d.]+):1\s*\|',
            text, re.M,
        )
        self.assertGreaterEqual(len(rows), len(TEXT_PAIRS))
        for label, fg, bg, stated, needed in rows:
            with self.subTest(pair=label):
                ratio = contrast(fg, bg)
                self.assertAlmostEqual(ratio, float(stated), delta=0.011)
                self.assertGreaterEqual(ratio, float(needed))
        tokens = theme_tokens()
        documented = dict(re.findall(
            r'^\|\s*`--color-([a-z-]+)`\s*\|\s*`(#[0-9A-Fa-f]{6})`\s*\|', text, re.M
        ))
        self.assertTrue(documented)
        for name, value in documented.items():
            with self.subTest(token=name):
                self.assertEqual(tokens.get(name), value.upper())

    def test_target_sizes_from_classes(self):
        """spec 03 AC-21 (HTML part): buttons, inputs, nav links, the brand
        link, back, cancel and row links have a minimum height ≥ 24px;
        inline cross-links get vertical padding."""
        rules = component_rules()
        self.assertIn('min-h-11', rules['.btn-primary'])
        self.assertIn('min-h-11', rules['.btn-secondary'])
        self.assertIn('min-h-11', rules['.nav-link'])
        self.assertIn('min-h-11', rules['.form-field input:not([type="hidden"])'])
        self.assertIn('py-1', rules['.link'])
        self.assertIn('focus:py-3', rules['.skip-link'])

        pages = self.parsed_pages()
        targets = []
        for name, root in pages.items():
            nav = root.find('nav')
            targets += [(name, a) for a in nav.find_all('a')]
            targets += [(name, b) for b in nav.find_all('button')]
            main = main_of(root)
            targets += [(name, b) for b in main.find_all('button')]
            targets += [
                (name, a) for a in main.find_all('a') if 'link' not in a.classes
            ]
        self.assertTrue(targets)
        for name, node in targets:
            with self.subTest(page=name, target=node.norm_text()):
                self.assertGreaterEqual(effective_min_h(node, rules), 24)
        # Inline sentence links use the .link padding.
        for name in ('login', 'register'):
            inline = [a for a in main_of(pages[name]).find_all('a')
                      if 'link' in a.classes]
            with self.subTest(page=name):
                self.assertEqual(len(inline), 1)

    def test_reduced_motion(self):
        """spec 03 AC-22: a prefers-reduced-motion rule turns transitions
        off, and every transition is behind motion-safe:."""
        base = css_block(tailwind_css(), '@layer base')
        reduced = css_block(base, '@media (prefers-reduced-motion: reduce)')
        self.assertIn('transition: none !important', reduced)
        self.assertIn('animation: none !important', reduced)

        def unsafe(tokens):
            return [
                t for t in tokens
                if re.search(r'(^|:)(transition|animate|duration)', t)
                and not t.startswith('motion-safe:')
            ]

        for selector, tokens in apply_rules(tailwind_css()).items():
            with self.subTest(selector=selector):
                self.assertEqual(unsafe(tokens), [])
        for name, root in self.parsed_pages().items():
            for node in root.iter():
                with self.subTest(page=name, node=node.tag):
                    self.assertEqual(unsafe(node.classes), [])


# --------------------------------------------------------------------------
# AC-25, AC-26: constraints preserved
# --------------------------------------------------------------------------

class ConstraintTests(UITestData):
    def test_only_tailwind_script_and_no_external_styles(self):
        """spec 03 AC-25: the only script is the Tailwind CDN, and no
        stylesheet, font or icon library is linked."""
        for name, root in self.parsed_pages().items():
            with self.subTest(page=name):
                scripts = root.find_all('script')
                self.assertEqual([s.attrs.get('src') for s in scripts], [TAILWIND_CDN])
                self.assertEqual(scripts[0].text().strip(), '')
                self.assertEqual(root.find_all('link'), [])
                self.assertEqual(root.find_all('img'), [])
                self.assertEqual(root.find_all('iframe'), [])
                for node in root.iter():
                    handlers = [k for k in node.attrs if k.startswith('on')]
                    self.assertEqual(handlers, [], node)

    def test_every_svg_is_hidden_or_titled(self):
        """spec 03 AC-25: every inline SVG is aria-hidden or has a <title>."""
        roots = dict(self.parsed_pages())
        roots['after_message'] = parse(self.client_for(self.alice).post(
            reverse('accounts:logout'), follow=True
        ))
        roots['login_error'] = parse(Client().post(
            reverse('accounts:login'), {'username': 'Alice', 'password': 'x'}
        ))
        svg_count = 0
        for name, root in roots.items():
            for svg in root.find_all('svg'):
                svg_count += 1
                with self.subTest(page=name):
                    self.assertTrue(
                        svg.attrs.get('aria-hidden') == 'true' or svg.find('title'),
                        svg,
                    )
        self.assertGreater(svg_count, 0)

    def test_icon_partials_are_inline_svg(self):
        """spec 03 AC-25: icon partials are inline SVG only, with no
        external references."""
        icons = list((settings.BASE_DIR / 'templates' / 'partials' / 'icons').glob('*.html'))
        self.assertTrue(icons)
        for path in icons:
            source = path.read_text(encoding='utf-8')
            with self.subTest(icon=path.name):
                self.assertIn('<svg', source)
                self.assertIn('aria-hidden="true"', source)
                self.assertNotRegex(source, r'(?:xlink:)?href=|<use\b|<img\b|url\(')

    def test_every_post_form_has_csrf_token(self):
        """spec 03 AC-26: every POST form carries the anti-forgery token, and
        logout is still a POST form."""
        for name, root in self.parsed_pages().items():
            forms = root.find_all('form')
            with self.subTest(page=name):
                self.assertTrue(forms)
                for form in forms:
                    self.assertEqual(form.attrs.get('method', '').lower(), 'post')
                    self.assertIsNotNone(
                        form.find('input', name='csrfmiddlewaretoken'), form
                    )
        nav = self.parsed_pages()['dashboard'].find('nav')
        logout = nav.find('form')
        self.assertEqual(logout.attrs.get('action'), reverse('accounts:logout'))
        self.assertEqual(logout.attrs.get('method'), 'post')

    def test_user_text_is_escaped(self):
        """spec 03 AC-26: workspace names and usernames stay plain text in
        the new markup (rows, h1, title, member list, messages)."""
        evil_user = User.objects.create_user(
            username='<i>eve</i>', email='eve@example.com', password=PASSWORD
        )
        workspace = Workspace.objects.create_with_owner('<b>Bold</b> & co', evil_user)
        client = self.client_for(evil_user)
        for url in (reverse('core:dashboard'),
                    reverse('workspaces:detail', args=[workspace.pk])):
            html = client.get(url).content.decode()
            with self.subTest(url=url):
                self.assertNotIn('<b>Bold</b>', html)
                self.assertIn('&lt;b&gt;Bold&lt;/b&gt; &amp; co', html)
                self.assertNotIn('<i>eve</i>', html)
                self.assertIn('&lt;i&gt;eve&lt;/i&gt;', html)
        response = client.post(
            reverse('workspaces:create'), {'name': '<u>New</u>'}, follow=True
        )
        html = response.content.decode()
        self.assertNotIn('<u>New</u>', html)
        self.assertIn('&lt;u&gt;New&lt;/u&gt;', html)
