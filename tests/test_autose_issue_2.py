"""
Acceptance tests for issue #2: RecursionError on deeply nested lists.
"""

import unittest

import markdown
from markdown.test_tools import TestCase


class TestDeepInlineListMarkers(TestCase):
    """FR-001: deeply nested inline list markers must not raise."""

    def test_ac_fr_001_01_500_unordered_markers(self):
        source = '- ' * 500 + 'x'
        result = markdown.markdown(source)
        self.assertIsInstance(result, str)
        self.assertTrue(result.startswith('<ul>'))
        self.assertIn('x', result)

    def test_ac_fr_001_02_500_ordered_markers(self):
        source = '1. ' * 500 + 'x'
        result = markdown.markdown(source)
        self.assertIsInstance(result, str)
        self.assertTrue(result.startswith('<ol>'))
        self.assertIn('x', result)

    def test_ac_fr_001_03_5000_unordered_markers(self):
        source = '- ' * 5000 + 'x'
        result = markdown.markdown(source)
        self.assertIsInstance(result, str)
        self.assertIn('x', result)

    def test_ac_fr_001_04_asterisk_markers(self):
        source = '* ' * 500 + 'x'
        result = markdown.markdown(source)
        self.assertIsInstance(result, str)
        self.assertIn('x', result)

    def test_ac_fr_001_04_plus_markers(self):
        source = '+ ' * 500 + 'x'
        result = markdown.markdown(source)
        self.assertIsInstance(result, str)
        self.assertIn('x', result)


class TestProgressivelyIndentedLists(TestCase):
    """FR-002: many progressively indented list lines must not raise."""

    def test_ac_fr_002_01_unordered_4_space_steps(self):
        source = '\n'.join(' ' * (4 * i) + '- x' for i in range(300))
        result = markdown.markdown(source)
        self.assertIsInstance(result, str)
        self.assertTrue(result.startswith('<ul>'))

    def test_ac_fr_002_02_ordered_loose_4_space_steps(self):
        source = '\n\n'.join(' ' * (4 * i) + '1. x' for i in range(300))
        result = markdown.markdown(source)
        self.assertIsInstance(result, str)
        self.assertTrue(result.startswith('<ol>'))

    def test_ac_fr_002_03_unordered_1_space_steps(self):
        source = '\n'.join(' ' * i + '- x' for i in range(300))
        result = markdown.markdown(source)
        self.assertIsInstance(result, str)


class TestShallowNestedListsUnchanged(TestCase):
    """FR-003: shallow nested lists render exactly as before."""

    def test_ac_fr_003_01_three_level_tight_unordered(self):
        self.assertEqual(
            markdown.markdown('* Tab\n    * Tab\n        * Tab'),
            '<ul>\n<li>Tab<ul>\n<li>Tab<ul>\n<li>Tab</li>\n</ul>\n</li>\n</ul>\n</li>\n</ul>'
        )

    def test_ac_fr_003_02_ordered_with_nested_unordered_tight(self):
        self.assertEqual(
            markdown.markdown('1. First\n2. Second:\n    * Fee\n    * Fie\n    * Foe\n3. Third'),
            '<ol>\n<li>First</li>\n<li>Second:<ul>\n<li>Fee</li>\n<li>Fie</li>\n<li>Foe</li>\n</ul>\n'
            '</li>\n<li>Third</li>\n</ol>'
        )

    def test_ac_fr_003_03_loose_ordered_with_nested_unordered(self):
        self.assertEqual(
            markdown.markdown('1. First\n\n2. Second:\n    * Fee\n    * Fie\n    * Foe\n\n3. Third'),
            '<ol>\n<li>\n<p>First</p>\n</li>\n<li>\n<p>Second:</p>\n<ul>\n<li>Fee</li>\n<li>Fie</li>\n'
            '<li>Foe</li>\n</ul>\n</li>\n<li>\n<p>Third</p>\n</li>\n</ol>'
        )

    def _run_named_test(self, name):
        suite = unittest.defaultTestLoader.loadTestsFromName(name)
        self.assertGreater(suite.countTestCases(), 0, name)
        result = unittest.TestResult()
        suite.run(result)
        self.assertTrue(
            result.wasSuccessful(),
            '{} failed: {}'.format(name, [str(e[1]) for e in result.errors + result.failures])
        )

    def test_ac_fr_003_04_legacy_ordered_and_unordered_fixture(self):
        self._run_named_test('tests.test_legacy.TestBasic.test_ordered_and_unordered_list')

    def test_ac_fr_003_04_blockquote_nesting_limit(self):
        self._run_named_test('tests.test_syntax.blocks.test_blockquotes.TestBlockquoteBlocks.test_nesting_limit')


if __name__ == '__main__':
    unittest.main()
