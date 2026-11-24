"""
Acceptance tests for issue #2: RecursionError on deeply nested lists.
"""

import unittest

import markdown
from markdown.test_tools import recursionlimit


class TestDeepListNesting(unittest.TestCase):

    def test_ac_fr_001_01_deep_unordered_list(self):
        result = markdown.markdown('- ' * 500 + 'x')
        self.assertIsInstance(result, str)
        self.assertTrue(result.startswith('<ul>'))
        self.assertIn('x', result)

    def test_ac_fr_001_02_deep_ordered_list(self):
        result = markdown.markdown('1. ' * 500 + 'x')
        self.assertIsInstance(result, str)
        self.assertTrue(result.startswith('<ol>'))
        self.assertIn('x', result)

    def test_ac_fr_001_03_deep_indented_lines(self):
        source = '\n'.join(' ' * (4 * i) + '- x' for i in range(300))
        result = markdown.markdown(source)
        self.assertIsInstance(result, str)
        self.assertTrue(result.startswith('<ul>'))

    def test_ac_fr_001_04_mixed_deep_nesting(self):
        result = markdown.markdown('- 1. ' * 250 + 'x')
        self.assertIsInstance(result, str)

    def test_ac_fr_001_05_lowered_recursion_limit(self):
        with recursionlimit(150):
            result = markdown.markdown('- ' * 100 + 'x')
        self.assertIsInstance(result, str)

    def test_ac_fr_001_06_converter_reusable_after_deep_input(self):
        md = markdown.Markdown()
        md.convert('- ' * 500 + 'x')
        md.reset()
        self.assertEqual(md.convert('- a\n- b'), '<ul>\n<li>a</li>\n<li>b</li>\n</ul>')


class TestShallowListNestingUnchanged(unittest.TestCase):

    def test_ac_fr_002_01_three_level_indented_list(self):
        self.assertEqual(
            markdown.markdown('- a\n    - b\n        - c'),
            '<ul>\n<li>a<ul>\n<li>b<ul>\n<li>c</li>\n</ul>\n</li>\n</ul>\n</li>\n</ul>'
        )

    def test_ac_fr_002_02_ordered_in_unordered(self):
        self.assertEqual(
            markdown.markdown('- a\n    1. b\n    2. c'),
            '<ul>\n<li>a<ol>\n<li>b</li>\n<li>c</li>\n</ol>\n</li>\n</ul>'
        )

    def test_ac_fr_002_03_shallow_same_line_markers(self):
        self.assertEqual(
            markdown.markdown('- - - x'),
            '<ul>\n<li>\n<ul>\n<li>\n<ul>\n<li>x</li>\n</ul>\n</li>\n</ul>\n</li>\n</ul>'
        )

    def test_ac_fr_002_04_blockquote_nesting_limit_still_holds(self):
        # The full suite run covers AC-FR-002-04; additionally make sure the
        # blockquote guard behaves as before alongside the list guard.
        with recursionlimit(120):
            result = markdown.markdown('>' * 100)
        self.assertIsInstance(result, str)


if __name__ == '__main__':
    unittest.main()
