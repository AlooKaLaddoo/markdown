from markdown.test_tools import TestCase


class TestStrikethrough(TestCase):
    default_kwargs = {'extensions': ['strikethrough']}

    def test_basic(self):
        self.assertMarkdownRenders('~~gone~~ text', '<p><del>gone</del> text</p>')

    def test_with_bold(self):
        self.assertMarkdownRenders('~~**b**~~', '<p><del><strong>b</strong></del></p>')
