"""UI tests for spec 04 AC-21 (projects): the parts of the step 03 design
system that can be seen in the rendered HTML or the template sources.

Pages: the workspace page's projects section (owner, member, empty), the
create-project page (fresh and with errors) and the project page (with and
without a description).

Not tested here (manual check, plan 04 step 10 / D-1): layout at 320, 768
and 1280px, real sideways scrolling, measured target sizes and visible focus
rendering. Visible focus and reduced motion are also covered globally by
core/tests/test_ui.py; here we only check the new markup doesn't opt out.

Helpers come from core/tests/helpers.py, a non-test module (spec 05 AC-23,
step 04 Q-46), so no other app's test module is imported. Each test renders
the page matrix once (step 04 Q-47).

Spec 05 AC-22 changed two things these tests pin: the workspace page's
empty-state action now reads "New project", and the project page's back
link reads "Back to <workspace name>".
"""
import re

from django.conf import settings

from core.tests.helpers import (
    BASE_TEMPLATE,
    HEX_COLOUR,
    PALETTE_CLASS as PALETTE,
    TAILWIND_CDN,
    by_id,
    component_rules,
    css_block,
    effective_min_h,
    main_of,
    parse,
    tailwind_css,
)
from projects.forms import ProjectForm
from projects.models import Project
from workspaces.models import Workspace

from .data import ProjectTestData

NEW_OR_CHANGED_TEMPLATES = [
    settings.BASE_DIR / 'projects' / 'templates' / 'projects' / 'project_form.html',
    settings.BASE_DIR / 'projects' / 'templates' / 'projects' / 'project_detail.html',
    settings.BASE_DIR / 'workspaces' / 'templates' / 'workspaces' / 'workspace_detail.html',
    settings.BASE_DIR / 'templates' / 'partials' / 'icons' / 'clipboard-document-list.html',
]


class ProjectUITestData(ProjectTestData):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.empty_ws = Workspace.objects.create_with_owner(
            'Zephyr', cls.dave
        )
        cls.bare = Project.objects.create(workspace=cls.apollo, name='Bare')

    def get(self, url, user):
        response = self.client_for(user).get(url)
        self.assertEqual(response.status_code, 200, url)
        return response

    def invalid_create(self):
        response = self.client_for(self.bob).post(
            self.create_url(self.apollo), {'name': '   ', 'description': 'd' * 2001}
        )
        self.assertEqual(response.status_code, 200)
        return response

    def responses(self):
        return {
            'workspace_owner': self.get(self.workspace_url(self.apollo), self.alice),
            'workspace_member': self.get(self.workspace_url(self.apollo), self.bob),
            'workspace_empty': self.get(self.workspace_url(self.empty_ws), self.dave),
            'create': self.get(self.create_url(self.apollo), self.bob),
            'create_errors': self.invalid_create(),
            'detail': self.get(self.detail_url(self.apollo, self.roadmap), self.bob),
            'detail_empty': self.get(self.detail_url(self.apollo, self.bare), self.bob),
        }

    def pages(self):
        return {name: parse(r) for name, r in self.responses().items()}


class HeadingsAndTitlesTests(ProjectUITestData):
    def test_one_h1_no_skipped_levels_and_main(self):
        """spec 04 AC-21: one main heading, heading order never skips a
        level, and a single main#main on every new or changed page."""
        for name, root in self.pages().items():
            with self.subTest(page=name):
                self.assertEqual(len(root.find_all('h1')), 1)
                levels = [
                    int(n.tag[1]) for n in root.iter()
                    if re.fullmatch(r'h[1-6]', n.tag)
                ]
                self.assertEqual(levels[0], 1)
                for previous, current in zip(levels, levels[1:]):
                    self.assertLessEqual(current, previous + 1, levels)
                mains = root.find_all('main')
                self.assertEqual(len(mains), 1)
                self.assertEqual(mains[0].attrs.get('id'), 'main')

    def test_headings_text(self):
        """spec 04 AC-21 / AC-1 / AC-10: the create page's h1 is "New
        project"; the project page's h1 is the project name; the projects
        section has an h2 "Projects"."""
        pages = self.pages()
        self.assertEqual(pages['create'].find('h1').norm_text(), 'New project')
        self.assertEqual(pages['detail'].find('h1').norm_text(), 'Roadmap')
        for name in ('workspace_owner', 'workspace_member', 'workspace_empty'):
            with self.subTest(page=name):
                heading = by_id(pages[name], 'projects-heading')
                self.assertEqual(heading.tag, 'h2')
                self.assertEqual(heading.norm_text(), 'Projects')

    def test_titles_unique_and_descriptive(self):
        """spec 04 AC-21: each new page has its own descriptive <title>."""
        pages = self.pages()
        titles = {}
        for name in ('workspace_owner', 'create', 'detail', 'detail_empty'):
            title = pages[name].find('title').norm_text()
            titles[name] = title
            with self.subTest(page=name):
                self.assertTrue(title.endswith('· Project Management System'), title)
        self.assertEqual(len(set(titles.values())), len(titles), titles)
        self.assertIn('New project', titles['create'])
        self.assertIn('Apollo', titles['create'])
        self.assertIn('Roadmap', titles['detail'])
        self.assertIn('Apollo', titles['detail'])


class ProjectsSectionStructureTests(ProjectUITestData):
    def section(self, root):
        heading = by_id(root, 'projects-heading')
        for node in heading.ancestors():
            if node.tag == 'section':
                return node
        self.fail('projects heading is not inside a <section>')

    def test_section_is_labelled_card_before_members(self):
        """spec 04 AC-21 / AC-7: the projects section is a labelled .card
        with a count badge, placed before the members section."""
        pages = self.pages()
        for name in ('workspace_owner', 'workspace_member', 'workspace_empty'):
            root = pages[name]
            with self.subTest(page=name):
                section = self.section(root)
                self.assertEqual(section.attrs.get('aria-labelledby'), 'projects-heading')
                self.assertIn('card', section.classes)
                self.assertIsNotNone(section.find(class_='badge'))
                members = by_id(root, 'members-heading')
                self.assertLess(section.order, members.order)

    def test_header_action_only_when_projects_exist(self):
        """spec 04 AC-7 / AC-8 (plan Files changed): with projects the
        header shows "New project"; when empty, the empty state's own
        create link is the single create action.

        spec 05 AC-22 (step 04 Q-41, plan 05 D-4): the empty state's action
        now uses the same label as the header, "New project" (was "Create a
        project")."""
        pages = self.pages()
        create = self.create_url(self.apollo)
        section = self.section(pages['workspace_owner'])
        links = [a for a in section.find_all('a') if a.attrs.get('href') == create]
        self.assertEqual([a.norm_text() for a in links], ['New project'])
        self.assertIn('btn-primary', links[0].classes)

        section = self.section(pages['workspace_empty'])
        create = self.create_url(self.empty_ws)
        links = [a for a in section.find_all('a') if a.attrs.get('href') == create]
        self.assertEqual([a.norm_text() for a in links], ['New project'])
        self.assertIn('btn-primary', links[0].classes)
        self.assertIn('No projects yet.', section.norm_text())

    def test_create_action_label_is_new_project_everywhere(self):
        """spec 05 AC-22 (D-4): the action that opens the create form reads
        "New project" in the header and in the empty state, never "Create a
        project"; the create page's h1 is "New project" and its submit
        button, a different action, says "Create project"."""
        pages = self.pages()
        for name in ('workspace_owner', 'workspace_member', 'workspace_empty'):
            with self.subTest(page=name):
                section = self.section(pages[name])
                self.assertNotIn('Create a project', section.norm_text())
                self.assertIn('New project', section.norm_text())
        create = main_of(pages['create'])
        self.assertEqual(create.find('h1').norm_text(), 'New project')
        self.assertEqual(
            create.find('button', type='submit').norm_text(), 'Create project'
        )

    def test_project_page_back_link_reads_back_to_workspace(self):
        """spec 05 AC-22 (step 04 Q-40): the project page's back link text is
        "Back to Apollo" and still links to Apollo's workspace page; the
        name keeps its own wrap-anywhere element."""
        pages = self.pages()
        for name in ('detail', 'detail_empty'):
            with self.subTest(page=name):
                main = main_of(pages[name])
                back = main.find_all('a', href=self.workspace_url(self.apollo))
                self.assertEqual(len(back), 1)
                self.assertEqual(back[0].norm_text(), 'Back to Apollo')
                self.assertLess(back[0].order, main.find('h1').order)
                holders = [
                    n for n in back[0].iter()
                    if n.norm_text() == 'Apollo' and 'wrap-anywhere' in n.classes
                ]
                self.assertEqual(len(holders), 1)


class TargetsAndFieldsTests(ProjectUITestData):
    def test_links_and_buttons_have_minimum_height(self):
        """spec 04 AC-21 (HTML part): every link and button in <main> on the
        new pages has min-h-11 or a .btn-* class (≥ 24px); the textarea
        keeps the field minimum height."""
        rules = component_rules()
        self.assertIn('min-h-28', rules['.form-field textarea'])
        self.assertIn('min-h-11', rules['.form-field textarea'])
        pages = self.pages()
        for name, root in pages.items():
            main = main_of(root)
            targets = main.find_all('a') + main.find_all('button')
            for node in targets:
                if 'link' in node.classes:
                    continue
                with self.subTest(page=name, target=node.norm_text()):
                    has_class = 'min-h-11' in node.classes or any(
                        c.startswith('btn-') for c in node.classes
                    )
                    self.assertTrue(has_class, node)
                    self.assertGreaterEqual(effective_min_h(node, rules), 24)

    def test_textarea_rule_in_components_layer(self):
        """spec 04 AC-21: the textarea rule lives in @layer components.

        Step 04 Q-47: asserted on the parsed @apply tokens of the components
        layer, not on an exact CSS string, so formatting changes don't break
        it. component_rules() reads only @layer components."""
        rules = component_rules()
        self.assertIn('.form-field textarea', rules)
        self.assertLessEqual({'min-h-28', 'py-2'}, rules['.form-field textarea'])

    def test_fields_labelled(self):
        """spec 04 AC-21: every visible field on the create page has a
        visible label; the name is marked required and the description
        says "(optional)"."""
        root = self.pages()['create']
        form = main_of(root).find('form')
        self.assertEqual(form.attrs.get('method'), 'post')
        self.assertIsNotNone(form.find('input', name='csrfmiddlewaretoken'))
        fields = [
            n for n in form.iter()
            if n.tag in ('input', 'textarea', 'select')
            and n.attrs.get('type') != 'hidden'
        ]
        self.assertEqual([f.attrs.get('name') for f in fields], ['name', 'description'])
        for field in fields:
            with self.subTest(field=field.attrs.get('name')):
                label = form.find('label', for_=field.attrs.get('id'))
                self.assertIsNotNone(label)
                self.assertTrue(label.norm_text())
        name_label = form.find('label', for_='id_name')
        self.assertIsNotNone(name_label.find(class_='required-mark'))
        self.assertIn('required', form.find(id='id_name').attrs)
        self.assertIn('(optional)', form.find('label', for_='id_description').norm_text())
        self.assertEqual(form.find(id='id_description').tag, 'textarea')

    def test_errors_linked_to_fields(self):
        """spec 04 AC-21: invalid fields are aria-invalid and linked through
        aria-describedby to an <id>_error element next to them."""
        response = self.invalid_create()
        form = response.context['form']
        self.assertEqual(set(form.errors), {'name', 'description'})
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

    def test_form_is_project_form(self):
        """spec 04 AC-21: the create page renders ProjectForm through the
        shared partials (one form-field wrapper per visible field)."""
        response = self.get(self.create_url(self.apollo), self.bob)
        self.assertIsInstance(response.context['form'], ProjectForm)
        self.assertTemplateUsed(response, 'partials/form_body.html')
        self.assertTemplateUsed(response, 'partials/form_field.html')
        form = main_of(parse(response)).find('form')
        self.assertEqual(len(form.find_all('div', class_='form-field')), 2)


class WrappingTests(ProjectUITestData):
    def holder_of(self, root, text):
        nodes = [
            n for n in main_of(root).iter()
            if any(isinstance(c, str) and c.strip() == text for c in n.children)
        ]
        self.assertTrue(nodes, 'no element holds %r' % text)
        return nodes

    def test_user_text_can_wrap(self):
        """spec 04 AC-21: project and workspace names and the description
        carry wrap-anywhere, so long text never forces sideways scrolling."""
        long_name = 'L' * 100
        project = Project.objects.create(
            workspace=self.apollo, name=long_name, description='D' * 300
        )
        cases = {
            'workspace row': (self.workspace_url(self.apollo), long_name),
            'project h1': (self.detail_url(self.apollo, project), long_name),
            'description': (self.detail_url(self.apollo, project), 'D' * 300),
            'back link': (self.detail_url(self.apollo, project), 'Apollo'),
            'create subtitle': (self.create_url(self.apollo), 'Apollo'),
        }
        for label, (url, text) in cases.items():
            with self.subTest(case=label):
                root = parse(self.get(url, self.bob))
                for node in self.holder_of(root, text):
                    self.assertIn('wrap-anywhere', node.classes)


class ConstraintTests(ProjectUITestData):
    def test_templates_use_tokens_only(self):
        """spec 04 AC-21: the new and changed templates use semantic colour
        tokens only (no palette classes, no raw hex) and never |safe."""
        for path in NEW_OR_CHANGED_TEMPLATES:
            source = path.read_text(encoding='utf-8')
            with self.subTest(template=path.name):
                self.assertEqual(PALETTE.findall(source), [])
                self.assertEqual(HEX_COLOUR.findall(source), [])
                self.assertNotIn('|safe', source)
                self.assertNotIn('autoescape off', source)
                self.assertNotIn('<script', source)
                self.assertNotIn('<link', source)

    def test_base_template_textarea_rule_uses_no_palette(self):
        """spec 04 AC-21: base.html's style additions stay token-only."""
        source = BASE_TEMPLATE.read_text(encoding='utf-8')
        source = source.replace(css_block(tailwind_css(), '@theme'), '')
        self.assertEqual(PALETTE.findall(source), [])
        self.assertEqual(HEX_COLOUR.findall(source), [])

    def test_no_new_scripts_or_stylesheets(self):
        """spec 04 AC-21: the only script is the Tailwind CDN; no stylesheet,
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
        """spec 04 AC-21: every inline SVG on the new pages is aria-hidden."""
        for name, root in self.pages().items():
            svgs = root.find_all('svg')
            self.assertTrue(svgs)
            for svg in svgs:
                with self.subTest(page=name, svg=svg.attrs.get('class')):
                    self.assertEqual(svg.attrs.get('aria-hidden'), 'true')

    def test_motion_only_behind_motion_safe(self):
        """spec 04 AC-21: any transition or animation class on the new pages
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
