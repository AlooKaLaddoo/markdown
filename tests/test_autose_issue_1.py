"""Acceptance tests for issue #1: TypeError in toc with a bare `{id}` attribute on a heading."""

import unittest

import markdown
from markdown.extensions import toc

EXTS = ['toc', 'attr_list']


class TestAutoseIssue1(unittest.TestCase):

    def test_ac_fr_001_01_bare_id_without_marker(self):
        self.assertEqual(markdown.markdown('#d {id}', extensions=EXTS), '<h1 id="d">d</h1>')

    def test_ac_fr_001_02_bare_id_with_marker(self):
        self.assertEqual(
            markdown.markdown('[TOC]\n\n# Header 1 {id}', extensions=EXTS),
            '<div class="toc">\n<ul>\n<li><a href="#header-1">Header 1</a></li>\n</ul>\n</div>\n'
            '<h1 id="header-1">Header 1</h1>'
        )

    def test_ac_fr_001_03_toc_tokens_carry_generated_id(self):
        md = markdown.Markdown(extensions=EXTS)
        md.convert('# Header 1 {id}')
        self.assertEqual(md.toc_tokens[0]['id'], 'header-1')
        self.assertEqual(md.toc_tokens[0]['name'], 'Header 1')

    def test_ac_fr_001_04_generated_id_unique(self):
        self.assertEqual(
            markdown.markdown('# Title\n\n# Title {id}', extensions=EXTS),
            '<h1 id="title">Title</h1>\n<h1 id="title_1">Title</h1>'
        )

    def test_ac_fr_001_05_permalink(self):
        html = markdown.markdown('# Header 1 {id}', extensions=['attr_list', toc.TocExtension(permalink=True)])
        self.assertIn('<h1 id="header-1">', html)
        self.assertIn('class="headerlink" href="#header-1"', html)

    def test_ac_fr_001_06_anchorlink(self):
        self.assertEqual(
            markdown.markdown('# Header 1 {id}', extensions=['attr_list', toc.TocExtension(anchorlink=True)]),
            '<h1 id="header-1"><a class="toclink" href="#header-1">Header 1</a></h1>'
        )

    def test_ac_fr_001_07_explicit_ids_not_overridden(self):
        for src in ('# Title {#my-id}', '# Title {id=my-id}'):
            with self.subTest(src=src):
                self.assertEqual(markdown.markdown(src, extensions=EXTS), '<h1 id="my-id">Title</h1>')

    def test_ac_fr_001_08_other_valueless_attrs_preserved(self):
        self.assertEqual(
            markdown.markdown('# Heading {download}', extensions=EXTS),
            '<h1 download id="heading">Heading</h1>'
        )


if __name__ == '__main__':
    unittest.main()
