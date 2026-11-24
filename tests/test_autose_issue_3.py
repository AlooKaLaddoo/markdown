"""
Acceptance tests for issue #3: wikilinks custom link text `[[Page Name|link text]]`.
"""

import os
import unittest

import markdown
from markdown.extensions.wikilinks import WikiLinkExtension
from markdown.test_tools import TestCase


class TestWikiLinkCustomText(TestCase):
    """ FR-001: `[[Page Name|link text]]`. """

    def test_ac_fr_001_01_default_configuration(self):
        md = markdown.Markdown(extensions=['wikilinks'])
        self.assertEqual(
            md.convert('See [[Installation Guide|see the install docs]].'),
            '<p>See <a class="wikilink" href="/Installation_Guide/">see the install docs</a>.</p>'
        )

    def test_ac_fr_001_02_whitespace_ignored(self):
        md = markdown.Markdown(extensions=['wikilinks'])
        self.assertEqual(
            md.convert('[[ Installation Guide | see the install docs ]]'),
            '<p><a class="wikilink" href="/Installation_Guide/">see the install docs</a></p>'
        )

    def test_ac_fr_001_03_base_end_url_and_html_class(self):
        md = markdown.Markdown(extensions=[
            WikiLinkExtension(base_url='/wiki/', end_url='.html', html_class='foo')
        ])
        self.assertEqual(
            md.convert('[[WikiLink|the text]]'),
            '<p><a class="foo" href="/wiki/WikiLink.html">the text</a></p>'
        )

    def test_ac_fr_001_04_custom_build_url_gets_page_name(self):
        calls = []

        def f(label, base, end):
            calls.append(label)
            return '/x/' + label + '/'

        md = markdown.Markdown(extensions=[WikiLinkExtension(build_url=f)])
        self.assertEqual(
            md.convert('[[foo|bar]]'),
            '<p><a class="wikilink" href="/x/foo/">bar</a></p>'
        )
        self.assertEqual(calls, ['foo'])

    def test_ac_fr_001_05_meta_data_overrides(self):
        md = markdown.Markdown(extensions=['meta', 'wikilinks'])
        text = ('wiki_base_url: http://example.com/\n'
                'wiki_end_url:   .html\n'
                'wiki_html_class:\n'
                '\n'
                'Some text with a [[WikiLink|custom]].')
        self.assertEqual(
            md.convert(text),
            '<p>Some text with a <a href="http://example.com/WikiLink.html">custom</a>.</p>'
        )

    def test_ac_fr_001_06_only_first_pipe_separates(self):
        md = markdown.Markdown(extensions=['wikilinks'])
        self.assertEqual(
            md.convert('[[Page|a|b]]'),
            '<p><a class="wikilink" href="/Page/">a|b</a></p>'
        )

    def test_ac_fr_001_07_html_special_chars_escaped(self):
        md = markdown.Markdown(extensions=['wikilinks'])
        self.assertEqual(
            md.convert('[[Page|a & b]]'),
            '<p><a class="wikilink" href="/Page/">a &amp; b</a></p>'
        )


class TestWikiLinkFallbackAndCompat(TestCase):
    """ FR-002: fallback to page name and unchanged plain behaviour. """

    def test_ac_fr_002_01_empty_link_text_falls_back(self):
        md = markdown.Markdown(extensions=['wikilinks'])
        self.assertEqual(
            md.convert('[[Installation Guide|]]'),
            '<p><a class="wikilink" href="/Installation_Guide/">Installation Guide</a></p>'
        )

    def test_ac_fr_002_02_whitespace_link_text_falls_back(self):
        md = markdown.Markdown(extensions=['wikilinks'])
        self.assertEqual(
            md.convert('[[ Installation Guide |   ]]'),
            '<p><a class="wikilink" href="/Installation_Guide/">Installation Guide</a></p>'
        )

    def test_ac_fr_002_03_plain_wikilinks_unchanged(self):
        md = markdown.Markdown(extensions=['wikilinks'])
        self.assertEqual(
            md.convert('Some text with a [[WikiLink]].'),
            '<p>Some text with a <a class="wikilink" href="/WikiLink/">WikiLink</a>.</p>'
        )
        md.reset()
        self.assertEqual(
            md.convert('[[ foo bar_baz ]]'),
            '<p><a class="wikilink" href="/foo_bar_baz/">foo bar_baz</a></p>'
        )

    def test_ac_fr_002_03_existing_wikilinks_unit_tests_pass(self):
        from tests.test_extensions import TestWikiLinks
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestWikiLinks)
        result = unittest.TestResult()
        suite.run(result)
        self.assertGreater(result.testsRun, 0)
        self.assertEqual(result.failures, [])
        self.assertEqual(result.errors, [])

    def test_ac_fr_002_03_legacy_wikilinks_file_unchanged(self):
        base = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'extensions')
        with open(os.path.join(base, 'wikilinks.txt'), encoding='utf-8') as f:
            source = f.read()
        with open(os.path.join(base, 'wikilinks.html'), encoding='utf-8') as f:
            expected = f.read()
        output = markdown.markdown(source, extensions=['wikilinks'])
        # Compare the same way the legacy test runner does (ignoring
        # whitespace-only differences between lines).
        self.assertEqual(
            [line.strip() for line in output.strip().splitlines() if line.strip()],
            [line.strip() for line in expected.strip().splitlines() if line.strip()]
        )

    def test_ac_fr_002_04_empty_plain_wikilink_renders_nothing(self):
        md = markdown.Markdown(extensions=['wikilinks'])
        self.assertEqual(md.convert('foo [[ ]] bar'), '<p>foo  bar</p>')

    def test_ac_fr_002_05_empty_page_name_with_text_renders_nothing(self):
        md = markdown.Markdown(extensions=['wikilinks'])
        output = md.convert('foo [[ |text]] bar')
        self.assertNotIn('<a', output)
        self.assertNotIn('href', output)
        self.assertEqual(output, '<p>foo  bar</p>')


if __name__ == '__main__':
    unittest.main()
