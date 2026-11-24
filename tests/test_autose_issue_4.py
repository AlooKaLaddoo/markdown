"""
Acceptance tests for issue #4: GitHub-style ~~strikethrough~~ extension.
"""

import markdown
from markdown.test_tools import TestCase


class TestStrikethroughLoading(TestCase):

    def test_ac_fr_001_01_load_by_short_name(self):
        self.assertEqual(
            markdown.markdown('~~foo~~', extensions=['strikethrough']),
            '<p><del>foo</del></p>'
        )

    def test_ac_fr_001_02_load_by_dotted_path(self):
        self.assertEqual(
            markdown.markdown('~~foo~~', extensions=['markdown.extensions.strikethrough']),
            '<p><del>foo</del></p>'
        )

    def test_ac_fr_001_03_unchanged_without_extension(self):
        self.assertEqual(
            markdown.markdown('~~foo~~ and *bar*'),
            '<p>~~foo~~ and <em>bar</em></p>'
        )

    def test_ac_fr_001_04_fenced_code_alongside(self):
        self.assertEqual(
            markdown.markdown('~~~\n~~foo~~\n~~~', extensions=['strikethrough', 'fenced_code']),
            '<pre><code>~~foo~~\n</code></pre>'
        )


class TestStrikethroughRendering(TestCase):

    default_kwargs = {'extensions': ['strikethrough']}

    def test_ac_fr_002_01_plain_in_sentence(self):
        self.assertMarkdownRenders(
            'This is ~~withdrawn~~ text.',
            '<p>This is <del>withdrawn</del> text.</p>'
        )

    def test_ac_fr_002_02_nested_inline_markup(self):
        self.assertMarkdownRenders(
            '~~**bold** *em* [link](http://example.com)~~',
            '<p><del><strong>bold</strong> <em>em</em> <a href="http://example.com">link</a></del></p>'
        )

    def test_ac_fr_002_03_inside_emphasis(self):
        self.assertMarkdownRenders(
            '*a ~~b~~ c*',
            '<p><em>a <del>b</del> c</em></p>'
        )

    def test_ac_fr_002_04_multiple_spans(self):
        self.assertMarkdownRenders(
            '~~one~~ and ~~two~~',
            '<p><del>one</del> and <del>two</del></p>'
        )

    def test_ac_fr_002_05_code_span_unaffected(self):
        self.assertMarkdownRenders(
            '`~~code~~`',
            '<p><code>~~code~~</code></p>'
        )


class TestStrikethroughLiteralTildes(TestCase):

    default_kwargs = {'extensions': ['strikethrough']}

    def test_ac_fr_003_01_single_tildes_literal(self):
        self.assertMarkdownRenders(
            'about ~5 minutes, ~foo~',
            '<p>about ~5 minutes, ~foo~</p>'
        )

    def test_ac_fr_003_02_unclosed_double_tilde(self):
        self.assertMarkdownRenders(
            'an ~~unclosed span',
            '<p>an ~~unclosed span</p>'
        )

    def test_ac_fr_003_03_whitespace_flanked_delimiters(self):
        self.assertMarkdownRenders(
            'a ~~ b ~~ c',
            '<p>a ~~ b ~~ c</p>'
        )

    def test_ac_fr_003_04_three_tildes_not_delimiter(self):
        self.assertMarkdownRenders(
            '~~~foo~~~',
            '<p>~~~foo~~~</p>'
        )

    def test_ac_fr_003_05_escaped_tildes_literal(self):
        self.assertMarkdownRenders(
            '\\~\\~foo\\~\\~',
            '<p>~~foo~~</p>'
        )
