---
title: Strikethrough Extension
---

# Strikethrough

## Summary

The Strikethrough extension adds GitHub-style strikethrough syntax. Text
enclosed in double tildes is rendered as a `<del>` element:

```md
This is ~~deleted~~ text.
```

becomes:

```html
<p>This is <del>deleted</del> text.</p>
```

## Syntax

* Exactly two tildes (`~~`) open and close a strikethrough span.
* The opening `~~` must not be followed by whitespace and the closing `~~` must
  not be preceded by whitespace, so `~~ text ~~` is output literally.
* A single tilde (`~text~`) and an unclosed `~~` are output literally.
* Other inline markup works inside and around a strikethrough span, e.g.
  `~~a **bold** [link](https://example.com)~~` or `**bold ~~struck~~**`.
* Tildes in code spans and fenced code blocks are not affected.
* `\~` is not a backslash escape; a backslash before a tilde is output as is.

## Usage

See [Extensions](index.md) for general extension usage. Use `strikethrough` as
the name of the extension, or the dotted path
`markdown.extensions.strikethrough`.

This extension does not accept any special configuration options.

A trivial example:

```python
markdown.markdown(some_text, extensions=['strikethrough'])
```
