"""
Acceptance tests for issue #3: piped wikilinks `[[Page Name|link text]]`.
"""

import unittest

import markdown
from markdown.extensions.wikilinks import WikiLinkExtension


class TestPipedWikiLinks(unittest.TestCase):
    """ FR-001: render piped wikilinks with custom link text. """

    def setUp(self):
        self.md = markdown.Markdown(extensions=['wikilinks'])

    def test_ac_fr_001_01_basic_piped_link(self):
        self.assertEqual(
            self.md.convert('[[Installation Guide|see the install docs]]'),
            '<p><a class="wikilink" href="/Installation_Guide/">see the install docs</a></p>'
        )

    def test_ac_fr_001_02_whitespace_ignored(self):
        self.assertEqual(
            self.md.convert('[[ Installation Guide | see the install docs ]]'),
            '<p><a class="wikilink" href="/Installation_Guide/">see the install docs</a></p>'
        )

    def test_ac_fr_001_03_simple_settings(self):
        self.assertEqual(
            markdown.markdown(
                'Some text with a [[WikiLink|a link]].',
                extensions=[WikiLinkExtension(base_url='/wiki/', end_url='.html', html_class='foo')]
            ),
            '<p>Some text with a <a class="foo" href="/wiki/WikiLink.html">a link</a>.</p>'
        )

    def test_ac_fr_001_04_empty_html_class(self):
        md = markdown.Markdown(
            extensions=['wikilinks'],
            extension_configs={
                'wikilinks': {
                    'base_url': 'http://example.com/',
                    'end_url': '.html',
                    'html_class': '',
                }
            }
        )
        self.assertEqual(
            md.convert('[[WikiLink|a link]]'),
            '<p><a href="http://example.com/WikiLink.html">a link</a></p>'
        )

    def test_ac_fr_001_05_metadata_overrides(self):
        text = (
            'wiki_base_url: http://example.com/\n'
            'wiki_end_url:   .html\n'
            'wiki_html_class:\n'
            '\n'
            'Some text with a [[WikiLink|a link]].'
        )
        md = markdown.Markdown(extensions=['meta', 'wikilinks'])
        self.assertEqual(
            md.convert(text),
            '<p>Some text with a <a href="http://example.com/WikiLink.html">a link</a>.</p>'
        )

    def test_ac_fr_001_06_build_url_receives_page_name(self):
        calls = []

        def my_url_builder(label, base, end):
            calls.append((label, base, end))
            return '/bar/'

        md = markdown.Markdown(extensions=[WikiLinkExtension(build_url=my_url_builder)])
        self.assertEqual(
            md.convert('[[ foo | some text ]]'),
            '<p><a class="wikilink" href="/bar/">some text</a></p>'
        )
        self.assertEqual(calls, [('foo', '/', '/')])

    def test_ac_fr_001_07_internal_whitespace_preserved(self):
        self.assertEqual(
            self.md.convert('[[foo|double  spaces]]'),
            '<p><a class="wikilink" href="/foo/">double  spaces</a></p>'
        )

    def test_ac_fr_001_08_special_characters_escaped(self):
        self.assertEqual(
            self.md.convert('[[foo|Q&A <docs>]]'),
            '<p><a class="wikilink" href="/foo/">Q&amp;A &lt;docs&gt;</a></p>'
        )


class TestPipedWikiLinksFallback(unittest.TestCase):
    """ FR-002: fallback to page name; plain wikilinks unchanged. """

    def setUp(self):
        self.md = markdown.Markdown(extensions=['wikilinks'])

    def test_ac_fr_002_01_empty_text_falls_back(self):
        self.assertEqual(
            self.md.convert('[[Installation Guide|]]'),
            '<p><a class="wikilink" href="/Installation_Guide/">Installation Guide</a></p>'
        )

    def test_ac_fr_002_02_whitespace_text_falls_back(self):
        self.assertEqual(
            self.md.convert('[[ Installation Guide |   ]]'),
            '<p><a class="wikilink" href="/Installation_Guide/">Installation Guide</a></p>'
        )

    def test_ac_fr_002_03_plain_wikilinks_unchanged(self):
        self.assertEqual(
            self.md.convert('Some text with a [[WikiLink]].'),
            '<p>Some text with a <a class="wikilink" href="/WikiLink/">WikiLink</a>.</p>'
        )
        self.assertEqual(
            self.md.convert('[[ foo bar_baz ]]'),
            '<p><a class="wikilink" href="/foo_bar_baz/">foo bar_baz</a></p>'
        )
        self.assertEqual(
            self.md.convert('foo [[ ]] bar'),
            '<p>foo  bar</p>'
        )

    def test_ac_fr_002_04_empty_page_name_no_link(self):
        output = self.md.convert('foo [[ |text]] bar')
        self.assertNotIn('<a', output)

    def test_ac_fr_002_05_multiple_pipes_literal(self):
        self.assertEqual(
            self.md.convert('[[a|b|c]]'),
            '<p>[[a|b|c]]</p>'
        )


if __name__ == '__main__':
    unittest.main()
