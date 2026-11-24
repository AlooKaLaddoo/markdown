# Strikethrough Extension for Python-Markdown
# ===========================================

# This extension adds `~~strikethrough~~` syntax, rendered as `<del>`.

# Copyright 2026 The Python Markdown Project

# License: [BSD](https://opensource.org/licenses/bsd-license.php)

"""
This extension renders text enclosed in double tildes (`~~text~~`) as a
`<del>` element, as GitHub does.
"""

from __future__ import annotations

from . import Extension
from ..inlinepatterns import DelimiterProcessor


class StrikethroughExtension(Extension):
    """ Add strikethrough extension to Markdown class."""

    def extendMarkdown(self, md):
        """ Register the `~` delimiter.

        | Class Instance                                                     | Registry                                                         | Name            | Priority |
        | ------------------------------------------------------------------ | ---------------------------------------------------------------- | --------------- | :------: |
        | [`DelimiterProcessor`][markdown.inlinepatterns.DelimiterProcessor] | [`inlinepatterns`][markdown.inlinepatterns.build_inlinepatterns] | `strikethrough` | `60`     |

        The `~` delimiter is added to the existing `em_strong` processor when one is
        present, so it is paired together with `*` and `_`. Otherwise a new
        processor is registered as `strikethrough`.

        """
        # flake8: noqa: E501 27-29

        if md.delimiters is not None:
            md.delimiters.add('~', 'del', smart=False, double=True)
        else:
            md.inlinePatterns.register(
                DelimiterProcessor('~', 'del', md, smart=False, double=True), 'strikethrough', 60
            )


def makeExtension(**kwargs):  # pragma: no cover
    """ Return an instance of the `StrikethroughExtension` """
    return StrikethroughExtension(**kwargs)
