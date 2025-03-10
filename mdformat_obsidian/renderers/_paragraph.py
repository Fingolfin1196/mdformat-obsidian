from __future__ import annotations

import re
from typing import TYPE_CHECKING

from markdown_it.rules_block.html_block import HTML_SEQUENCES
from mdformat import codepoints
from mdformat.renderer._context import _wrap
from mdformat.renderer._util import decimalify_leading, decimalify_trailing

from .._helpers import separate_indent

if TYPE_CHECKING:
    from mdformat.renderer import RenderContext, RenderTreeNode


def paragraph(node: RenderTreeNode, context: RenderContext) -> str:  # noqa: C901
    inline_node = node.children[0]
    text = inline_node.render(context)

    if context.do_wrap:
        wrap_mode = context.options["mdformat"]["wrap"]
        if isinstance(wrap_mode, int):
            wrap_mode -= context.env["indent_width"]
            wrap_mode = max(1, wrap_mode)
        # Newlines should be mostly WRAP_POINTs by now, but there are
        # exceptional newlines that need to be preserved:
        # - hard breaks: newline defines the hard break
        # - html inline: newline vs space can be the difference between
        #                html block and html inline
        # Split the text and word wrap each section separately.
        sections = text.split("\n")
        text = "\n".join(_wrap(s, width=wrap_mode) for s in sections)

    # A paragraph can start or end in whitespace e.g. if the whitespace was
    # in decimal representation form. We need to re-decimalify it, one reason being
    # to enable "empty" paragraphs with whitespace only.
    text = decimalify_leading(codepoints.UNICODE_WHITESPACE, text)
    text = decimalify_trailing(codepoints.UNICODE_WHITESPACE, text)

    lines = text.split("\n")
    for i in range(len(lines)):
        # Strip whitespace to prevent issues like a line starting tab that is
        # interpreted as start of a code block.
        lines[i] = lines[i].rstrip()
        lindent, lstrip = separate_indent(lines[i])
        lines[i] = lstrip

        # If a line looks like an ATX heading, escape the first hash.
        if re.match(r"#{1,6}( |\t|$)", lines[i]):
            lines[i] = f"\\{lines[i]}"

        # Make sure a paragraph line does not start with ">"
        # (otherwise it will be interpreted as a block quote).
        if lines[i].startswith(">"):
            lines[i] = f"\\{lines[i]}"

        # Make sure a paragraph line does not start with "*", "-" or "+"
        # followed by a space, tab, or end of line.
        # (otherwise it will be interpreted as list item).
        if re.match(r"[-*+]( |\t|$)", lines[i]):
            lines[i] = f"\\{lines[i]}"

        # If a line starts with a number followed by "." or ")" followed by
        # a space, tab or end of line, escape the "." or ")" or it will be
        # interpreted as ordered list item.
        if re.match(r"[0-9]+\)( |\t|$)", lines[i]):
            lines[i] = lines[i].replace(")", "\\)", 1)
        if re.match(r"[0-9]+\.( |\t|$)", lines[i]):
            lines[i] = lines[i].replace(".", "\\.", 1)

        # Consecutive "-", "*" or "_" sequences can be interpreted as thematic
        # break. Escape them.
        space_removed = lines[i].replace(" ", "").replace("\t", "")
        if len(space_removed) >= 3:
            if all(c == "*" for c in space_removed):
                lines[i] = lines[i].replace("*", "\\*", 1)  # pragma: no cover
            elif all(c == "-" for c in space_removed):
                lines[i] = lines[i].replace("-", "\\-", 1)
            elif all(c == "_" for c in space_removed):
                lines[i] = lines[i].replace("_", "\\_", 1)  # pragma: no cover

        # A stripped line where all characters are "=" or "-" will be
        # interpreted as a setext heading. Escape.
        stripped = lines[i].strip(" \t")
        if all(c == "-" for c in stripped):
            lines[i] = lines[i].replace("-", "\\-", 1)
        elif all(c == "=" for c in stripped):
            lines[i] = lines[i].replace("=", "\\=", 1)

        # Check if the line could be interpreted as an HTML block.
        # If yes, prefix it with 4 spaces to prevent this.
        for html_seq_tuple in HTML_SEQUENCES:
            can_break_paragraph = html_seq_tuple[2]
            opening_re = html_seq_tuple[0]
            if can_break_paragraph and opening_re.search(lines[i]):
                lines[i] = f"    {lines[i]}"
                break

        lines[i] = lindent + lines[i]

    text = "\n".join(lines)

    return text
