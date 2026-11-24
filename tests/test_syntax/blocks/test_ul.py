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

Copyright 2007-2024 The Python Markdown Project (v. 1.7 and later)
Copyright 2004, 2005, 2006 Yuri Takhteyev (v. 0.2-1.6b)
Copyright 2004 Manfred Stienstra (the original version)

License: BSD (see LICENSE.md for details).
"""

import unittest
import markdown
from markdown.test_tools import TestCase, recursionlimit


class TestUnorderedLists(TestCase):

    # TODO: Move legacy tests here

    def test_header_and_paragraph_no_blank_line_loose_list(self):
        self.assertMarkdownRenders(
            self.dedent(
                """
                - ### List 1
                    Entry 1.1

                - ### List 2
                    Entry 2.1
                """
            ),
            self.dedent(
                """
                <ul>
                <li>
                <h3>List 1</h3>
                <p>Entry 1.1</p>
                </li>
                <li>
                <h3>List 2</h3>
                <p>Entry 2.1</p>
                </li>
                </ul>
                """
            )
        )

    # Note: This is strange. Any other element on first line of list item would get very
    # different behavior. However, as a heading can only ever be one line, this is the
    # correct behavior. In fact, `markdown.pl` behaves this way with no indentation.
    def test_header_and_paragraph_no_blank_line_loose_list_no_indent(self):
        self.assertMarkdownRenders(
            self.dedent(
                """
                - ### List 1
                Entry 1.1

                - ### List 2
                Entry 2.1
                """
            ),
            self.dedent(
                """
                <ul>
                <li>
                <h3>List 1</h3>
                <p>Entry 1.1</p>
                </li>
                <li>
                <h3>List 2</h3>
                <p>Entry 2.1</p>
                </li>
                </ul>
                """
            )
        )

    # TODO: Possibly change this behavior. While this test follows the behavior
    # of `markdown.pl`, it is likely surprising to most users. In fact, actual
    # behavior is to return the same results as for a loose list.
    @unittest.skip('This behaves as a loose list in Python-Markdown')
    def test_header_and_paragraph_no_blank_line_tight_list(self):
        self.assertMarkdownRenders(
            self.dedent(
                """
                - ### List 1
                    Entry 1.1
                - ### List 2
                    Entry 2.1
                """
            ),
            self.dedent(
                """
                <ul>
                <li>### List 1
                Entry 1.1</li>
                <li>### List 2
                Entry 2.1</li>
                </ul>
                """
            )
        )

    # TODO: Possibly change this behavior. While this test follows the behavior
    # of `markdown.pl`, it is likely surprising to most users. In fact, actual
    # behavior is to return the same results as for a loose list.
    @unittest.skip('This behaves as a loose list in Python-Markdown')
    def test_header_and_paragraph_no_blank_line_tight_list_no_indent(self):
        self.assertMarkdownRenders(
            self.dedent(
                """
                - ### List 1
                Entry 1.1
                - ### List 2
                Entry 2.1
                """
            ),
            self.dedent(
                """
                <ul>
                <li>### List 1
                Entry 1.1</li>
                <li>### List 2
                Entry 2.1</li>
                </ul>
                """
            )
        )


class TestListNestingLimit(TestCase):
    """ Deeply nested lists must not raise `RecursionError`. """

    def render(self, source):
        result = markdown.markdown(source)
        self.assertIsInstance(result, str)
        return result

    def test_nested_unordered_markers(self):
        for marker in ('- ', '* ', '+ '):
            with self.subTest(marker=marker):
                result = self.render(marker * 500 + 'x')
                self.assertTrue(result.startswith('<ul>'))
                self.assertIn('x', result)

    def test_nested_ordered_markers(self):
        result = self.render('1. ' * 500 + 'x')
        self.assertTrue(result.startswith('<ol>'))
        self.assertIn('x', result)

    def test_very_deeply_nested_markers(self):
        result = self.render('- ' * 5000 + 'x')
        self.assertIn('x', result)

    def test_progressively_indented_lines(self):
        result = self.render('\n'.join(' ' * (4 * i) + '- x' for i in range(300)))
        self.assertTrue(result.startswith('<ul>'))

    def test_progressively_indented_loose_ordered(self):
        result = self.render('\n\n'.join(' ' * (4 * i) + '1. x' for i in range(300)))
        self.assertTrue(result.startswith('<ol>'))

    def test_progressively_indented_by_one_space(self):
        self.render('\n'.join(' ' * i + '- x' for i in range(300)))

    def test_nesting_limit_with_lowered_recursion_limit(self):
        with recursionlimit(150):
            result = self.render('- ' * 50 + 'x')
        self.assertTrue(result.startswith('<ul>'))
        self.assertIn('x', result)

    def test_shallow_tight_nesting_unchanged(self):
        self.assertMarkdownRenders(
            '* Tab\n    * Tab\n        * Tab',
            '<ul>\n<li>Tab<ul>\n<li>Tab<ul>\n<li>Tab</li>\n</ul>\n</li>\n</ul>\n</li>\n</ul>'
        )

    def test_shallow_mixed_nesting_unchanged(self):
        self.assertMarkdownRenders(
            '1. First\n2. Second:\n    * Fee\n    * Fie\n    * Foe\n3. Third',
            '<ol>\n<li>First</li>\n<li>Second:<ul>\n<li>Fee</li>\n<li>Fie</li>\n<li>Foe</li>\n</ul>\n</li>\n'
            '<li>Third</li>\n</ol>'
        )

    def test_shallow_loose_nesting_unchanged(self):
        self.assertMarkdownRenders(
            '1. First\n\n2. Second:\n    * Fee\n    * Fie\n    * Foe\n\n3. Third',
            '<ol>\n<li>\n<p>First</p>\n</li>\n<li>\n<p>Second:</p>\n<ul>\n<li>Fee</li>\n<li>Fie</li>\n'
            '<li>Foe</li>\n</ul>\n</li>\n<li>\n<p>Third</p>\n</li>\n</ol>'
        )
