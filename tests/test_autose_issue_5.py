"""
Acceptance tests for issue #5: readable `toc` anchors for non-Latin headings.
"""

import unittest

import markdown
from markdown.extensions.toc import TocExtension, slugify, slugify_unicode


class TestAutoseIssue5(unittest.TestCase):
    maxDiff = None

    # FR-001

    def test_ac_fr_001_01_russian_heading_readable_id(self):
        self.assertEqual(
            markdown.markdown('# Введение', extensions=['toc']),
            '<h1 id="введение">Введение</h1>'
        )

    def test_ac_fr_001_02_multi_word_russian_uses_separator_and_toc_link(self):
        out = markdown.markdown('[TOC]\n\n# Быстрый старт', extensions=['toc'])
        self.assertIn('<h1 id="быстрый-старт">Быстрый старт</h1>', out)
        self.assertIn('<a href="#быстрый-старт">Быстрый старт</a>', out)

    def test_ac_fr_001_03_duplicate_non_latin_headings_unique(self):
        self.assertEqual(
            markdown.markdown('# Введение\n\n# Введение', extensions=['toc']),
            '<h1 id="введение">Введение</h1>\n<h1 id="введение_1">Введение</h1>'
        )

    def test_ac_fr_001_04_latin_and_extended_latin_unchanged(self):
        self.assertEqual(
            markdown.markdown('# Žlutý kůň\n\n# Hello World', extensions=['toc']),
            '<h1 id="zluty-kun">Žlutý kůň</h1>\n<h1 id="hello-world">Hello World</h1>'
        )

    def test_ac_fr_001_05_mixed_latin_cyrillic_keeps_ascii_slug(self):
        self.assertEqual(
            markdown.markdown('# Setup Настройка', extensions=['toc']),
            '<h1 id="setup">Setup Настройка</h1>'
        )

    def test_ac_fr_001_06_no_word_characters_falls_back_to_numbered_id(self):
        self.assertEqual(
            markdown.markdown('# !!!', extensions=['toc']),
            '<h1 id="_1">!!!</h1>'
        )

    def test_ac_fr_001_07_user_slugify_callable_used_as_is(self):
        self.assertEqual(
            markdown.markdown(
                '# Введение',
                extensions=[TocExtension(slugify=lambda value, separator: 'custom')]
            ),
            '<h1 id="custom">Введение</h1>'
        )

    def test_ac_fr_001_01_fallback_uses_composed_characters(self):
        # `й` must stay a single composed character, not `и` + combining breve.
        self.assertEqual(slugify('Настройка', '-'), 'настройка')
        self.assertEqual(slugify('Ёлка', '-'), 'ёлка')

    # FR-002

    def test_ac_fr_002_01_hindi_heading_keeps_vowel_signs_by_default(self):
        self.assertEqual(
            markdown.markdown('# परिचय', extensions=['toc']),
            '<h1 id="परिचय">परिचय</h1>'
        )

    def test_ac_fr_002_02_hindi_multi_word_keeps_marks_with_slugify_unicode(self):
        self.assertEqual(
            markdown.markdown(
                '# नमस्ते दुनिया',
                extensions=[TocExtension(slugify=slugify_unicode)]
            ),
            '<h1 id="नमस्ते-दुनिया">नमस्ते दुनिया</h1>'
        )

    def test_ac_fr_002_03_punctuation_still_stripped_from_unicode_slugs(self):
        self.assertEqual(
            markdown.markdown(
                '# Unicode ヘッダー!',
                extensions=[TocExtension(slugify=slugify_unicode)]
            ),
            '<h1 id="unicode-ヘッダー">Unicode ヘッダー!</h1>'
        )

    def test_ac_fr_002_04_ascii_mode_strips_latin_accents(self):
        self.assertEqual(slugify('Žlutý kůň', '-'), 'zluty-kun')


if __name__ == '__main__':
    unittest.main()
