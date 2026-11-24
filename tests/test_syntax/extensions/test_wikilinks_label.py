from markdown.test_tools import TestCase


class TestWikiLinkLabels(TestCase):

    def test_piped_link_shows_label(self):
        html = self.md_render('[[Installation Guide|see the install docs]]')
        self.assertIn('>see the install docs</a>', html)

    def test_plain_link_unchanged(self):
        self.assertMarkdownRenders(
            '[[Installation Guide]]',
            '<p><a class="wikilink" href="/Installation_Guide/">Installation Guide</a></p>',
            extensions=['wikilinks']
        )

    def md_render(self, src):
        import markdown
        return markdown.markdown(src, extensions=['wikilinks'])
