"""Acceptance tests for issue #4: opt-in `strikethrough` extension."""

import unittest

import markdown


class TestIssue4Acceptance(unittest.TestCase):

    def render(self, source, extensions=('strikethrough',)):
        return markdown.markdown(source, extensions=list(extensions))

    # FR-001

    def test_ac_fr_001_01_short_name(self):
        self.assertEqual(
            self.render('This is ~~deleted~~ text.'),
            '<p>This is <del>deleted</del> text.</p>'
        )

    def test_ac_fr_001_02_disabled_by_default(self):
        self.assertEqual(
            markdown.markdown('This is ~~deleted~~ text.'),
            '<p>This is ~~deleted~~ text.</p>'
        )

    def test_ac_fr_001_03_dotted_path(self):
        self.assertEqual(
            self.render('~~gone~~', ['markdown.extensions.strikethrough']),
            '<p><del>gone</del></p>'
        )

    # FR-002

    def test_ac_fr_002_01_nested_inline_markup(self):
        self.assertEqual(
            self.render('~~a **bold** and *em* [link](http://example.com)~~'),
            '<p><del>a <strong>bold</strong> and <em>em</em> '
            '<a href="http://example.com">link</a></del></p>'
        )

    def test_ac_fr_002_02_inside_strong(self):
        self.assertEqual(
            self.render('**bold ~~struck~~**'),
            '<p><strong>bold <del>struck</del></strong></p>'
        )

    def test_ac_fr_002_03_single_tilde_literal(self):
        self.assertEqual(
            self.render('about ~5 minutes and ~text~'),
            '<p>about ~5 minutes and ~text~</p>'
        )

    def test_ac_fr_002_04_unclosed_literal(self):
        self.assertEqual(
            self.render('this ~~is not closed'),
            '<p>this ~~is not closed</p>'
        )

    def test_ac_fr_002_05_multiple_spans(self):
        self.assertEqual(
            self.render('~~one~~ and ~~two~~'),
            '<p><del>one</del> and <del>two</del></p>'
        )

    def test_ac_fr_002_06_code_span_literal(self):
        self.assertEqual(
            self.render('`~~code~~`'),
            '<p><code>~~code~~</code></p>'
        )

    def test_ac_fr_002_07_tilde_fenced_code(self):
        self.assertEqual(
            self.render('~~~\n~~x~~\n~~~', ['strikethrough', 'fenced_code']),
            '<pre><code>~~x~~\n</code></pre>'
        )

    def test_ac_fr_002_08_emphasis_unaffected(self):
        source = '*em* and **strong** and ***both***'
        self.assertEqual(self.render(source), markdown.markdown(source))


if __name__ == '__main__':
    unittest.main()
