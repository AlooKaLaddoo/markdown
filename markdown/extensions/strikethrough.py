"""
Strikethrough extension: `~~text~~` renders as `<del>text</del>`.

The pattern itself is part of the core inline patterns (see `build_inlinepatterns`), so this
extension only exists so that `extensions=['strikethrough']` keeps working for users who ask for it.
"""
from . import Extension


class StrikethroughExtension(Extension):
    def extendMarkdown(self, md):
        pass


def makeExtension(**kwargs):  # pragma: no cover
    return StrikethroughExtension(**kwargs)
