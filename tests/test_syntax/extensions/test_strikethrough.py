"""
Python Markdown

A Python implementation of John Gruber's Markdown.

Documentation: https://python-markdown.github.io/
GitHub: https://github.com/Python-Markdown/markdown/
PyPI: https://pypi.org/project/Markdown/

Started by Manfred Stienstra (http://www.dwerg.net/).
Maintained for a few years by Yuri Takhteyev (http://www.freewisdom.org).
Currently maintained by Waylan Limberg (https://github.com/waylan),
Dmitry Shachnev (https://github.com/mitya57) and Isaac Muse (https://github.com/facelessuser).

Copyright 2007-2023 The Python Markdown Project (v. 1.7 and later)
Copyright 2004, 2005, 2006 Yuri Takhteyev (v. 0.2-1.6b)
Copyright 2004 Manfred Stienstra (the original version)

License: BSD (see LICENSE.md for details).
"""

import os

import markdown
from markdown.test_tools import TestCase
from markdown.util import get_installed_extensions
from markdown.extensions.strikethrough import StrikethroughExtension


class TestStrikethrough(TestCase):

    default_kwargs = {'extensions': [StrikethroughExtension()]}

    def test_entry_point_declared(self):
        # AC-FR-001-01: the short name is provided by this entry point (ADR-2).
        path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'pyproject.toml')
        with open(path, encoding='utf-8') as f:
            content = f.read()
        self.assertIn(
            "strikethrough = 'markdown.extensions.strikethrough:StrikethroughExtension'",
            content
        )

    def test_short_name(self):
        # AC-FR-001-01
        if not any(ep.name == 'strikethrough' for ep in get_installed_extensions()):
            self.skipTest('Package metadata must be reinstalled to register the entry point.')
        self.assertEqual(
            markdown.markdown('~~foo~~', extensions=['strikethrough']),
            '<p><del>foo</del></p>'
        )

    def test_dotted_path(self):
        # AC-FR-001-02
        self.assertEqual(
            markdown.markdown('~~foo~~', extensions=['markdown.extensions.strikethrough']),
            '<p><del>foo</del></p>'
        )

    def test_disabled_by_default(self):
        # AC-FR-001-03
        self.assertEqual(
            markdown.markdown('~~foo~~ and *bar*'),
            '<p>~~foo~~ and <em>bar</em></p>'
        )
        self.assertNotIn('~', markdown.Markdown().ESCAPED_CHARS)

    def test_escaped_chars_per_instance(self):
        md = markdown.Markdown(extensions=[StrikethroughExtension()])
        self.assertIn('~', md.ESCAPED_CHARS)
        self.assertEqual(md.ESCAPED_CHARS.count('~'), 1)
        self.assertNotIn('~', markdown.Markdown().ESCAPED_CHARS)

    def test_fenced_code(self):
        # AC-FR-001-04
        self.assertMarkdownRenders(
            '~~~\n~~foo~~\n~~~',
            '<pre><code>~~foo~~\n</code></pre>',
            extensions=[StrikethroughExtension(), 'fenced_code']
        )

    def test_in_sentence(self):
        # AC-FR-002-01
        self.assertMarkdownRenders(
            'This is ~~withdrawn~~ text.',
            '<p>This is <del>withdrawn</del> text.</p>'
        )

    def test_nested_inline(self):
        # AC-FR-002-02
        self.assertMarkdownRenders(
            '~~**bold** *em* [link](http://example.com)~~',
            '<p><del><strong>bold</strong> <em>em</em> <a href="http://example.com">link</a></del></p>'
        )

    def test_inside_emphasis(self):
        # AC-FR-002-03
        self.assertMarkdownRenders(
            '*a ~~b~~ c*',
            '<p><em>a <del>b</del> c</em></p>'
        )

    def test_inside_strong(self):
        self.assertMarkdownRenders(
            '**a ~~b~~ c**',
            '<p><strong>a <del>b</del> c</strong></p>'
        )

    def test_multiple_spans(self):
        # AC-FR-002-04
        self.assertMarkdownRenders(
            '~~one~~ and ~~two~~',
            '<p><del>one</del> and <del>two</del></p>'
        )

    def test_code_span(self):
        # AC-FR-002-05
        self.assertMarkdownRenders(
            '`~~code~~`',
            '<p><code>~~code~~</code></p>'
        )

    def test_single_tilde(self):
        # AC-FR-003-01
        self.assertMarkdownRenders(
            'about ~5 minutes, ~foo~',
            '<p>about ~5 minutes, ~foo~</p>'
        )

    def test_unclosed(self):
        # AC-FR-003-02
        self.assertMarkdownRenders(
            'an ~~unclosed span',
            '<p>an ~~unclosed span</p>'
        )

    def test_whitespace_flanked(self):
        # AC-FR-003-03
        self.assertMarkdownRenders(
            'a ~~ b ~~ c',
            '<p>a ~~ b ~~ c</p>'
        )

    def test_three_tildes(self):
        # AC-FR-003-04
        self.assertMarkdownRenders(
            '~~~foo~~~',
            '<p>~~~foo~~~</p>'
        )

    def test_escaped(self):
        # AC-FR-003-05
        self.assertMarkdownRenders(
            '\\~\\~foo\\~\\~',
            '<p>~~foo~~</p>'
        )

    def test_intraword(self):
        self.assertMarkdownRenders(
            'a~~b~~c',
            '<p>a<del>b</del>c</p>'
        )

    def test_multiline(self):
        self.assertMarkdownRenders(
            '~~foo\nbar~~',
            '<p><del>foo\nbar</del></p>'
        )

    def test_emphasis_unchanged(self):
        self.assertMarkdownRenders(
            '***a** b* _c_ __d__',
            '<p><em><strong>a</strong> b</em> <em>c</em> <strong>d</strong></p>'
        )
