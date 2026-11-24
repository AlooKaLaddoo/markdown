---
title: Strikethrough Extension
---

# Strikethrough

## Summary

The Strikethrough extension adds GitHub-style syntax for struck-out text.
Text wrapped in a pair of double tildes is rendered as a `<del>` element.

## Syntax

```md
This is ~~withdrawn~~ text.
```

becomes:

```html
<p>This is <del>withdrawn</del> text.</p>
```

Other inline markup (strong, emphasis, links, etc.) inside the struck text
works as usual, and strikethrough can itself be nested inside emphasis.

The following rules apply:

* Only a run of exactly two tildes is a delimiter. A single `~` and runs of
  three or more tildes (such as `~~~foo~~~`) are left as literal text.
* The opening `~~` must not be followed by whitespace, and the closing `~~`
  must not be preceded by whitespace. So `a ~~ b ~~ c` is left as is.
  Intraword use, such as `a~~b~~c`, is allowed.
* An unclosed `~~` is left as literal text.
* Tildes inside code spans and fenced code blocks are not affected.

When the extension is enabled, a tilde can be escaped with a backslash (`\~`)
to prevent it from being treated as a delimiter. For example,
`\~\~foo\~\~` renders as `~~foo~~`.

## Usage

See [Extensions](index.md) for general extension usage. Use `strikethrough` as
the name of the extension.

This extension does not accept any special configuration options.

A trivial example:

```python
markdown.markdown(some_text, extensions=['strikethrough'])
```
