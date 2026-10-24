"""Shared HTML and CSS helpers for the UI tests (step 05 Q-46).

This module holds no tests and its name doesn't match the runner's
"test*.py" pattern, so it is never collected. core, projects and tasks UI
tests import from here instead of from each other's test modules.

HTML is parsed with the stdlib html.parser into a small tree, so the tests
don't depend on attribute order or whitespace. CSS helpers read the
Tailwind <style type="text/tailwindcss"> block in base.html.
"""
import re
from html.parser import HTMLParser
from pathlib import Path

from django.apps import apps
from django.conf import settings

TAILWIND_CDN = 'https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4'
BASE_TEMPLATE = settings.BASE_DIR / 'templates' / 'base.html'

# Tailwind palette colour classes (e.g. bg-indigo-600). Templates use the
# semantic tokens from @theme instead (spec 03 AC-3/AC-4).
PALETTE_CLASS = re.compile(
    r'\b(?:bg|text|border|ring|divide|outline|decoration|fill|stroke)-'
    r'(?:slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|'
    r'emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)-\d{2,3}\b'
)
# Raw hex colours; allowed only inside base.html's @theme block.
HEX_COLOUR = re.compile(r'#[0-9A-Fa-f]{6}\b|#[0-9A-Fa-f]{3}\b')


# --------------------------------------------------------------------------
# A tiny HTML tree built with the stdlib parser
# --------------------------------------------------------------------------

VOID_TAGS = {
    'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link',
    'meta', 'source', 'track', 'wbr',
}
FOCUSABLE_TAGS = {'a', 'button', 'input', 'select', 'textarea', 'summary'}


class Node:
    def __init__(self, tag, attrs, parent, order):
        self.tag = tag
        self.attrs = {k: (v if v is not None else '') for k, v in attrs}
        self.parent = parent
        self.order = order
        self.children = []  # Node or str

    @property
    def classes(self):
        return self.attrs.get('class', '').split()

    def text(self):
        parts = []
        for child in self.children:
            parts.append(child if isinstance(child, str) else child.text())
        return ''.join(parts)

    def norm_text(self):
        return ' '.join(self.text().split())

    def iter(self):
        for child in self.children:
            if isinstance(child, Node):
                yield child
                yield from child.iter()

    def find_all(self, tag=None, **attrs):
        """Descendants matching tag and exact attribute values. Use
        class_='x' to require a class token."""
        wanted_class = attrs.pop('class_', None)
        result = []
        for node in self.iter():
            if tag is not None and node.tag != tag:
                continue
            if wanted_class is not None and wanted_class not in node.classes:
                continue
            if all(
                node.attrs.get(k.rstrip('_').replace('_', '-')) == v
                for k, v in attrs.items()
            ):
                result.append(node)
        return result

    def find(self, tag=None, **attrs):
        found = self.find_all(tag, **attrs)
        return found[0] if found else None

    def ancestors(self):
        node = self.parent
        while node is not None:
            yield node
            node = node.parent

    def has_ancestor(self, predicate):
        return any(predicate(a) for a in self.ancestors())

    def __repr__(self):
        return '<%s %r>' % (self.tag, self.attrs)


class TreeBuilder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node('#root', [], None, 0)
        self.stack = [self.root]
        self.counter = 0

    def _new(self, tag, attrs):
        self.counter += 1
        node = Node(tag, attrs, self.stack[-1], self.counter)
        self.stack[-1].children.append(node)
        return node

    def handle_starttag(self, tag, attrs):
        node = self._new(tag, attrs)
        if tag not in VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self._new(tag, attrs)

    def handle_endtag(self, tag):
        if tag in VOID_TAGS:
            return
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def parse(html):
    if not isinstance(html, str):
        html = html.content.decode()
    builder = TreeBuilder()
    builder.feed(html)
    builder.close()
    return builder.root


def by_id(root, element_id):
    for node in root.iter():
        if node.attrs.get('id') == element_id:
            return node
    return None


def in_nav(node):
    return node.has_ancestor(lambda a: a.tag == 'nav')


def main_of(root):
    main = root.find('main')
    assert main is not None, 'page has no <main>'
    return main


# --------------------------------------------------------------------------
# The style block in base.html
# --------------------------------------------------------------------------

def base_source():
    return BASE_TEMPLATE.read_text(encoding='utf-8')


def tailwind_css():
    match = re.search(
        r'<style type="text/tailwindcss">(.*?)</style>', base_source(), re.S
    )
    assert match, 'base.html has no <style type="text/tailwindcss"> block'
    return match.group(1)


def css_block(css, opener):
    """Return the body of the first `opener { ... }` block, matching braces."""
    start = css.find(opener)
    assert start != -1, '%s not found in the style block' % opener
    brace = css.index('{', start)
    depth = 0
    for i in range(brace, len(css)):
        if css[i] == '{':
            depth += 1
        elif css[i] == '}':
            depth -= 1
            if depth == 0:
                return css[brace + 1:i]
    raise AssertionError('unbalanced braces after %s' % opener)


def strip_comments(css):
    """Remove /* ... */ comments so they never leak into selectors."""
    return re.sub(r'/\*.*?\*/', ' ', css, flags=re.S)


def split_top_level(text, sep=','):
    """Split on `sep` outside any (...) or [...]."""
    parts, depth, current = [], 0, []
    for ch in text:
        if ch in '([':
            depth += 1
        elif ch in ')]':
            depth -= 1
        if ch == sep and depth == 0:
            parts.append(''.join(current))
            current = []
        else:
            current.append(ch)
    parts.append(''.join(current))
    return parts


def ordered_apply_rules(block):
    """List of (position, selector, tokens) for each selector of each
    `selectors { @apply ...; }` rule, in source order. Comments are
    stripped first. Selectors of one rule share a position."""
    result = []
    pattern = r'([^{}]+)\{\s*@apply\s+([^;]+);\s*\}'
    for position, (selectors, body) in enumerate(
        re.findall(pattern, strip_comments(block))
    ):
        tokens = set(body.split())
        for selector in split_top_level(selectors):
            selector = ' '.join(selector.split())
            if selector:
                result.append((position, selector, tokens))
    return result


def apply_rules(block):
    """Map each selector to the set of utilities it @applies."""
    rules = {}
    for _, selector, tokens in ordered_apply_rules(block):
        rules.setdefault(selector, set()).update(tokens)
    return rules


def specificity(selector):
    """CSS selector specificity as (ids, classes/attrs/pseudo-classes,
    types/pseudo-elements). :not() and :is() count their most specific
    argument; :where() counts zero."""
    a = b = c = 0
    s = selector
    while True:
        match = re.search(r':(not|is|has|where)\(', s)
        if not match:
            break
        depth, i = 1, match.end()
        while depth:
            if s[i] == '(':
                depth += 1
            elif s[i] == ')':
                depth -= 1
            i += 1
        argument = s[match.end():i - 1]
        if match.group(1) != 'where':
            best = max(specificity(p.strip()) for p in split_top_level(argument))
            a, b, c = a + best[0], b + best[1], c + best[2]
        s = s[:match.start()] + s[i:]
    for pattern, kind in (
        (r'\[[^\]]*\]', 'b'), (r'#[\w-]+', 'a'), (r'\.[\w-]+', 'b'),
        (r'::[\w-]+', 'c'), (r':[\w-]+', 'b'),
    ):
        count = len(re.findall(pattern, s))
        s = re.sub(pattern, ' ', s)
        if kind == 'a':
            a += count
        elif kind == 'b':
            b += count
        else:
            c += count
    c += len(re.findall(r'(?<![\w-])[A-Za-z][\w-]*', s))
    return (a, b, c)


def subject_type(selector):
    """Element type of the selector's last compound, or None (any element)."""
    last = re.split(r'\s*[>+~]\s*|\s+', selector.strip())[-1]
    match = re.match(r'[A-Za-z][\w-]*', last)
    return match.group(0) if match else None


def component_rules():
    return apply_rules(css_block(tailwind_css(), '@layer components'))


def theme_tokens():
    block = css_block(tailwind_css(), '@theme')
    return {
        name: value.upper()
        for name, value in re.findall(r'--color-([a-z-]+):\s*(#[0-9A-Fa-f]{6})\s*;', block)
    }


def min_h_px(tokens):
    """Largest min-h-N (N in Tailwind 4px steps) among the tokens, in px."""
    best = 0
    for token in tokens:
        match = re.fullmatch(r'(?:[a-z-]+:)?min-h-(\d+(?:\.\d+)?)', token)
        if match:
            best = max(best, float(match.group(1)) * 4)
    return best


def effective_min_h(node, rules):
    """Minimum height from the node's own utilities or its component class."""
    tokens = set(node.classes)
    for cls in node.classes:
        tokens |= rules.get('.' + cls, set())
    return min_h_px(tokens)


# --------------------------------------------------------------------------
# Small page-level helpers
# --------------------------------------------------------------------------

def heading_levels(root):
    """Heading levels (1-6) in document order."""
    return [int(n.tag[1]) for n in root.iter() if re.fullmatch(r'h[1-6]', n.tag)]


def local_template_dirs():
    """The templates/ folder of every project app in INSTALLED_APPS (apps
    that live inside BASE_DIR, not Django's own), when it has one."""
    base = Path(settings.BASE_DIR).resolve()
    dirs = []
    for config in apps.get_app_configs():
        path = Path(config.path).resolve()
        if base not in path.parents:
            continue
        templates = path / 'templates'
        if templates.is_dir():
            dirs.append(templates)
    return dirs
