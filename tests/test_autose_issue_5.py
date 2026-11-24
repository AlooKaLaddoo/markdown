"""
Acceptance tests for issue #5: TOC ids for non-English (Hindi, Russian) headings.
"""

import os
import unittest

import markdown
from markdown.test_tools import TestCase
from markdown.extensions.toc import TocExtension, slugify, slugify_unicode


DOCS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'docs', 'extensions', 'toc.md'
)


def read_docs():
    with open(DOCS_PATH, encoding='utf-8') as f:
        return f.read()


class TestSlugifyUnicodeCombiningMarks(TestCase):
    """FR-001: slugify_unicode keeps Mn/Mc characters."""

    def test_ac_fr_001_01_hindi_heading_keeps_vowel_signs_and_virama(self):
        self.assertMarkdownRenders(
            '# नमस्ते दुनिया',
            '<h1 id="नमस्ते-दुनिया">नमस्ते दुनिया</h1>',
            extensions=[TocExtension(slugify=slugify_unicode)]
        )

    def test_ac_fr_001_02_direct_call_hindi_combining_marks(self):
        self.assertEqual(slugify_unicode('हिन्दी', '-'), 'हिन्दी')

    def test_ac_fr_001_03_russian_heading_unchanged(self):
        self.assertMarkdownRenders(
            '# Привет мир',
            '<h1 id="привет-мир">Привет мир</h1>',
            extensions=[TocExtension(slugify=slugify_unicode)]
        )

    def test_ac_fr_001_04_punctuation_removed_japanese_unchanged(self):
        self.assertEqual(slugify_unicode('Unicode ヘッダー!?', '-'), 'unicode-ヘッダー')

    def test_ac_fr_001_04_permalink_with_unicode_in_id_still_passes(self):
        self.assertMarkdownRenders(
            '# Unicode ヘッダー',
            '<h1 id="unicode-ヘッダー">'
            'Unicode ヘッダー'
            '<a class="headerlink" href="#unicode-ヘッダー" title="Permanent link">&para;</a>'
            '</h1>',
            extensions=[TocExtension(permalink=True, slugify=slugify_unicode)]
        )

    def test_ac_fr_001_04_permalink_with_unicode_title_still_passes(self):
        self.assertMarkdownRenders(
            '# Unicode ヘッダー',
            '<h1 id="unicode-ヘッダー">'
            'Unicode ヘッダー'
            '<a class="headerlink" href="#unicode-ヘッダー" title="パーマリンク">&para;</a>'
            '</h1>',
            extensions=[TocExtension(permalink=True, permalink_title="パーマリンク", slugify=slugify_unicode)]
        )

    def test_ac_fr_001_05_default_slugify_extended_latin(self):
        self.assertEqual(slugify('Théâtre', '-'), 'theatre')

    def test_ac_fr_001_05_default_slugify_cyrillic_empty(self):
        self.assertEqual(slugify('Привет мир', '-'), '')

    def test_ac_fr_001_05_permalink_with_extended_latin_in_id_still_passes(self):
        self.assertMarkdownRenders(
            '# Théâtre',
            '<h1 id="theatre">'
            'Théâtre'
            '<a class="headerlink" href="#theatre" title="Permanent link">&para;</a>'
            '</h1>',
            extensions=[TocExtension(permalink=True)]
        )


class TestSlugifyUnicodeDocs(unittest.TestCase):
    """FR-002: docs contain a concrete non-Latin slugify_unicode example."""

    EXPECTED_HTML = '<h1 id="привет-мир">Привет мир</h1>'

    def test_ac_fr_002_01_docs_show_configuration(self):
        text = read_docs()
        self.assertIn('TocExtension(slugify=slugify_unicode)', text)
        self.assertIn('from markdown.extensions.toc import TocExtension, slugify_unicode', text)

    def test_ac_fr_002_02_docs_show_cyrillic_heading_and_id(self):
        text = read_docs()
        self.assertIn('# Привет мир', text)
        self.assertIn(self.EXPECTED_HTML, text)

    def test_ac_fr_002_03_documented_output_matches_actual(self):
        result = markdown.markdown(
            '# Привет мир',
            extensions=[TocExtension(slugify=slugify_unicode)]
        )
        self.assertEqual(result, self.EXPECTED_HTML)

    def test_ac_fr_002_04_default_documented_unchanged(self):
        self.assertIn('Default: `markdown.extensions.toc.slugify`', read_docs())


if __name__ == '__main__':
    unittest.main()
