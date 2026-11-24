"""
Acceptance tests for issue #1: TypeError in toc when a heading has a bare `{id}` attribute.
"""

import unittest

import markdown
from markdown.extensions.toc import TocExtension
from markdown.test_tools import TestCase


class TestBareIdOnHeading(TestCase):

    maxDiff = None

    def test_ac_fr_001_01_reported_reproduction(self):
        result = markdown.markdown('#d {id}', extensions=['toc', 'attr_list'])
        self.assertEqual(result, '<h1 id="d">d</h1>')

    def test_ac_fr_001_02_bare_id_with_toc_marker(self):
        md = markdown.Markdown(extensions=['toc', 'attr_list'])
        html = md.convert('[TOC]\n\n# Some Title {id}')
        self.assertIn('<h1 id="some-title">Some Title</h1>', html)
        self.assertIn('<div class="toc">', html)
        toc_div = html[html.index('<div class="toc">'):html.index('</div>') + len('</div>')]
        self.assertIn('<a href="#some-title">Some Title</a>', toc_div)
        self.assertEqual(
            md.toc_tokens,
            [{
                'level': 1,
                'id': 'some-title',
                'name': 'Some Title',
                'html': 'Some Title',
                'data-toc-label': '',
                'children': [],
            }]
        )

    def test_ac_fr_001_03_generated_slug_is_unique(self):
        result = markdown.markdown('# Title\n\n# Title {id}', extensions=['toc', 'attr_list'])
        self.assertEqual(result, '<h1 id="title">Title</h1>\n<h1 id="title_1">Title</h1>')

    def test_ac_fr_001_04_bare_id_with_other_attributes(self):
        result = markdown.markdown('# Title {id .cls}', extensions=['toc', 'attr_list'])
        self.assertEqual(result, '<h1 class="cls" id="title">Title</h1>')

    def test_ac_fr_001_05_bare_id_with_permalink(self):
        result = markdown.markdown('# Title {id}', extensions=['attr_list', TocExtension(permalink=True)])
        self.assertIn('<h1 id="title">', result)
        self.assertIn('href="#title"', result)
        self.assertIn('class="headerlink"', result)

    def test_ac_fr_001_05_bare_id_with_anchorlink(self):
        result = markdown.markdown('# Title {id}', extensions=['attr_list', TocExtension(anchorlink=True)])
        self.assertIn('<h1 id="title">', result)
        self.assertIn('href="#title"', result)
        self.assertIn('class="toclink"', result)


class TestExistingIdHandling(TestCase):

    def test_ac_fr_002_01_explicit_id_not_overridden(self):
        md = markdown.Markdown(extensions=['toc', 'attr_list'])
        result = md.convert('# Title {#my-id}')
        self.assertEqual(result, '<h1 id="my-id">Title</h1>')
        self.assertEqual(md.toc_tokens[0]['id'], 'my-id')

    def test_ac_fr_002_02_heading_without_attributes_gets_slug(self):
        result = markdown.markdown('# Title', extensions=['toc', 'attr_list'])
        self.assertEqual(result, '<h1 id="title">Title</h1>')

    def test_ac_fr_002_03_existing_toc_and_attr_list_tests_pass(self):
        # Running the whole suite from inside a test would recurse into this file,
        # so run the existing toc and attr_list test modules named by the criterion.
        # The full suite is run by the pipeline itself.
        loader = unittest.TestLoader()
        suite = unittest.TestSuite([
            loader.loadTestsFromName('tests.test_syntax.extensions.test_toc'),
            loader.loadTestsFromName('tests.test_syntax.extensions.test_attr_list'),
        ])
        result = unittest.TestResult()
        suite.run(result)
        self.assertGreater(result.testsRun, 0)
        self.assertEqual(result.failures, [])
        self.assertEqual(result.errors, [])

    def test_ac_fr_002_04_valueless_id_without_toc_unchanged(self):
        result = markdown.markdown('# Title {id}', extensions=['attr_list'])
        self.assertEqual(result, '<h1 id>Title</h1>')


if __name__ == '__main__':
    unittest.main()
