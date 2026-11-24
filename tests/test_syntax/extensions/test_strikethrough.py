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

import markdown
from markdown.test_tools import TestCase
from markdown.extensions.strikethrough import StrikethroughExtension

EXT = 'markdown.extensions.strikethrough'


class TestStrikethrough(TestCase):

    default_kwargs = {'extensions': [EXT]}

    def test_simple(self):
        self.assertMarkdownRenders(
            'This is ~~deleted~~ text.',
            '<p>This is <del>deleted</del> text.</p>'
        )

    def test_disabled_by_default(self):
        self.assertMarkdownRenders(
            'This is ~~deleted~~ text.',
            '<p>This is ~~deleted~~ text.</p>',
            extensions=[]
        )

    def test_extension_instance(self):
        self.assertMarkdownRenders(
            '~~gone~~',
            '<p><del>gone</del></p>',
            extensions=[StrikethroughExtension()]
        )

    def test_nested_inline(self):
        self.assertMarkdownRenders(
            '~~a **bold** and *em* [link](http://example.com)~~',
            '<p><del>a <strong>bold</strong> and <em>em</em> <a href="http://example.com">link</a></del></p>'
        )

    def test_inside_strong(self):
        self.assertMarkdownRenders(
            '**bold ~~struck~~**',
            '<p><strong>bold <del>struck</del></strong></p>'
        )

    def test_single_tilde(self):
        self.assertMarkdownRenders(
            'about ~5 minutes and ~text~',
            '<p>about ~5 minutes and ~text~</p>'
        )

    def test_unclosed(self):
        self.assertMarkdownRenders(
            'this ~~is not closed',
            '<p>this ~~is not closed</p>'
        )

    def test_multiple(self):
        self.assertMarkdownRenders(
            '~~one~~ and ~~two~~',
            '<p><del>one</del> and <del>two</del></p>'
        )

    def test_whitespace_flanked(self):
        self.assertMarkdownRenders(
            '~~ text ~~',
            '<p>~~ text ~~</p>'
        )

    def test_code_span(self):
        self.assertMarkdownRenders(
            '`~~code~~`',
            '<p><code>~~code~~</code></p>'
        )

    def test_tilde_fence(self):
        self.assertMarkdownRenders(
            '~~~\n~~x~~\n~~~',
            '<pre><code>~~x~~\n</code></pre>',
            extensions=[EXT, 'fenced_code']
        )

    def test_emphasis_unchanged(self):
        src = '*em* and **strong** and ***both***'
        self.assertEqual(
            markdown.markdown(src, extensions=[EXT]),
            markdown.markdown(src)
        )

    def test_with_legacy_em(self):
        self.assertMarkdownRenders(
            '~~a _b_~~ and _connected_words_',
            '<p><del>a <em>b</em></del> and <em>connected</em>words_</p>',
            extensions=[EXT, 'markdown.extensions.legacy_em']
        )

    def test_without_em_strong(self):
        md = markdown.Markdown()
        md.inlinePatterns.deregister('em_strong')
        md.delimiters = None
        StrikethroughExtension().extendMarkdown(md)
        self.assertIn('strikethrough', md.inlinePatterns)
        self.assertEqual(md.convert('~~x~~ *y*'), '<p><del>x</del> *y*</p>')

    def test_reused_instance(self):
        md = markdown.Markdown(extensions=[EXT])
        self.assertEqual(md.convert('~~a~~ ~~b'), '<p><del>a</del> ~~b</p>')
        md.reset()
        self.assertEqual(md.convert('~~c~~'), '<p><del>c</del></p>')
