# Strikethrough Extension for Python-Markdown
# ===========================================

# This extension adds GitHub-style `~~strikethrough~~` syntax.

# Copyright 2026 The Python Markdown Project

# License: [BSD](https://opensource.org/licenses/bsd-license.php)

"""
This extension renders text wrapped in a pair of double tildes (`~~text~~`)
as a `<del>` element, as GitHub does.

See the [documentation](https://Python-Markdown.github.io/extensions/strikethrough)
for details.
"""

from __future__ import annotations

from . import Extension
from ..inlinepatterns import SimpleTagInlineProcessor

STRIKE_RE = r'(?<!~)(~~)(?![\s~])(.+?)(?<![\s~])~~(?!~)'
""" Match `~~text~~`: exactly two tildes, not flanked by whitespace on the inside. """


class StrikethroughExtension(Extension):
    """ Add strikethrough to Markdown. """

    def extendMarkdown(self, md):
        """ Register the processor and make `~` escapable.

        | Class Instance                                                                   | Registry                                                         | Name            | Priority |
        | -------------------------------------------------------------------------------- | ---------------------------------------------------------------- | --------------- | :------: |
        | [`SimpleTagInlineProcessor`][markdown.inlinepatterns.SimpleTagInlineProcessor] | [`inlinepatterns`][markdown.inlinepatterns.build_inlinepatterns] | `strikethrough` | `65`     |

        """
        # flake8: noqa: E501 33-35

        md.inlinePatterns.register(SimpleTagInlineProcessor(STRIKE_RE, 'del'), 'strikethrough', 65)
        if '~' not in md.ESCAPED_CHARS:
            md.ESCAPED_CHARS.append('~')


def makeExtension(**kwargs):  # pragma: no cover
    """ Return an instance of the `StrikethroughExtension` """
    return StrikethroughExtension(**kwargs)
