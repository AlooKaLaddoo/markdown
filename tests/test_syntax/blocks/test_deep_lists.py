import markdown
from markdown.test_tools import TestCase


class TestDeepLists(TestCase):

    def test_deep_unordered_list_does_not_raise(self):
        result = markdown.markdown('- ' * 500 + 'x')
        self.assertIn('x', result)

    def test_shallow_list_unchanged(self):
        self.assertMarkdownRenders('- a\n- b', '<ul>\n<li>a</li>\n<li>b</li>\n</ul>')
