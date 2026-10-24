"""UI tests for spec 05 AC-20 (tasks): the parts of the step 03 design
system that can be seen in the rendered HTML or the template sources.

Pages: the project page's tasks section (with tasks and empty), the
create-task page (fresh and with errors) and the task page (with and
without a description).

Not tested here (manual check, plan 05 step 11 / D-1): layout at 320, 768
and 1280px, real sideways scrolling, measured target sizes and how visible
focus actually renders. Focus and reduced-motion rules are covered globally
by core/tests/test_ui.py; here we only check the new markup doesn't opt out.
"""
import re

from django.conf import settings

from core.tests.helpers import (
    HEX_COLOUR,
    PALETTE_CLASS,
    TAILWIND_CDN,
    by_id,
    component_rules,
    effective_min_h,
    heading_levels,
    main_of,
    parse,
)
from tasks.forms import TaskForm
from tasks.models import Task

from .data import TaskTestData

NEW_OR_CHANGED_TEMPLATES = [
    settings.BASE_DIR / 'tasks' / 'templates' / 'tasks' / 'task_form.html',
    settings.BASE_DIR / 'tasks' / 'templates' / 'tasks' / 'task_detail.html',
    settings.BASE_DIR / 'projects' / 'templates' / 'projects' / 'project_detail.html',
    settings.BASE_DIR / 'workspaces' / 'templates' / 'workspaces' / 'workspace_detail.html',
    settings.BASE_DIR / 'templates' / 'partials' / 'icons' / 'list-bullet.html',
]

FOCUS_OPT_OUTS = {
    'outline-none', 'focus:outline-none', 'focus-visible:outline-none',
    'focus:ring-0', 'focus-visible:ring-0',
}


class TaskUITestData(TaskTestData):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.bare_task = Task.objects.create(project=cls.roadmap, title='Bare task')

    def get(self, url, user=None):
        response = self.client_for(user or self.bob).get(url)
        self.assertEqual(response.status_code, 200, url)
        return response

    def invalid_create(self):
        response = self.client_for(self.bob).post(
            self.create_url(self.apollo, self.roadmap),
            {'title': '   ', 'description': 'd' * 2001},
        )
        self.assertEqual(response.status_code, 200)
        return response

    def responses(self):
        return {
            'project_with_tasks': self.get(self.project_url(self.apollo, self.roadmap)),
            'project_empty': self.get(self.project_url(self.apollo, self.launch)),
            'create': self.get(self.create_url(self.apollo, self.roadmap)),
            'create_errors': self.invalid_create(),
            'detail': self.get(self.detail_url(self.apollo, self.roadmap, self.task)),
            'detail_empty': self.get(
                self.detail_url(self.apollo, self.roadmap, self.bare_task)
            ),
        }

    def pages(self):
        return {name: parse(r) for name, r in self.responses().items()}


class HeadingsAndTitlesTests(TaskUITestData):
    def test_one_h1_no_skipped_levels_and_main(self):
        """spec 05 AC-20: one main heading, heading order never skips a
        level, and a single main#main on every new or changed page."""
        for name, root in self.pages().items():
            with self.subTest(page=name):
                self.assertEqual(len(root.find_all('h1')), 1)
                levels = heading_levels(root)
                self.assertEqual(levels[0], 1)
                for previous, current in zip(levels, levels[1:]):
                    self.assertLessEqual(current, previous + 1, levels)
                mains = root.find_all('main')
                self.assertEqual(len(mains), 1)
                self.assertEqual(mains[0].attrs.get('id'), 'main')

    def test_headings_text(self):
        """spec 05 AC-20 / AC-1 / AC-7 / AC-10: the create page's h1 is "New
        task", the task page's h1 is the task title, and the tasks section
        has an h2 "Tasks"."""
        pages = self.pages()
        for name in ('create', 'create_errors'):
            with self.subTest(page=name):
                self.assertEqual(pages[name].find('h1').norm_text(), 'New task')
        self.assertEqual(pages['detail'].find('h1').norm_text(), 'Draft outline')
        self.assertEqual(pages['detail_empty'].find('h1').norm_text(), 'Bare task')
        for name in ('project_with_tasks', 'project_empty'):
            with self.subTest(page=name):
                heading = by_id(pages[name], 'tasks-heading')
                self.assertEqual(heading.tag, 'h2')
                self.assertEqual(heading.norm_text(), 'Tasks')

    def test_titles_unique_and_descriptive(self):
        """spec 05 AC-20: each new page has its own descriptive <title>."""
        pages = self.pages()
        titles = {}
        for name in ('project_with_tasks', 'create', 'detail', 'detail_empty'):
            title = pages[name].find('title').norm_text()
            titles[name] = title
            with self.subTest(page=name):
                self.assertTrue(title.endswith('· Project Management System'), title)
        self.assertEqual(len(set(titles.values())), len(titles), titles)
        self.assertIn('New task', titles['create'])
        self.assertIn('Roadmap', titles['create'])
        self.assertIn('Draft outline', titles['detail'])
        self.assertIn('Roadmap', titles['detail'])


class TargetsAndFieldsTests(TaskUITestData):
    def test_links_and_buttons_have_minimum_height(self):
        """spec 05 AC-20 (HTML part): every link and button in <main> on the
        new pages has min-h-11 or a .btn-* class (at least 24px)."""
        rules = component_rules()
        for name, root in self.pages().items():
            main = main_of(root)
            targets = main.find_all('a') + main.find_all('button')
            self.assertTrue(targets, name)
            for node in targets:
                if 'link' in node.classes:
                    continue
                with self.subTest(page=name, target=node.norm_text()):
                    has_class = 'min-h-11' in node.classes or any(
                        c.startswith('btn-') for c in node.classes
                    )
                    self.assertTrue(has_class, node)
                    self.assertGreaterEqual(effective_min_h(node, rules), 24)

    def test_create_page_actions(self):
        """spec 05 AC-20 / AC-1 (OQ-5): a primary "Create task" submit and a
        secondary "Cancel" link back to the project page."""
        main = main_of(self.pages()['create'])
        form = main.find('form')
        buttons = form.find_all('button')
        self.assertEqual(len(buttons), 1)
        self.assertEqual(buttons[0].attrs.get('type'), 'submit')
        self.assertEqual(buttons[0].norm_text(), 'Create task')
        self.assertIn('btn-primary', buttons[0].classes)
        cancel = [a for a in main.find_all('a') if a.norm_text() == 'Cancel']
        self.assertEqual(len(cancel), 1)
        self.assertIn('btn-secondary', cancel[0].classes)
        self.assertEqual(
            cancel[0].attrs.get('href'), self.project_url(self.apollo, self.roadmap)
        )

    def test_fields_labelled(self):
        """spec 05 AC-20: every visible field on the create page has a
        visible label; the title is marked required, has autocomplete off,
        and the description is a textarea labelled "(optional)"."""
        form = main_of(self.pages()['create']).find('form')
        self.assertEqual(form.attrs.get('method'), 'post')
        self.assertIsNotNone(form.find('input', name='csrfmiddlewaretoken'))
        fields = [
            n for n in form.iter()
            if n.tag in ('input', 'textarea', 'select')
            and n.attrs.get('type') != 'hidden'
        ]
        self.assertEqual([f.attrs.get('name') for f in fields], ['title', 'description'])
        for field in fields:
            with self.subTest(field=field.attrs.get('name')):
                labels = form.find_all('label', for_=field.attrs.get('id'))
                self.assertEqual(len(labels), 1)
                self.assertTrue(labels[0].norm_text())
                self.assertNotIn('sr-only', labels[0].classes)
        title_label = form.find('label', for_='id_title')
        self.assertIsNotNone(title_label.find(class_='required-mark'))
        title = form.find(id='id_title')
        self.assertIn('required', title.attrs)
        self.assertEqual(title.attrs.get('autocomplete'), 'off')
        self.assertIn('(optional)', form.find('label', for_='id_description').norm_text())
        self.assertEqual(form.find(id='id_description').tag, 'textarea')
        self.assertNotIn('required', form.find(id='id_description').attrs)

    def test_errors_linked_to_fields(self):
        """spec 05 AC-20: invalid fields are aria-invalid and linked through
        aria-describedby to an <id>_error element next to them."""
        response = self.invalid_create()
        form = response.context['form']
        self.assertEqual(set(form.errors), {'title', 'description'})
        root = parse(response)
        for bf in form:
            with self.subTest(field=bf.name):
                field = by_id(root, bf.auto_id)
                self.assertEqual(field.attrs.get('aria-invalid'), 'true')
                error_id = '%s_error' % bf.auto_id
                self.assertIn(error_id, field.attrs.get('aria-describedby', '').split())
                error_node = by_id(root, error_id)
                self.assertIsNotNone(error_node)
                self.assertIs(error_node.parent, field.parent)
                for error in bf.errors:
                    self.assertIn(error, error_node.norm_text())

    def test_form_is_task_form_through_shared_partials(self):
        """spec 05 AC-20: the create page renders TaskForm through the shared
        partials (one form-field wrapper per visible field)."""
        response = self.get(self.create_url(self.apollo, self.roadmap))
        self.assertIsInstance(response.context['form'], TaskForm)
        self.assertTemplateUsed(response, 'partials/form_body.html')
        self.assertTemplateUsed(response, 'partials/form_field.html')
        form = main_of(parse(response)).find('form')
        self.assertEqual(len(form.find_all('div', class_='form-field')), 2)


class WrappingTests(TaskUITestData):
    def holders_of(self, root, text):
        nodes = [
            n for n in main_of(root).iter()
            if any(isinstance(c, str) and c.strip() == text for c in n.children)
        ]
        self.assertTrue(nodes, 'no element holds %r' % text)
        return nodes

    def test_user_text_can_wrap(self):
        """spec 05 AC-20 (HTML part): task titles, descriptions, and the
        project and workspace names on the new pages carry wrap-anywhere, so
        long unbroken text never forces sideways scrolling."""
        long_title = 'T' * 200
        task = Task.objects.create(
            project=self.roadmap, title=long_title, description='D' * 300
        )
        detail = self.detail_url(self.apollo, self.roadmap, task)
        create = self.create_url(self.apollo, self.roadmap)
        cases = {
            'task row': (self.project_url(self.apollo, self.roadmap), long_title),
            'task h1': (detail, long_title),
            'description': (detail, 'D' * 300),
            'back link project name': (detail, 'Roadmap'),
            'context workspace name': (detail, 'Apollo'),
            'create subtitle project': (create, 'Roadmap'),
            'create subtitle workspace': (create, 'Apollo'),
        }
        for label, (url, text) in cases.items():
            with self.subTest(case=label):
                root = parse(self.get(url))
                for node in self.holders_of(root, text):
                    self.assertIn('wrap-anywhere', node.classes)

    def test_task_rows_can_shrink(self):
        """spec 05 AC-20 (HTML part): the title inside each row link may
        shrink (min-w-0), so a long title wraps instead of overflowing."""
        root = self.pages()['project_with_tasks']
        section = by_id(root, 'tasks-heading').parent.parent.parent
        rows = section.find_all('li')
        self.assertTrue(rows)
        for row in rows:
            span = row.find('a').find('span')
            with self.subTest(row=row.norm_text()):
                self.assertIn('min-w-0', span.classes)
                self.assertIn('wrap-anywhere', span.classes)


class ConstraintTests(TaskUITestData):
    def test_templates_use_tokens_only(self):
        """spec 05 AC-20: the new and changed templates use semantic colour
        tokens only (no palette classes, no raw hex), never |safe, and add no
        script or stylesheet."""
        for path in NEW_OR_CHANGED_TEMPLATES:
            self.assertTrue(path.is_file(), path)
            source = path.read_text(encoding='utf-8')
            with self.subTest(template=path.name):
                self.assertEqual(PALETTE_CLASS.findall(source), [])
                self.assertEqual(HEX_COLOUR.findall(source), [])
                self.assertNotIn('|safe', source)
                self.assertNotIn('autoescape off', source)
                self.assertNotIn('<script', source)
                self.assertNotIn('<link', source)

    def test_list_bullet_icon_is_inline_hidden_svg(self):
        """spec 05 AC-20: the one new icon is an inline, aria-hidden SVG with
        no external reference (no icon package)."""
        source = NEW_OR_CHANGED_TEMPLATES[-1].read_text(encoding='utf-8')
        self.assertIn('<svg', source)
        self.assertIn('aria-hidden="true"', source)
        self.assertNotRegex(source, r'(?:xlink:)?href=|<use\b|<img\b|url\(')

    def test_no_new_scripts_or_stylesheets(self):
        """spec 05 AC-20: the only script is the Tailwind CDN; no stylesheet,
        font, image or inline handler is added."""
        for name, root in self.pages().items():
            with self.subTest(page=name):
                scripts = root.find_all('script')
                self.assertEqual([s.attrs.get('src') for s in scripts], [TAILWIND_CDN])
                self.assertEqual(root.find_all('link'), [])
                self.assertEqual(root.find_all('img'), [])
                for node in root.iter():
                    handlers = [k for k in node.attrs if k.startswith('on')]
                    self.assertEqual(handlers, [], node)

    def test_every_svg_is_aria_hidden(self):
        """spec 05 AC-20: every inline SVG on the new pages is aria-hidden."""
        for name, root in self.pages().items():
            svgs = root.find_all('svg')
            self.assertTrue(svgs, name)
            for svg in svgs:
                with self.subTest(page=name, svg=svg.attrs.get('class')):
                    self.assertEqual(svg.attrs.get('aria-hidden'), 'true')

    def test_focus_not_removed(self):
        """spec 05 AC-20: no element on the new pages removes its focus
        outline or ring."""
        for name, root in self.pages().items():
            for node in root.iter():
                with self.subTest(page=name, node=node.tag):
                    self.assertEqual(FOCUS_OPT_OUTS & set(node.classes), set())

    def test_motion_only_behind_motion_safe(self):
        """spec 05 AC-20: any transition or animation class on the new pages
        is behind motion-safe:, so reduced motion is respected."""
        for name, root in self.pages().items():
            for node in root.iter():
                unsafe = [
                    t for t in node.classes
                    if re.search(r'(^|:)(transition|animate|duration)', t)
                    and not t.startswith('motion-safe:')
                ]
                with self.subTest(page=name, node=node.tag):
                    self.assertEqual(unsafe, [])

    def test_every_post_form_has_csrf_token(self):
        """spec 05 AC-20 / AC-17: every form on the new pages posts with the
        anti-forgery token."""
        for name, root in self.pages().items():
            for form in root.find_all('form'):
                with self.subTest(page=name):
                    self.assertEqual(form.attrs.get('method', '').lower(), 'post')
                    self.assertIsNotNone(form.find('input', name='csrfmiddlewaretoken'))
