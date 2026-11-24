"""
Acceptance tests for issue #3: piped wikilinks `[[Page Name|link text]]`.
"""

import unittest

import markdown
from markdown.extensions.wikilinks import WikiLinkExtension


class TestPipedWikiLinks(unittest.TestCase):

    def setUp(self):
        self.md = markdown.Markdown(extensions=['wikilinks'])

    def test_ac_fr_001_01_basic_piped_link(self):
        self.assertEqual(
            self.md.convert('Read [[Installation Guide|see the install docs]] first.'),
            '<p>Read <a class="wikilink" href="/Installation_Guide/">see the install docs</a> first.</p>'
        )

    def test_ac_fr_001_02_whitespace_ignored(self):
        self.assertEqual(
            self.md.convert('[[  Installation Guide  |  see the install docs  ]]'),
            '<p><a class="wikilink" href="/Installation_Guide/">see the install docs</a></p>'
        )

    def test_ac_fr_001_03_settings_apply(self):
        md = markdown.Markdown(
            extensions=[WikiLinkExtension(base_url='/wiki/', end_url='.html', html_class='foo')]
        )
        self.assertEqual(
            md.convert('[[Installation Guide|see the install docs]]'),
            '<p><a class="foo" href="/wiki/Installation_Guide.html">see the install docs</a></p>'
        )

    def test_ac_fr_001_04_build_url_receives_page_name(self):
        calls = []

        def my_url_builder(label, base, end):
            calls.append((label, base, end))
            return '/bar/'

        md = markdown.Markdown(extensions=[WikiLinkExtension(build_url=my_url_builder)])
        self.assertEqual(
            md.convert('[[foo|Some Text]]'),
            '<p><a class="wikilink" href="/bar/">Some Text</a></p>'
        )
        self.assertEqual(calls, [('foo', '/', '/')])

    def test_ac_fr_001_05_meta_data_overrides(self):
        md = markdown.Markdown(extensions=['meta', 'wikilinks'])
        text = (
            'wiki_base_url: http://example.com/\n'
            'wiki_end_url:   .html\n'
            'wiki_html_class:\n'
            '\n'
            'See [[Installation Guide|the docs]].'
        )
        self.assertEqual(
            md.convert(text),
            '<p>See <a href="http://example.com/Installation_Guide.html">the docs</a>.</p>'
        )

    def test_ac_fr_001_06_punctuation_in_link_text(self):
        self.assertEqual(
            self.md.convert('[[Installation Guide|the install docs, v2.0!]]'),
            '<p><a class="wikilink" href="/Installation_Guide/">the install docs, v2.0!</a></p>'
        )

    def test_ac_fr_001_07_multiple_pipes_not_a_link(self):
        out = self.md.convert('[[a|b|c]]')
        self.assertNotIn('<a', out)
        self.assertEqual(out, '<p>[[a|b|c]]</p>')

    def test_ac_fr_002_01_empty_link_text_falls_back(self):
        self.assertEqual(
            self.md.convert('[[Installation Guide|]]'),
            '<p><a class="wikilink" href="/Installation_Guide/">Installation Guide</a></p>'
        )

    def test_ac_fr_002_02_whitespace_link_text_falls_back(self):
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

    def test_ac_fr_002_04_empty_page_name_no_link(self):
        self.assertEqual(self.md.convert('foo [[ |some text]] bar'), '<p>foo  bar</p>')
        self.assertEqual(self.md.convert('foo [[ ]] bar'), '<p>foo  bar</p>')


if __name__ == '__main__':
    unittest.main()
